from __future__ import annotations

import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from tkinter import filedialog, messagebox, ttk

import command_store as cs
from command_store import CATEGORIES, Command, CommandStore, Settings, StoreError

GAM_REFERENCE = "https://sites.google.com/view/gam--commands/home"
CLOUD_SHELL = "https://shell.cloud.google.com/"
IS_WINDOWS = sys.platform == "win32"


# ─────────────────────────────────────────────────────────────────────────────
# Tooltip helper
# ─────────────────────────────────────────────────────────────────────────────
class Tooltip:
    def __init__(self, widget, text, colors):
        self.widget = widget
        self.text = text
        self.C = colors
        self.tip_window = None
        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")

    def show(self, event=None):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text, background=self.C["surface"], foreground=self.C["muted"],
                 relief="flat", padx=8, pady=4, borderwidth=1,
                 highlightbackground=self.C["border"], highlightthickness=1,
                 justify=tk.LEFT).pack()

    def hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


# ─────────────────────────────────────────────────────────────────────────────
# Command execution
# ─────────────────────────────────────────────────────────────────────────────
def _powershell():
    for exe in (("powershell.exe", "pwsh.exe") if IS_WINDOWS else ("pwsh", "powershell")):
        path = shutil.which(exe)
        if path:
            return path
    return None


def shell_argv(category, command):
    """argv that runs `command` locally, or None when no suitable shell exists."""
    ps = _powershell()
    if category == "GAM":
        if not shutil.which("gam"):
            return None
        if IS_WINDOWS:
            return [ps, "-NoProfile", "-NonInteractive", "-Command", command] if ps else None
        return ["/bin/sh", "-c", command]
    return [ps, "-NoProfile", "-NonInteractive", "-Command", command] if ps else None


def run_in_thread(argv, out_queue, on_start):
    """Run argv, streaming ("out", line) then ("done", code) into out_queue."""
    def worker():
        kwargs = dict(stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                      stdin=subprocess.DEVNULL, text=True,
                      encoding="utf-8", errors="replace")
        if IS_WINDOWS:
            # No console window flashing up from the windowed exe.
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            proc = subprocess.Popen(argv, **kwargs)
        except Exception as exc:
            out_queue.put(("error", str(exc)))
            return
        on_start(proc)
        for line in proc.stdout:
            out_queue.put(("out", line))
        out_queue.put(("done", proc.wait()))

    threading.Thread(target=worker, daemon=True).start()


def open_path(path):
    try:
        if IS_WINDOWS:
            os.startfile(path)  # noqa: S606 - opening a local folder
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        messagebox.showerror("Open Folder", str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# Add / Edit dialog
# ─────────────────────────────────────────────────────────────────────────────
class CommandDialog:
    def __init__(self, app, title, category, command="", description="", on_save=None):
        self.app = app
        self.on_save = on_save
        C, F = app.C, app.F
        self.win = win = tk.Toplevel(app.root)
        win.title(title)
        win.configure(bg=C["bg"])
        win.transient(app.root)
        win.resizable(True, False)
        win.minsize(560, 0)

        tk.Frame(win, bg=C["primary"], height=2).pack(fill=tk.X)
        body = tk.Frame(win, bg=C["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=18, pady=14)
        body.columnconfigure(1, weight=1)

        def label(text, row):
            tk.Label(body, text=text, font=F["small"], fg=C["muted"], bg=C["bg"],
                     anchor=tk.W).grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=(6, 0))

        label("Category", 0)
        self.cat_var = tk.StringVar(value=category)
        ttk.Combobox(body, textvariable=self.cat_var, values=CATEGORIES, state="readonly",
                     width=16).grid(row=0, column=1, sticky="w", pady=4)

        label("Description", 1)
        self.desc_var = tk.StringVar(value=description)
        self.desc_entry = app.make_entry(body, self.desc_var, F["base"])
        self.desc_entry.grid(row=1, column=1, sticky="ew", pady=4, ipady=3)

        label("Command", 2)
        self.cmd_text = tk.Text(body, height=4, wrap=tk.WORD, font=F["mono"],
                                bg=C["surface2"], fg=C["text"], insertbackground=C["primary"],
                                relief="flat", highlightthickness=1, undo=True,
                                highlightbackground=C["border"], highlightcolor=C["primary"],
                                padx=8, pady=6)
        self.cmd_text.grid(row=2, column=1, sticky="ew", pady=4)
        self.cmd_text.insert("1.0", command)

        self.hint = tk.Label(body, font=F["small"], fg=C["dim"], bg=C["bg"], anchor=tk.W,
                             justify=tk.LEFT, wraplength=460)
        self.hint.grid(row=3, column=1, sticky="w")
        self.error = tk.Label(body, font=F["small"], fg=C["danger"], bg=C["bg"], anchor=tk.W,
                              justify=tk.LEFT, wraplength=460)
        self.error.grid(row=4, column=1, sticky="w", pady=(4, 0))

        btns = tk.Frame(body, bg=C["bg"])
        btns.grid(row=5, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(btns, text="Cancel", style="Gh.TButton", command=win.destroy).pack(side=tk.RIGHT)
        ttk.Button(btns, text="Save", style="P.TButton", command=self.save).pack(side=tk.RIGHT, padx=(0, 8))

        self.cmd_text.bind("<KeyRelease>", lambda e: self._update_hint())
        self.cmd_text.bind("<Control-Return>", lambda e: (self.save(), "break")[1])
        self.desc_entry.bind("<Return>", lambda e: self.save())
        win.bind("<Escape>", lambda e: win.destroy())
        self._update_hint()

        win.update_idletasks()
        x = app.root.winfo_rootx() + (app.root.winfo_width() - win.winfo_width()) // 2
        y = app.root.winfo_rooty() + 80
        win.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        win.grab_set()
        (self.cmd_text if not command else self.desc_entry).focus_set()

    def _update_hint(self):
        names = cs.placeholders(self.cmd_text.get("1.0", tk.END))
        if names:
            self.hint.config(text="Fields: " + ", ".join(f"<{n}>" for n in names))
        else:
            self.hint.config(text="Tip: use <name> for values you fill in each time, "
                                  "or <a|b|c> for a pick-list.  Ctrl+Enter saves.")

    def save(self):
        try:
            self.on_save(self.cat_var.get(), self.cmd_text.get("1.0", tk.END),
                         self.desc_var.get())
        except (ValueError, StoreError) as exc:
            self.error.config(text=str(exc))
            return
        self.win.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────────────────────────────────────
class CommandManager:

    DARK = {
        "bg": "#0D1117", "surface": "#161B22", "surface2": "#21262D", "border": "#30363D",
        "primary": "#2F81F7", "primary_dk": "#1F6FEB", "success": "#3FB950", "success_dk": "#2EA043",
        "danger": "#F85149", "danger_dk": "#DA3633", "warning": "#D29922", "warning_dk": "#BB8009",
        "text": "#E6EDF3", "muted": "#8B949E", "dim": "#6E7681", "accent": "#58A6FF",
        "star": "#E3B341", "on_primary": "#FFFFFF",
    }
    LIGHT = {
        "bg": "#F6F8FA", "surface": "#FFFFFF", "surface2": "#EFF2F5", "border": "#D0D7DE",
        "primary": "#0969DA", "primary_dk": "#0550AE", "success": "#1A7F37", "success_dk": "#116329",
        "danger": "#CF222E", "danger_dk": "#A40E26", "warning": "#9A6700", "warning_dk": "#7D4E00",
        "text": "#1F2328", "muted": "#636C76", "dim": "#8C959F", "accent": "#0969DA",
        "star": "#BF8700", "on_primary": "#FFFFFF",
    }
    FILTERS = ("All", "Favorites", "Recent") + CATEGORIES

    def __init__(self, root):
        self.root = root
        root.title(cs.APP_NAME)
        root.minsize(900, 560)
        self._set_icon()

        data_dir = cs.resolve_data_dir()
        self.settings = Settings(os.path.join(data_dir, cs.SETTINGS_FILENAME))
        self.store = CommandStore(os.path.join(data_dir, cs.DATA_FILENAME),
                                  cs.builtin_library_path())

        root.geometry(self.settings.get("geometry") or "1120x700")
        self._is_dark = self.settings.get("theme") != "light"
        self.C = dict(self.DARK if self._is_dark else self.LIGHT)
        self._init_fonts()

        self.filter = self.settings.get("filter") if self.settings.get("filter") in self.FILTERS else "All"
        self.current: Command | None = None
        self.values: dict[str, str] = {}     # placeholder values, shared across commands
        self.param_vars: dict[str, tk.StringVar] = {}
        self.param_widgets: list[tk.Widget] = []
        self._iid_to_cmd: dict[str, Command] = {}
        self._status_job = None
        self._last_deleted = None
        self._proc = None
        self._run_queue: queue.Queue = queue.Queue()

        self.style = ttk.Style()
        self._build_all()
        self._bind_keys()
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.load_all_commands()

    # =========================================================================
    # SETUP
    # =========================================================================
    def _set_icon(self):
        try:
            icon_path = cs.resource_path("icon.ico")
            if IS_WINDOWS and os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

    def _init_fonts(self):
        families = set(tkfont.families(self.root))
        ui = next((f for f in ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Cantarell",
                               "DejaVu Sans") if f in families), "TkDefaultFont")
        mono = next((f for f in ("Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono")
                     if f in families), "TkFixedFont")
        self.F = {
            "base": (ui, 10), "bold": (ui, 10, "bold"), "small": (ui, 9),
            "tiny": (ui, 8), "label": (ui, 8, "bold"), "title": (ui, 13, "bold"),
            "heading": (ui, 12, "bold"), "icon": (ui, 13), "mono": (mono, 10),
        }

    def _configure_style(self):
        s, C, F = self.style, self.C, self.F
        s.theme_use("clam")
        s.configure(".", background=C["bg"], foreground=C["text"], font=F["base"],
                    bordercolor=C["border"], lightcolor=C["surface2"], darkcolor=C["surface2"],
                    troughcolor=C["surface"], focuscolor=C["primary"])
        s.configure("TFrame", background=C["bg"])

        for name in ("TEntry", "TCombobox"):
            s.configure(name, foreground=C["text"], fieldbackground=C["surface2"],
                        background=C["surface2"], insertcolor=C["primary"],
                        arrowcolor=C["muted"], bordercolor=C["border"], padding=4)
            s.map(name, bordercolor=[("focus", C["primary"])],
                  fieldbackground=[("readonly", C["surface2"])],
                  foreground=[("readonly", C["text"])],
                  selectbackground=[("readonly", C["surface2"])],
                  selectforeground=[("readonly", C["text"])])

        s.configure("TScrollbar", background=C["surface2"], troughcolor=C["surface"],
                    arrowcolor=C["dim"], borderwidth=0, relief="flat")
        s.map("TScrollbar", background=[("active", C["border"])])

        s.configure("Treeview", background=C["surface"], fieldbackground=C["surface"],
                    foreground=C["text"], rowheight=28, borderwidth=0, font=F["base"])
        s.map("Treeview", background=[("selected", C["primary"])],
              foreground=[("selected", C["on_primary"])])
        s.configure("Treeview.Heading", background=C["surface2"], foreground=C["muted"],
                    relief="flat", font=F["label"], padding=(6, 4))
        s.map("Treeview.Heading", background=[("active", C["border"])])
        s.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

        def btn(name, bg, hover, fg="#FFFFFF", pad=(12, 6)):
            s.configure(f"{name}.TButton", font=F["bold"], foreground=fg, background=bg,
                        relief="flat", borderwidth=0, padding=list(pad), focuscolor=bg,
                        width=-5)
            s.map(f"{name}.TButton", background=[("disabled", C["surface2"]),
                                                 ("active", hover), ("pressed", hover)],
                  foreground=[("disabled", C["dim"]), ("active", fg)])

        btn("P", C["primary"], C["primary_dk"])
        btn("G", C["success"], C["success_dk"])
        btn("R", C["danger"], C["danger_dk"])
        btn("Gh", C["surface2"], C["border"], fg=C["text"], pad=(10, 5))

        self.root.option_add("*TCombobox*Listbox*Background", C["surface2"])
        self.root.option_add("*TCombobox*Listbox*Foreground", C["text"])
        self.root.option_add("*TCombobox*Listbox*selectBackground", C["primary"])
        self.root.option_add("*TCombobox*Listbox*selectForeground", "#FFFFFF")

    def make_entry(self, parent, var, font=None):
        C = self.C
        return tk.Entry(parent, textvariable=var, font=font or self.F["mono"],
                        bg=C["surface2"], fg=C["text"], insertbackground=C["primary"],
                        relief="flat", highlightthickness=1,
                        highlightbackground=C["border"], highlightcolor=C["primary"])

    def tip(self, widget, text):
        Tooltip(widget, text, self.C)

    # =========================================================================
    # MENU
    # =========================================================================
    def _create_menu(self):
        C = self.C
        kw = dict(bg=C["surface"], fg=C["text"], activebackground=C["primary"],
                  activeforeground="#fff", borderwidth=0, relief="flat", tearoff=0)
        menubar = tk.Menu(self.root, **{k: v for k, v in kw.items() if k != "tearoff"})

        m = tk.Menu(menubar, **kw)
        m.add_command(label="New Command…", accelerator="Ctrl+N", command=self.new_command)
        m.add_separator()
        m.add_command(label="Import Commands…", command=self.import_commands)
        m.add_command(label="Export Commands…", command=self.export_commands)
        m.add_command(label="Add Missing Built-in Commands", command=self.merge_library)
        m.add_separator()
        m.add_command(label="Open Data Folder", command=lambda: open_path(os.path.dirname(self.store.path)))
        m.add_command(label="Reload", accelerator="F5", command=self.load_all_commands)
        m.add_separator()
        m.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=m)

        m = tk.Menu(menubar, **kw)
        m.add_command(label="Edit Command…", accelerator="Ctrl+E", command=self.edit_command)
        m.add_command(label="Toggle Favorite", accelerator="Ctrl+D", command=self.toggle_favorite)
        m.add_command(label="Delete Command", accelerator="Del", command=self.delete_command)
        m.add_command(label="Undo Delete", accelerator="Ctrl+Z", command=self.undo_delete)
        m.add_separator()
        m.add_command(label="Clear Usage History", command=self.clear_history)
        m.add_command(label="Forget Remembered Field Values", command=self.clear_recent_values)
        menubar.add_cascade(label="Edit", menu=m)

        m = tk.Menu(menubar, **kw)
        for i, f in enumerate(self.FILTERS, 1):
            m.add_command(label=self._filter_label(f, counts=False), accelerator=f"Ctrl+{i}",
                          command=lambda f=f: self.set_filter(f))
        m.add_separator()
        m.add_command(label="Toggle Light / Dark", accelerator="Ctrl+T", command=self._toggle_theme)
        menubar.add_cascade(label="View", menu=m)

        m = tk.Menu(menubar, **kw)
        m.add_command(label="GAM People", command=lambda: webbrowser.open("https://sites.google.com/view/gam--commands/people"))
        m.add_command(label="GAM Services", command=lambda: webbrowser.open("https://sites.google.com/view/gam--commands/services"))
        m.add_command(label="GAM Full Reference", command=lambda: webbrowser.open(GAM_REFERENCE))
        m.add_command(label="Google Cloud Shell", command=lambda: webbrowser.open(CLOUD_SHELL))
        menubar.add_cascade(label="Reference", menu=m)

        m = tk.Menu(menubar, **kw)
        m.add_command(label="Keyboard Shortcuts", accelerator="F1", command=self._show_shortcuts)
        m.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=m)

        self.root.config(menu=menubar)

    # =========================================================================
    # LAYOUT
    # =========================================================================
    def _build_all(self):
        self.root.configure(bg=self.C["bg"])
        self._configure_style()
        self._create_menu()
        self._create_header()
        self._create_status_bar()
        self._create_body()

    def _create_header(self):
        C, F = self.C, self.F
        hbar = tk.Frame(self.root, bg=C["surface"], height=50)
        hbar.pack(fill=tk.X)
        hbar.pack_propagate(False)
        tk.Frame(hbar, bg=C["primary"], width=3).pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(hbar, text=cs.APP_NAME, font=F["title"], fg=C["text"], bg=C["surface"],
                 padx=14).pack(side=tk.LEFT)
        tk.Label(hbar, text=f"v{cs.APP_VERSION}", font=F["tiny"], fg=C["muted"],
                 bg=C["surface"]).pack(side=tk.LEFT)

        theme_btn = tk.Label(hbar, text="☽" if self._is_dark else "☀", font=F["icon"],
                             fg=C["muted"], bg=C["surface"], cursor="hand2", padx=10)
        theme_btn.pack(side=tk.RIGHT, padx=(0, 6))
        theme_btn.bind("<Button-1>", lambda e: self._toggle_theme())
        self.tip(theme_btn, "Toggle light / dark (Ctrl+T)")

        new_btn = ttk.Button(hbar, text="＋ New", style="G.TButton", command=self.new_command)
        new_btn.pack(side=tk.RIGHT, padx=(0, 10))
        self.tip(new_btn, "Add a command (Ctrl+N)")

        # search box with inline hint and clear button
        box = tk.Frame(hbar, bg=C["surface2"], highlightthickness=1,
                       highlightbackground=C["border"], highlightcolor=C["primary"])
        box.pack(side=tk.RIGHT, pady=10, padx=(0, 10))
        tk.Label(box, text="⌕", font=F["icon"], fg=C["muted"], bg=C["surface2"],
                 padx=6).pack(side=tk.LEFT)
        self.search_var = getattr(self, "search_var", None) or tk.StringVar()
        self.search_entry = tk.Entry(box, textvariable=self.search_var, width=34, font=F["base"],
                                     bg=C["surface2"], fg=C["text"], relief="flat",
                                     insertbackground=C["primary"], highlightthickness=0)
        self.search_entry.pack(side=tk.LEFT, ipady=4)
        self._search_hint = tk.Label(box, text="Search all commands   Ctrl+F", font=F["small"],
                                     fg=C["dim"], bg=C["surface2"])
        self._search_hint.bind("<Button-1>", lambda e: self.search_entry.focus_set())
        clr = tk.Label(box, text="✕", font=F["small"], fg=C["muted"], bg=C["surface2"],
                       cursor="hand2", padx=8)
        clr.pack(side=tk.LEFT)
        clr.bind("<Button-1>", lambda e: self._clear_search())
        self.search_entry.bind("<FocusIn>", lambda e: box.config(highlightbackground=C["primary"]))
        self.search_entry.bind("<FocusOut>", lambda e: box.config(highlightbackground=C["border"]))
        self.search_entry.bind("<Down>", lambda e: self._focus_list())
        self.search_entry.bind("<Return>", lambda e: self._activate_first())
        self.search_entry.bind("<Escape>", lambda e: self._clear_search())
        self._search_trace = self.search_var.trace_add("write", lambda *_: self._on_search())
        self._update_search_hint()

    def _create_body(self):
        C, F = self.C, self.F
        self.paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=C["border"],
                                    sashwidth=4, bd=0, relief="flat", opaqueresize=True)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # ── left: filters + list ─────────────────────────────────────────────
        left = tk.Frame(self.paned, bg=C["bg"])
        self.paned.add(left, minsize=300, width=int(self.settings.get("sash") or 400))

        chips = tk.Frame(left, bg=C["bg"])
        chips.pack(fill=tk.X, padx=10, pady=(10, 6))
        self.chip_widgets = {}
        for i, f in enumerate(self.FILTERS):
            chip = tk.Label(chips, font=F["small"], padx=9, pady=3, cursor="hand2")
            chip.grid(row=i // 3, column=i % 3, sticky="ew", padx=2, pady=2)
            chip.bind("<Button-1>", lambda e, f=f: self.set_filter(f))
            self.chip_widgets[f] = chip
        for col in range(3):
            chips.columnconfigure(col, weight=1)

        tree_wrap = tk.Frame(left, bg=C["surface"], highlightthickness=1,
                             highlightbackground=C["border"])
        tree_wrap.pack(fill=tk.BOTH, expand=True, padx=10)
        self.tree = ttk.Treeview(tree_wrap, columns=("fav", "desc", "cat"), show="headings",
                                 selectmode="browse")
        self.tree.heading("fav", text="★")
        self.tree.heading("desc", text="DESCRIPTION", anchor=tk.W)
        self.tree.heading("cat", text="TYPE", anchor=tk.W)
        self.tree.column("fav", width=28, minwidth=28, stretch=False, anchor=tk.CENTER)
        self.tree.column("desc", width=260, anchor=tk.W)
        self.tree.column("cat", width=92, minwidth=60, stretch=False, anchor=tk.W)
        vsb = ttk.Scrollbar(tree_wrap, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._on_tree_select())
        self.tree.bind("<Return>", lambda e: self._focus_first_param())
        self.tree.bind("<Double-Button-1>", lambda e: self._focus_first_param())
        self.tree.bind("<Delete>", lambda e: self.delete_command())

        self.list_info = tk.Label(left, font=F["tiny"], fg=C["dim"], bg=C["bg"], anchor=tk.W)
        self.list_info.pack(fill=tk.X, padx=12, pady=(4, 8))

        # ── right: detail ────────────────────────────────────────────────────
        right = tk.Frame(self.paned, bg=C["bg"])
        self.paned.add(right, minsize=440)
        self.detail = right
        self._build_detail(right)

    def _section(self, parent, text):
        lbl = tk.Label(parent, text=text, font=self.F["label"], fg=self.C["muted"],
                       bg=self.C["surface"], anchor=tk.W)
        lbl.pack(fill=tk.X, pady=(10, 4))
        return lbl

    def _build_detail(self, parent):
        C, F = self.C, self.F

        # empty state
        self.empty = tk.Frame(parent, bg=C["bg"])
        tk.Label(self.empty, text="Pick a command", font=F["heading"], fg=C["text"],
                 bg=C["bg"]).pack(pady=(120, 6))
        tk.Label(self.empty, bg=C["bg"], fg=C["muted"], font=F["small"], justify=tk.CENTER,
                 text="Search with Ctrl+F, use ↑ ↓ to move through the list,\n"
                      "Enter to fill in fields, Ctrl+Enter to copy.").pack()

        # command card
        self.card = card = tk.Frame(parent, bg=C["surface"], highlightthickness=1,
                                    highlightbackground=C["border"])
        tk.Frame(card, bg=C["primary"], height=2).pack(fill=tk.X)
        inner = tk.Frame(card, bg=C["surface"])
        inner.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        top = tk.Frame(inner, bg=C["surface"])
        top.pack(fill=tk.X)
        self.badge = tk.Label(top, font=F["label"], fg=C["on_primary"], bg=C["primary"], padx=6, pady=1)
        self.badge.pack(side=tk.LEFT, anchor=tk.N, pady=(4, 0))
        self.title_lbl = tk.Label(top, font=F["heading"], fg=C["text"], bg=C["surface"],
                                  anchor=tk.W, justify=tk.LEFT, padx=10)
        self.title_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        top.bind("<Configure>", lambda e: self.title_lbl.config(wraplength=max(e.width - 260, 200)))

        del_btn = ttk.Button(top, text="Delete", style="Gh.TButton", command=self.delete_command)
        del_btn.pack(side=tk.RIGHT, padx=(6, 0))
        self.tip(del_btn, "Delete command (Del) — undo with Ctrl+Z")
        edit_btn = ttk.Button(top, text="Edit", style="Gh.TButton", command=self.edit_command)
        edit_btn.pack(side=tk.RIGHT, padx=(6, 0))
        self.tip(edit_btn, "Edit command (Ctrl+E)")
        self.fav_btn = tk.Label(top, text="☆", font=F["icon"], fg=C["star"], bg=C["surface"],
                                cursor="hand2", padx=6)
        self.fav_btn.pack(side=tk.RIGHT)
        self.fav_btn.bind("<Button-1>", lambda e: self.toggle_favorite())
        self.tip(self.fav_btn, "Toggle favorite (Ctrl+D)")

        self.meta_lbl = tk.Label(inner, font=F["tiny"], fg=C["dim"], bg=C["surface"], anchor=tk.W)
        self.meta_lbl.pack(fill=tk.X, pady=(4, 0))

        self.params_section = tk.Frame(inner, bg=C["surface"])
        self.params_section.pack(fill=tk.X)
        self._section(self.params_section, "FIELDS")
        self.params_frame = tk.Frame(self.params_section, bg=C["surface"])
        self.params_frame.pack(fill=tk.X)
        self.params_frame.columnconfigure(1, weight=1)

        self.command_label = self._section(inner, "COMMAND")
        out_wrap = tk.Frame(inner, bg=C["surface2"], highlightthickness=1,
                            highlightbackground=C["border"])
        out_wrap.pack(fill=tk.X)
        self.preview = tk.Text(out_wrap, height=4, font=F["mono"], bg=C["surface2"], fg=C["text"],
                               selectbackground=C["primary"], relief="flat", borderwidth=0,
                               wrap=tk.WORD, padx=10, pady=8, cursor="xterm")
        self.preview.pack(fill=tk.X)
        self.preview.tag_configure("value", foreground=C["accent"])
        self.preview.tag_configure("missing", foreground=C["warning"])
        # read-only but still selectable
        self.preview.bind("<Key>", lambda e: None if (e.state & 0x4 and e.keysym.lower() in ("c", "a")) else "break")

        act = tk.Frame(inner, bg=C["surface"])
        act.pack(fill=tk.X, pady=(10, 0))
        copy_btn = ttk.Button(act, text="⎘ Copy", style="P.TButton", command=self.copy_command)
        copy_btn.pack(side=tk.LEFT)
        self.tip(copy_btn, "Copy the finished command (Ctrl+Enter)")
        self.run_btn = ttk.Button(act, text="▶ Run", style="G.TButton", command=self.run_command)
        self.run_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.run_tip = Tooltip(self.run_btn, "", C)
        self.stop_btn = ttk.Button(act, text="■ Stop", style="R.TButton", command=self.stop_command)
        self.reset_btn = ttk.Button(act, text="Clear Fields", style="Gh.TButton", command=self.reset_fields)
        self.docs_link = tk.Label(act, text="↗ GAM reference", font=F["small"], fg=C["accent"],
                                  bg=C["surface"], cursor="hand2")
        self.docs_link.bind("<Button-1>", lambda e: webbrowser.open(GAM_REFERENCE))

        # output console (shown after a run)
        self.output_section = tk.Frame(inner, bg=C["surface"])
        head = tk.Frame(self.output_section, bg=C["surface"])
        head.pack(fill=tk.X, pady=(12, 4))
        tk.Label(head, text="OUTPUT", font=F["label"], fg=C["muted"], bg=C["surface"]).pack(side=tk.LEFT)
        hide = tk.Label(head, text="Hide", font=F["small"], fg=C["accent"], bg=C["surface"], cursor="hand2")
        hide.pack(side=tk.RIGHT)
        hide.bind("<Button-1>", lambda e: self.output_section.pack_forget())
        clear = tk.Label(head, text="Clear", font=F["small"], fg=C["accent"], bg=C["surface"], cursor="hand2")
        clear.pack(side=tk.RIGHT, padx=10)
        clear.bind("<Button-1>", lambda e: self._clear_output())
        con_wrap = tk.Frame(self.output_section, bg=C["bg"], highlightthickness=1,
                            highlightbackground=C["border"])
        con_wrap.pack(fill=tk.BOTH, expand=True)
        self.console = tk.Text(con_wrap, font=F["mono"], bg=C["bg"], fg=C["text"], height=8,
                               relief="flat", borderwidth=0, wrap=tk.NONE, padx=10, pady=6,
                               state=tk.DISABLED)
        cvsb = ttk.Scrollbar(con_wrap, orient=tk.VERTICAL, command=self.console.yview)
        chsb = ttk.Scrollbar(con_wrap, orient=tk.HORIZONTAL, command=self.console.xview)
        self.console.configure(yscrollcommand=cvsb.set, xscrollcommand=chsb.set)
        cvsb.pack(side=tk.RIGHT, fill=tk.Y)
        chsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.console.pack(fill=tk.BOTH, expand=True)
        self.console.tag_configure("cmd", foreground=C["accent"])
        self.console.tag_configure("ok", foreground=C["success"])
        self.console.tag_configure("err", foreground=C["danger"])

        self._show_detail(None)

    def _create_status_bar(self):
        C, F = self.C, self.F
        sb = tk.Frame(self.root, bg=C["surface"], height=26)
        sb.pack(side=tk.BOTTOM, fill=tk.X)
        sb.pack_propagate(False)
        tk.Frame(sb, bg=C["border"], height=1).pack(fill=tk.X, side=tk.TOP)
        self.status_bar = tk.Label(sb, text="Ready", anchor=tk.W, font=F["tiny"],
                                   fg=C["muted"], bg=C["surface"], padx=12)
        self.status_bar.pack(side=tk.LEFT, fill=tk.Y)
        self.path_label = tk.Label(sb, anchor=tk.E, font=F["tiny"], fg=C["dim"],
                                   bg=C["surface"], padx=12, cursor="hand2")
        self.path_label.pack(side=tk.RIGHT, fill=tk.Y)
        self.path_label.bind("<Button-1>", lambda e: open_path(os.path.dirname(self.store.path)))
        self.tip(self.path_label, "Where your commands are saved — click to open the folder")

    # =========================================================================
    # KEYS
    # =========================================================================
    def _bind_keys(self):
        r = self.root

        def main_window(fn, skip_text=False):
            # Shortcuts only apply in the main window (not in dialogs), and
            # optionally leave text fields their own meaning for the key.
            def handler(event):
                try:
                    if event.widget.winfo_toplevel() is not r:
                        return None
                except (AttributeError, KeyError, tk.TclError):
                    return None
                if skip_text and isinstance(event.widget, (tk.Entry, tk.Text, ttk.Entry)) \
                        and event.widget is not self.preview:
                    return None
                fn()
                return "break"
            return handler

        keys = {
            "<Control-f>": self._focus_search,
            "<Control-n>": self.new_command,
            "<Control-e>": self.edit_command,
            "<Control-d>": self.toggle_favorite,
            "<Control-Return>": self.copy_command,
            "<Control-r>": self.run_command,
            "<Control-t>": self._toggle_theme,
            "<F5>": self.load_all_commands,
            "<F1>": self._show_shortcuts,
        }
        for seq, fn in keys.items():
            r.bind_all(seq, main_window(fn))
        r.bind_all("<Control-z>", main_window(self.undo_delete, skip_text=True))
        for i, f in enumerate(self.FILTERS, 1):
            r.bind_all(f"<Control-Key-{i}>", main_window(lambda f=f: self.set_filter(f)))

    # =========================================================================
    # LIST / FILTER / SEARCH
    # =========================================================================
    def _filter_label(self, f, counts=True):
        n = ""
        if counts:
            c = self.store.counts()
            n = {
                "All": len(self.store.commands),
                "Favorites": sum(1 for x in self.store.commands if x.favorite),
                "Recent": None,
            }.get(f, c.get(f, 0))
            n = f"  {n}" if n is not None else ""
        icon = {"Favorites": "★ ", "Recent": "⌚ "}.get(f, "")
        return f"{icon}{f}{n}"

    def _paint_chips(self):
        C = self.C
        for f, chip in self.chip_widgets.items():
            active = f == self.filter
            chip.config(text=self._filter_label(f),
                        bg=C["primary"] if active else C["surface2"],
                        fg=C["on_primary"] if active else C["muted"])

    def set_filter(self, f):
        self.filter = f
        self.settings.set("filter", f)
        self.refresh_list()
        return "break"

    def _query(self):
        return self.search_var.get().strip()

    def _on_search(self):
        self._update_search_hint()
        self.refresh_list(keep_selection=False)

    def _update_search_hint(self):
        if self.search_var.get():
            self._search_hint.place_forget()
        else:
            self._search_hint.place(in_=self.search_entry, x=2, rely=0.5, anchor=tk.W)

    def _clear_search(self):
        self.search_var.set("")
        self.search_entry.focus_set()

    def _focus_search(self):
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)
        return "break"

    def refresh_list(self, keep_selection=True):
        f = self.filter
        results = self.store.search(
            self._query(),
            category=f if f in CATEGORIES else None,
            favorites=(f == "Favorites"),
            recent=(f == "Recent"),
            limit=50 if f == "Recent" else None,
        )
        # The type column is redundant when viewing a single category.
        self.tree.configure(displaycolumns=("fav", "desc") if f in CATEGORIES else ("fav", "desc", "cat"))
        self.tree.delete(*self.tree.get_children())
        self._iid_to_cmd = {}
        for cmd in results:
            iid = str(id(cmd))
            self._iid_to_cmd[iid] = cmd
            self.tree.insert("", tk.END, iid=iid,
                             values=("★" if cmd.favorite else "", cmd.description, cmd.category))
        self._paint_chips()

        total = len(self.store.commands)
        where = "" if f == "All" else f" in {f}"
        q = self._query()
        if q:
            self.list_info.config(text=f"{len(results)} match{'es' if len(results) != 1 else ''} for “{q}”{where}")
        elif not results and f == "Favorites":
            self.list_info.config(text="No favorites yet — select a command and press ☆ or Ctrl+D.")
        elif not results and f == "Recent":
            self.list_info.config(text="Nothing used yet — copied and run commands show up here.")
        else:
            self.list_info.config(text=f"{len(results)} of {total} commands{where}")

        cur_iid = str(id(self.current)) if self.current else None
        if cur_iid in self._iid_to_cmd and (keep_selection or not q):
            self._select(self.current)
        elif q and results:
            # While searching, preview the best match without stealing focus.
            self._select(results[0])
        else:
            self._show_detail(None)

    def _select(self, cmd):
        iid = str(id(cmd))
        if iid in self._iid_to_cmd:
            self.tree.selection_set(iid)
            self.tree.focus(iid)
            self.tree.see(iid)
            return True
        return False

    def _focus_list(self):
        kids = self.tree.get_children()
        if not kids:
            return "break"
        target = self.tree.selection()[0] if self.tree.selection() else kids[0]
        self.tree.selection_set(target)
        self.tree.focus(target)
        self.tree.focus_set()
        self.tree.see(target)
        return "break"

    def _activate_first(self):
        kids = self.tree.get_children()
        if kids:
            if not self.tree.selection():
                self.tree.selection_set(kids[0])
            self._focus_first_param()
        return "break"

    def _on_tree_select(self):
        sel = self.tree.selection()
        cmd = self._iid_to_cmd.get(sel[0]) if sel else None
        if cmd is not self.current:
            self._show_detail(cmd)

    # =========================================================================
    # DETAIL PANE
    # =========================================================================
    def _show_detail(self, cmd):
        self._capture_values()
        self.current = cmd
        if cmd is None:
            self.card.pack_forget()
            self.empty.pack(fill=tk.BOTH, expand=True)
            return
        self.empty.pack_forget()
        self.card.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        C = self.C
        self.badge.config(text=cmd.category)
        self.title_lbl.config(text=cmd.description)
        self.fav_btn.config(text="★" if cmd.favorite else "☆")
        meta = []
        if cmd.use_count:
            meta.append(f"Used {cmd.use_count}×")
        if cmd.last_used:
            meta.append("last " + cmd.last_used[:16].replace("T", " "))
        self.meta_lbl.config(text="   ·   ".join(meta))

        # rebuild field inputs
        for w in self.param_widgets:
            w.destroy()
        self.param_widgets, self.param_vars = [], {}
        names = cmd.placeholders
        if names:
            self.params_section.pack(fill=tk.X, before=self.command_label)
        else:
            self.params_section.pack_forget()
        for row, name in enumerate(names):
            choices = cs.placeholder_choices(name)
            label = "choose one" if choices else name
            lbl = tk.Label(self.params_frame, text=label, font=self.F["small"], fg=C["muted"],
                           bg=C["surface"], anchor=tk.W)
            lbl.grid(row=row, column=0, sticky="w", padx=(0, 12), pady=3)
            var = tk.StringVar(value=self.values.get(name, ""))
            if choices:
                w = ttk.Combobox(self.params_frame, textvariable=var, values=choices,
                                 state="readonly", font=self.F["mono"])
            else:
                # editable, with previously used values in the drop-down
                w = ttk.Combobox(self.params_frame, textvariable=var, font=self.F["mono"],
                                 values=self.settings.recent_values(name))
            w.grid(row=row, column=1, sticky="ew", pady=3)
            var.trace_add("write", lambda *_: self._render_preview())
            w.bind("<Return>", lambda e, r=row: self._next_field(r))
            self.param_vars[name] = var
            self.param_widgets += [lbl, w]

        if names:
            self.reset_btn.pack(side=tk.LEFT, padx=(8, 0))
        else:
            self.reset_btn.pack_forget()
        if cmd.category == "GAM":
            self.docs_link.pack(side=tk.RIGHT)
        else:
            self.docs_link.pack_forget()
        self._update_run_button()
        self._render_preview()

    def _next_field(self, row):
        entries = self.param_widgets[1::2]
        if row + 1 < len(entries):
            entries[row + 1].focus_set()
        else:
            self.copy_command()
        return "break"

    def _focus_first_param(self):
        if self.current is None:
            self._on_tree_select()
        entries = self.param_widgets[1::2]
        if entries:
            empty = next((e for e, n in zip(entries, self.param_vars)
                          if not self.param_vars[n].get().strip()), entries[0])
            empty.focus_set()
        else:
            self.copy_command()
        return "break"

    def _capture_values(self):
        for name, var in self.param_vars.items():
            self.values[name] = var.get()

    def _current_values(self):
        return {n: v.get() for n, v in self.param_vars.items()}

    def built_command(self):
        if not self.current:
            return ""
        return cs.fill(self.current.command, self._current_values()).strip()

    def _render_preview(self):
        if not self.current:
            return
        values = self._current_values()
        template = self.current.command
        t = self.preview
        t.delete("1.0", tk.END)
        pos = 0
        for m in cs.PLACEHOLDER_RE.finditer(template):
            t.insert(tk.END, template[pos:m.start()])
            val = (values.get(m.group(1)) or "").strip()
            t.insert(tk.END, val or m.group(0), "value" if val else "missing")
            pos = m.end()
        t.insert(tk.END, template[pos:])
        lines = int(t.index("end-1c").split(".")[0])
        t.config(height=min(max(lines, 2), 10))

    def reset_fields(self):
        for var in self.param_vars.values():
            var.set("")
        self.values = {}
        entries = self.param_widgets[1::2]
        if entries:
            entries[0].focus_set()

    def _update_run_button(self):
        cmd = self.current
        if not cmd:
            return
        if cmd.category == "GAM" and shell_argv("GAM", "") is None:
            self.run_btn.config(text="↗ Cloud Shell")
            self.run_tip.text = "GAM isn't installed on this PC.\nCopies the command and opens Google Cloud Shell."
        elif shell_argv(cmd.category, "") is None:
            self.run_btn.config(text="▶ Run")
            self.run_tip.text = "PowerShell was not found on this system."
        else:
            self.run_btn.config(text="▶ Run")
            self.run_tip.text = "Run on this computer (Ctrl+R).\nYou'll be asked to confirm first."
        running = self._proc is not None
        self.run_btn.state(["disabled"] if running else ["!disabled"])
        if running:
            self.stop_btn.pack(side=tk.LEFT, padx=(8, 0), after=self.run_btn)
        else:
            self.stop_btn.pack_forget()

    # =========================================================================
    # ACTIONS
    # =========================================================================
    def _require_complete(self):
        """Return the finished command, or None after pointing at the empty field."""
        if not self.current:
            self.set_status("Select a command first.")
            return None
        missing = cs.missing_values(self.current.command, self._current_values())
        if missing:
            self.set_status(f"Fill in: {', '.join(missing)}")
            names = list(self.param_vars)
            self.param_widgets[1::2][names.index(missing[0])].focus_set()
            return None
        return self.built_command()

    def _record_use(self):
        self._capture_values()
        self.settings.remember_values(self._current_values())
        self._safe(self.store.mark_used, self.current)
        self.meta_lbl.config(text=f"Used {self.current.use_count}×   ·   last {self.current.last_used[:16].replace('T', ' ')}")
        if self.filter == "Recent":
            self.refresh_list()
        # refresh remembered values in the dropdowns
        for (name, var), w in zip(self.param_vars.items(), self.param_widgets[1::2]):
            if not cs.placeholder_choices(name):
                w.configure(values=self.settings.recent_values(name))

    def copy_command(self):
        text = self._require_complete()
        if text is None:
            return "break"
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._record_use()
        self.set_status("⎘ Copied to clipboard.")
        return "break"

    def run_command(self):
        text = self._require_complete()
        if text is None:
            return "break"
        if self._proc is not None:
            self.set_status("A command is already running.")
            return "break"
        cmd = self.current
        argv = shell_argv(cmd.category, text)
        if argv is None:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self._record_use()
            if cmd.category == "GAM":
                webbrowser.open(CLOUD_SHELL)
                self.set_status("↗ Cloud Shell opened — the command is on your clipboard.", 8000)
            else:
                messagebox.showinfo("PowerShell not found",
                                    "PowerShell isn't available on this system.\n\n"
                                    "The command was copied to your clipboard instead.")
            return "break"
        if not messagebox.askyesno("Run command?",
                                   f"Run this on {os.environ.get('COMPUTERNAME') or 'this computer'}?\n\n{text}",
                                   icon=messagebox.WARNING, default=messagebox.NO):
            return "break"
        self._record_use()
        self.output_section.pack(fill=tk.BOTH, expand=True)
        self._console_write(f"❯ {text}\n", "cmd")
        self._proc = True  # placeholder until the thread reports the Popen
        self._update_run_button()
        run_in_thread(argv, self._run_queue, self._set_proc)
        self.root.after(80, self._poll_run)
        self.set_status("▶ Running…", 60_000)
        return "break"

    def _set_proc(self, proc):
        self._proc = proc

    def stop_command(self):
        proc = self._proc
        if proc not in (None, True):
            try:
                proc.kill()
            except Exception:
                pass
            self._console_write("■ Stopped.\n", "err")

    def _poll_run(self):
        try:
            while True:
                kind, payload = self._run_queue.get_nowait()
                if kind == "out":
                    self._console_write(payload)
                else:
                    if kind == "error":
                        self._console_write(f"✖ {payload}\n", "err")
                        self.set_status(f"✖ {payload}")
                    elif payload == 0:
                        self._console_write("✔ Done.\n\n", "ok")
                        self.set_status("✔ Finished.")
                    else:
                        self._console_write(f"✖ Exit code {payload}\n\n", "err")
                        self.set_status(f"✖ Exit code {payload}.")
                    self._proc = None
                    self._update_run_button()
                    return
        except queue.Empty:
            pass
        self.root.after(80, self._poll_run)

    def _console_write(self, text, tag=None):
        self.console.config(state=tk.NORMAL)
        self.console.insert(tk.END, text, tag)
        self.console.see(tk.END)
        self.console.config(state=tk.DISABLED)

    def _clear_output(self):
        self.console.config(state=tk.NORMAL)
        self.console.delete("1.0", tk.END)
        self.console.config(state=tk.DISABLED)

    # =========================================================================
    # CRUD
    # =========================================================================
    def _safe(self, fn, *args):
        """Run a store mutation, reporting save failures instead of crashing."""
        try:
            return fn(*args)
        except StoreError as exc:
            messagebox.showerror("Not Saved", str(exc))
        except OSError as exc:
            messagebox.showerror("Save Error", f"Could not save commands:\n{exc}")
        return None

    def new_command(self):
        default = (self.filter if self.filter in CATEGORIES
                   else self.current.category if self.current else "GAM")

        def save(category, command, description):
            cmd = self.store.add(category, command, description)
            self.filter = self.filter if self.filter in ("All", cmd.category) else cmd.category
            self.search_var.set("")
            self.refresh_list()
            self._select(cmd)
            self.set_status(f"✔ Added to {cmd.category}.")

        CommandDialog(self, "New Command", default, on_save=save)
        return "break"

    def edit_command(self):
        cmd = self.current
        if not cmd:
            self.set_status("Select a command to edit.")
            return "break"

        def save(category, command, description):
            self.store.update(cmd, category, command, description)
            self.current = None
            self.refresh_list()
            if not self._select(cmd):
                self.set_filter("All")
                self._select(cmd)
            self.set_status("✔ Saved.")

        CommandDialog(self, "Edit Command", cmd.category, cmd.command, cmd.description, on_save=save)
        return "break"

    def delete_command(self):
        cmd = self.current
        if not cmd:
            return "break"
        # Keep the list position so the next command is selected.
        kids = list(self.tree.get_children())
        iid = str(id(cmd))
        pos = kids.index(iid) if iid in kids else 0
        index = self._safe(self.store.remove, cmd)
        if index is None:
            return "break"
        self._last_deleted = (cmd, index)
        self.current = None
        self.refresh_list(keep_selection=False)
        kids = self.tree.get_children()
        if kids:
            self._select(self._iid_to_cmd[kids[min(pos, len(kids) - 1)]])
        self.set_status(f"Deleted “{cmd.description}”.  Press Ctrl+Z to undo.", 10_000)
        return "break"

    def undo_delete(self):
        if not self._last_deleted:
            self.set_status("Nothing to undo.")
            return
        cmd, index = self._last_deleted
        self._last_deleted = None
        self._safe(self.store.restore, cmd, index)
        self.refresh_list()
        self._select(cmd)
        self.set_status(f"Restored “{cmd.description}”.")

    def toggle_favorite(self):
        cmd = self.current
        if not cmd:
            return
        fav = self._safe(self.store.toggle_favorite, cmd)
        if fav is None:
            return
        self.fav_btn.config(text="★" if fav else "☆")
        self.refresh_list()
        self.set_status(f"★ Added “{cmd.description}” to favorites." if fav
                        else f"Removed “{cmd.description}” from favorites.")

    def clear_history(self):
        if messagebox.askyesno("Clear Usage History", "Reset use counts and the Recent list?"):
            self._safe(self.store.clear_history)
            self.refresh_list()
            self._show_detail(self.current)

    def clear_recent_values(self):
        self.settings.clear_recent_values()
        self._show_detail(self.current)
        self.set_status("Forgot remembered field values.")

    # =========================================================================
    # IMPORT / EXPORT / PERSISTENCE
    # =========================================================================
    def load_all_commands(self):
        try:
            self.store.load()
            self.set_status(self.store.load_message)
        except StoreError as exc:
            messagebox.showwarning("Could Not Load Commands", str(exc))
            self.set_status("✖ " + str(exc), 15_000)
        self.path_label.config(text=self.store.path)
        self.current = None
        self.refresh_list()
        return "break"

    def import_commands(self):
        path = filedialog.askopenfilename(title="Import Commands",
                                          filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            added, skipped = self.store.import_file(path)
        except (OSError, ValueError, StoreError) as exc:
            messagebox.showerror("Import Failed", str(exc))
            return
        self.refresh_list()
        messagebox.showinfo("Import Complete",
                            f"Added {added} command(s).\nSkipped {skipped} already in your bank.")

    def export_commands(self):
        path = filedialog.asksaveasfilename(title="Export Commands", defaultextension=".json",
                                            initialfile="commands-export.json",
                                            filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            n = self.store.export_file(path)
        except OSError as exc:
            messagebox.showerror("Export Failed", str(exc))
            return
        self.set_status(f"Exported {n} commands to {os.path.basename(path)}.")

    def merge_library(self):
        try:
            added, _ = self.store.merge_library()
        except StoreError as exc:
            messagebox.showerror("Not Saved", str(exc))
            return
        self.refresh_list()
        self.set_status(f"Added {added} built-in command(s)." if added
                        else "You already have every built-in command.")

    # =========================================================================
    # MISC
    # =========================================================================
    def set_status(self, text, duration_ms=5000):
        self.status_bar.config(text=text)
        if self._status_job:
            self.root.after_cancel(self._status_job)
        self._status_job = self.root.after(duration_ms, lambda: self.status_bar.config(text="Ready"))

    def _toggle_theme(self):
        self._is_dark = not self._is_dark
        self.settings.set("theme", "dark" if self._is_dark else "light")
        self.C = dict(self.DARK if self._is_dark else self.LIGHT)
        self._rebuild_ui()
        return "break"

    def _rebuild_ui(self):
        current = self.current
        self._capture_values()
        self.settings.set("sash", self.paned.sash_coord(0)[0], save=False)
        if self._status_job:
            self.root.after_cancel(self._status_job)
            self._status_job = None
        self.search_var.trace_remove("write", self._search_trace)
        self.param_vars, self.param_widgets = {}, []
        for w in self.root.winfo_children():
            w.destroy()
        self.current = None
        self._build_all()
        self.path_label.config(text=self.store.path)
        self.refresh_list()
        if current:
            self._select(current)
        self.set_status(f"{'☽ Dark' if self._is_dark else '☀ Light'} mode.")

    def _on_close(self):
        try:
            self.settings.data["geometry"] = self.root.winfo_geometry()
            self.settings.data["sash"] = self.paned.sash_coord(0)[0]
            self.settings.save()
        except Exception:
            pass
        self.stop_command()
        self.root.destroy()

    def _dialog(self, title, width=420):
        C = self.C
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=C["surface"])
        win.resizable(False, False)
        win.transient(self.root)
        tk.Frame(win, bg=C["primary"], height=3).pack(fill=tk.X)
        win.bind("<Escape>", lambda e: win.destroy())
        return win

    def _show_shortcuts(self):
        C, F = self.C, self.F
        win = self._dialog("Keyboard Shortcuts")
        rows = [
            ("Ctrl+F", "Search"), ("↓ / Enter", "Move from search into the list"),
            ("Enter", "Fill in the selected command's fields"),
            ("Ctrl+Enter", "Copy the finished command"), ("Ctrl+R", "Run / open Cloud Shell"),
            ("Ctrl+N", "New command"), ("Ctrl+E", "Edit command"), ("Ctrl+D", "Toggle favorite"),
            ("Del", "Delete (in the list)"), ("Ctrl+Z", "Undo delete"),
            ("Ctrl+1 … 6", "All, Favorites, Recent, GAM, AD, PowerShell"),
            ("Ctrl+T", "Light / dark"), ("F5", "Reload from disk"), ("Esc", "Clear search"),
        ]
        grid = tk.Frame(win, bg=C["surface"])
        grid.pack(padx=22, pady=16)
        for i, (k, v) in enumerate(rows):
            tk.Label(grid, text=k, font=F["mono"], fg=C["accent"], bg=C["surface"],
                     anchor=tk.W).grid(row=i, column=0, sticky="w", padx=(0, 18), pady=1)
            tk.Label(grid, text=v, font=F["small"], fg=C["text"], bg=C["surface"],
                     anchor=tk.W).grid(row=i, column=1, sticky="w", pady=1)
        ttk.Button(win, text="Close", command=win.destroy, style="Gh.TButton").pack(pady=(0, 16))

    def _show_about(self):
        C, F = self.C, self.F
        win = self._dialog("About")
        tk.Label(win, text=cs.APP_NAME, font=F["title"], fg=C["text"], bg=C["surface"]).pack(pady=(18, 2), padx=40)
        tk.Label(win, text=f"v{cs.APP_VERSION}", font=F["small"], fg=C["muted"], bg=C["surface"]).pack()
        tk.Label(win, text="Author:   Jeff Burns\nContact:  JeffBurns@JFLX.CLOUD", font=F["small"],
                 fg=C["accent"], bg=C["surface"], justify=tk.LEFT).pack(pady=(10, 0))
        tk.Label(win, text=f"Data: {self.store.path}", font=F["tiny"], fg=C["dim"],
                 bg=C["surface"], wraplength=360).pack(pady=(10, 0), padx=16)
        ttk.Button(win, text="Close", command=win.destroy, style="Gh.TButton").pack(pady=16)


# ─────────────────────────────────────────────────────────────────────────────
def main():
    if IS_WINDOWS:
        try:  # crisp text on high-DPI displays
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    CommandManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
