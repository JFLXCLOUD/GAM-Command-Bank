"""
Storage and command logic for GAM Command Bank.

This module has no UI dependencies so it can be unit tested and shared by
any front end. It owns:

* where data lives on disk (portable next to the exe, or a per-user folder)
* loading / validating / normalising the command file
* safe (atomic) saving with a rolling backup
* searching, favorites, usage tracking
* import / export / merging of command files
* placeholder parsing and substitution

File format (unchanged from earlier versions, so old files keep working and
the web version can import/export the same file):

    {
        "GAM":        [{"command": "...", "description": "...", ...}, ...],
        "AD":         [...],
        "PowerShell": [...]
    }
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

APP_NAME = "GAM Command Bank"
APP_VERSION = "4.0"
DATA_FILENAME = "commands.json"
SETTINGS_FILENAME = "settings.json"
DATA_DIR_ENV = "GAM_COMMAND_BANK_HOME"

CATEGORIES = ("GAM", "AD", "PowerShell")

# Accept the various spellings used by older desktop / web builds.
_CATEGORY_ALIASES = {
    "gam": "GAM",
    "ad": "AD",
    "activedirectory": "AD",
    "active directory": "AD",
    "powershell": "PowerShell",
    "ps": "PowerShell",
}

# <name> placeholders. Excludes nested brackets and line breaks so that
# things like "2>&1" or "<<EOF" are not mistaken for placeholders.
PLACEHOLDER_RE = re.compile(r"<([^<>\r\n]+)>")

MAX_RECENT_VALUES = 10


# ─────────────────────────────────────────────────────────────────────────────
# Placeholders
# ─────────────────────────────────────────────────────────────────────────────
def placeholders(template: str) -> list[str]:
    """Unique placeholder names in the order they first appear."""
    seen: dict[str, None] = {}
    for name in PLACEHOLDER_RE.findall(template or ""):
        seen.setdefault(name, None)
    return list(seen)


def placeholder_choices(name: str) -> list[str]:
    """`<a|b|c>` placeholders offer a fixed list of choices."""
    if "|" not in name:
        return []
    parts = [p.strip() for p in name.split("|")]
    return parts if all(parts) else []


def fill(template: str, values: dict[str, str]) -> str:
    """Substitute placeholder values in a single pass.

    Blank values leave the `<placeholder>` in place so the user can see what
    is still missing. A single pass means a value that itself contains
    `<something>` is never substituted a second time.
    """
    def _sub(match: re.Match) -> str:
        value = (values.get(match.group(1)) or "").strip()
        return value if value else match.group(0)

    return PLACEHOLDER_RE.sub(_sub, template or "")


def missing_values(template: str, values: dict[str, str]) -> list[str]:
    return [p for p in placeholders(template) if not (values.get(p) or "").strip()]


# ─────────────────────────────────────────────────────────────────────────────
# Model
# ─────────────────────────────────────────────────────────────────────────────
def normalize_category(name: str) -> str | None:
    if not isinstance(name, str):
        return None
    if name in CATEGORIES:
        return name
    return _CATEGORY_ALIASES.get(name.strip().lower())


def _command_key(text: str) -> str:
    """Whitespace-insensitive identity used for duplicate detection."""
    return " ".join((text or "").split()).lower()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass(eq=False)
class Command:
    category: str
    command: str
    description: str
    favorite: bool = False
    use_count: int = 0
    last_used: str | None = None
    extra: dict = field(default_factory=dict)  # unknown keys, preserved on save

    @property
    def key(self) -> tuple[str, str, str]:
        # The same command may be listed under two descriptions (e.g. in
        # different "Section › ..." groups), so both parts form the identity.
        return (self.category, _command_key(self.command), _command_key(self.description))

    @property
    def placeholders(self) -> list[str]:
        return placeholders(self.command)

    def to_dict(self) -> dict:
        data = dict(self.extra)
        data.update({
            "command": self.command,
            "description": self.description,
            "favorite": self.favorite,
            "use_count": self.use_count,
            "last_used": self.last_used,
        })
        return data

    @classmethod
    def from_dict(cls, category: str, raw: dict) -> "Command | None":
        if not isinstance(raw, dict):
            return None
        command = str(raw.get("command") or "").strip()
        if not command:
            return None
        description = str(raw.get("description") or "").strip() or command
        # Older builds tracked copies separately; fold into last_used.
        stamps = [s for s in (raw.get("last_used"), raw.get("copied_at"))
                  if isinstance(s, str) and s]
        try:
            use_count = max(0, int(raw.get("use_count") or 0))
        except (TypeError, ValueError):
            use_count = 0
        extra = {k: v for k, v in raw.items()
                 if k not in {"command", "description", "favorite", "use_count",
                              "last_used", "copied_at", "category"}}
        return cls(category=category,
                   command=command,
                   description=description,
                   favorite=bool(raw.get("favorite", False)),
                   use_count=use_count,
                   last_used=max(stamps) if stamps else None,
                   extra=extra)


def parse_commands(data) -> list[Command]:
    """Parse any supported file layout into a flat, de-duplicated list.

    Supports the classic ``{category: [..]}`` layout (with any category
    capitalisation used by older desktop / web builds) and a wrapped
    ``{"commands": {category: [..]}}`` layout.
    """
    if isinstance(data, dict) and isinstance(data.get("commands"), dict):
        data = data["commands"]
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object of categories.")

    result: list[Command] = []
    seen: set[tuple[str, str, str]] = set()
    for raw_cat, items in data.items():
        category = normalize_category(raw_cat)
        if category is None or not isinstance(items, list):
            continue
        for raw in items:
            cmd = Command.from_dict(category, raw)
            if cmd is None or cmd.key in seen:
                continue
            seen.add(cmd.key)
            result.append(cmd)
    return result


def serialize_commands(commands: Iterable[Command]) -> dict:
    out: dict[str, list] = {c: [] for c in CATEGORIES}
    for cmd in commands:
        out.setdefault(cmd.category, []).append(cmd.to_dict())
    return out


# ─────────────────────────────────────────────────────────────────────────────
# File helpers
# ─────────────────────────────────────────────────────────────────────────────
def read_json(path: str):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def write_json_atomic(path: str, data) -> None:
    """Write to a temp file then rename, so a crash never leaves half a file."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _is_writable_dir(path: str) -> bool:
    try:
        fd, tmp = tempfile.mkstemp(prefix=".probe-", dir=path)
        os.close(fd)
        os.remove(tmp)
        return True
    except OSError:
        return False


def user_data_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, APP_NAME)
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~/Library/Application Support"), APP_NAME)
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "gam-command-bank")


def app_dir() -> str:
    """Folder containing the exe (frozen) or this source file."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(name: str) -> str:
    """Path to a file bundled with the app (PyInstaller-aware)."""
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, name)


def resolve_data_dir() -> str:
    """Pick where user data lives.

    1. ``GAM_COMMAND_BANK_HOME`` if set.
    2. The compiled exe's folder, when writable (portable, as before).
    3. A per-user application-data folder. This is also used when running
       from source so the repository's ``commands.json`` stays a clean
       built-in library instead of collecting personal usage stats.
    """
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        return os.path.abspath(os.path.expanduser(override))
    if getattr(sys, "frozen", False) and _is_writable_dir(app_dir()):
        return app_dir()
    return user_data_dir()


def builtin_library_path() -> str:
    return resource_path(DATA_FILENAME)


# ─────────────────────────────────────────────────────────────────────────────
# Store
# ─────────────────────────────────────────────────────────────────────────────
class StoreError(Exception):
    pass


class CommandStore:
    def __init__(self, path: str, library_path: str | None = None):
        self.path = path
        self.library_path = library_path
        self.commands: list[Command] = []
        # When the file on disk could not be read we refuse to save over it,
        # so a typo in a hand-edited file never wipes the user's commands.
        self.read_only = False
        self.load_message = ""

    # ── load / save ──────────────────────────────────────────────────────────
    def load(self) -> None:
        self.read_only = False
        if not os.path.exists(self.path):
            self.commands = self._load_library()
            self.load_message = (f"Created command bank with {len(self.commands)} built-in commands."
                                 if self.commands else "Starting with an empty command bank.")
            self.save()
            return
        try:
            self.commands = parse_commands(read_json(self.path))
            self.load_message = f"Loaded {len(self.commands)} commands."
        except (OSError, ValueError) as exc:
            self.commands = []
            self.read_only = True
            backup = self._preserve_corrupt_file()
            self.load_message = (f"Could not read {os.path.basename(self.path)} ({exc}). "
                                 f"Changes will not be saved until it is fixed."
                                 + (f" A copy was saved to {os.path.basename(backup)}." if backup else ""))
            raise StoreError(self.load_message) from exc

    def _load_library(self) -> list[Command]:
        if not self.library_path or not os.path.exists(self.library_path):
            return []
        if os.path.abspath(self.library_path) == os.path.abspath(self.path):
            return []
        try:
            return parse_commands(read_json(self.library_path))
        except (OSError, ValueError):
            return []

    def _preserve_corrupt_file(self) -> str | None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        root, ext = os.path.splitext(self.path)
        dest = f"{root}.corrupt-{stamp}{ext}"
        try:
            shutil.copy2(self.path, dest)
            return dest
        except OSError:
            return None

    def save(self) -> None:
        if self.read_only:
            raise StoreError("The command file could not be read, so it will not be overwritten. "
                             "Fix or remove it and choose File > Reload.")
        if os.path.exists(self.path):
            try:
                shutil.copy2(self.path, self.path + ".bak")
            except OSError:
                pass
        write_json_atomic(self.path, serialize_commands(self.commands))

    # ── queries ──────────────────────────────────────────────────────────────
    def counts(self) -> dict[str, int]:
        out = {c: 0 for c in CATEGORIES}
        for cmd in self.commands:
            out[cmd.category] = out.get(cmd.category, 0) + 1
        return out

    def find(self, category: str, command: str, description: str | None = None) -> Command | None:
        cat, cmd_key = normalize_category(category), _command_key(command)
        desc_key = None if description is None else _command_key(description)
        return next((c for c in self.commands
                     if c.category == cat and c.key[1] == cmd_key
                     and (desc_key is None or c.key[2] == desc_key)), None)

    def search(self, query: str = "", category: str | None = None,
               favorites: bool = False, recent: bool = False,
               limit: int | None = None) -> list[Command]:
        """Filter and rank commands.

        Every whitespace-separated term must appear in the description,
        command or category. Matches in the description rank above matches
        only in the command text; favorites and frequently used commands
        break ties. With no query the stored order is kept, except for the
        recent view which is newest first.
        """
        pool = [c for c in self.commands
                if (category is None or c.category == category)
                and (not favorites or c.favorite)
                and (not recent or c.last_used)]
        terms = (query or "").lower().split()

        if terms:
            scored = []
            for idx, cmd in enumerate(pool):
                desc = cmd.description.lower()
                hay = f"{desc} {cmd.command.lower()} {cmd.category.lower()}"
                if not all(t in hay for t in terms):
                    continue
                score = 0
                for t in terms:
                    if desc.startswith(t):
                        score += 4
                    elif re.search(rf"\b{re.escape(t)}", desc):
                        score += 3
                    elif t in desc:
                        score += 2
                    else:
                        score += 1
                scored.append((-score, not cmd.favorite, -cmd.use_count, idx, cmd))
            scored.sort(key=lambda s: s[:4])
            pool = [s[-1] for s in scored]
        elif recent:
            pool.sort(key=lambda c: c.last_used or "", reverse=True)

        return pool[:limit] if limit else pool

    # ── mutations ────────────────────────────────────────────────────────────
    @staticmethod
    def validate(category: str, command: str, description: str) -> tuple[str, str, str]:
        cat = normalize_category(category)
        if cat is None:
            raise ValueError(f"Unknown category: {category!r}")
        command = (command or "").strip()
        description = (description or "").strip()
        if not command:
            raise ValueError("Command cannot be empty.")
        if not description:
            raise ValueError("Description cannot be empty.")
        return cat, command, description

    def add(self, category: str, command: str, description: str) -> Command:
        cat, command, description = self.validate(category, command, description)
        if self.find(cat, command, description):
            raise ValueError(f"That command already exists in {cat} with the same description.")
        cmd = Command(cat, command, description)
        self.commands.append(cmd)
        self.save()
        return cmd

    def update(self, cmd: Command, category: str, command: str, description: str) -> None:
        cat, command, description = self.validate(category, command, description)
        existing = self.find(cat, command, description)
        if existing is not None and existing is not cmd:
            raise ValueError(f"That command already exists in {cat} with the same description.")
        cmd.category, cmd.command, cmd.description = cat, command, description
        self.save()

    def remove(self, cmd: Command) -> int:
        idx = self.commands.index(cmd)
        del self.commands[idx]
        self.save()
        return idx

    def restore(self, cmd: Command, index: int) -> None:
        """Undo a remove()."""
        self.commands.insert(min(index, len(self.commands)), cmd)
        self.save()

    def toggle_favorite(self, cmd: Command) -> bool:
        cmd.favorite = not cmd.favorite
        self.save()
        return cmd.favorite

    def mark_used(self, cmd: Command) -> None:
        """Record a copy / run. Selecting a command does not count as use."""
        cmd.use_count += 1
        cmd.last_used = _now()
        self.save()

    def clear_history(self) -> None:
        for cmd in self.commands:
            cmd.use_count = 0
            cmd.last_used = None
        self.save()

    # ── import / export ──────────────────────────────────────────────────────
    def merge(self, incoming: Iterable[Command]) -> tuple[int, int]:
        """Add commands that are not already present. Returns (added, skipped).

        Existing commands (and their favorites / usage) are never changed.
        """
        added = skipped = 0
        keys = {c.key for c in self.commands}
        for cmd in incoming:
            if cmd.key in keys:
                skipped += 1
                continue
            keys.add(cmd.key)
            self.commands.append(Command(cmd.category, cmd.command, cmd.description,
                                         favorite=cmd.favorite))
            added += 1
        if added:
            self.save()
        return added, skipped

    def import_file(self, path: str) -> tuple[int, int]:
        return self.merge(parse_commands(read_json(path)))

    def merge_library(self) -> tuple[int, int]:
        return self.merge(self._load_library())

    def export_file(self, path: str, include_usage: bool = False) -> int:
        data = serialize_commands(self.commands)
        if not include_usage:
            for items in data.values():
                for item in items:
                    item.pop("use_count", None)
                    item.pop("last_used", None)
        write_json_atomic(path, data)
        return len(self.commands)


# ─────────────────────────────────────────────────────────────────────────────
# Settings (theme, window size, remembered placeholder values)
# ─────────────────────────────────────────────────────────────────────────────
class Settings:
    DEFAULTS = {
        "theme": "dark",
        "geometry": "1120x700",
        "sash": 400,
        "filter": "All",
        "remember_values": True,
        "recent_values": {},
    }

    def __init__(self, path: str):
        self.path = path
        self.data = dict(self.DEFAULTS)
        self.data["recent_values"] = {}
        try:
            loaded = read_json(path)
            if isinstance(loaded, dict):
                self.data.update(loaded)
        except (OSError, ValueError):
            pass
        if not isinstance(self.data.get("recent_values"), dict):
            self.data["recent_values"] = {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value, save: bool = True) -> None:
        self.data[key] = value
        if save:
            self.save()

    def save(self) -> None:
        try:
            write_json_atomic(self.path, self.data)
        except OSError:
            pass  # settings are a convenience; never block the user on them

    def recent_values(self, placeholder: str) -> list[str]:
        vals = self.data["recent_values"].get(placeholder, [])
        return [v for v in vals if isinstance(v, str)]

    def remember_values(self, values: dict[str, str]) -> None:
        if not self.data.get("remember_values", True):
            return
        store = self.data["recent_values"]
        changed = False
        for name, value in values.items():
            value = (value or "").strip()
            if not value or placeholder_choices(name):
                continue
            existing = [v for v in store.get(name, []) if v != value]
            store[name] = [value] + existing[:MAX_RECENT_VALUES - 1]
            changed = True
        if changed:
            self.save()

    def clear_recent_values(self) -> None:
        self.data["recent_values"] = {}
        self.save()
