# GAM Command Bank

A command library for GAM (Google Workspace admin), Active Directory, and PowerShell. Pick a command, fill in its fields, and copy or run it. It comes as a Windows desktop app and as a web page, and both use the same `commands.json` format.

## Features

- More than 480 built-in commands, searchable across every category at once
- Fill-in fields: `<user>` becomes an input box. `<reader|writer|owner>` becomes a drop-down.
- The app remembers values you used recently for each field name. A value you enter for `<email>` carries over when you switch to another command.
- Favorites and a Recent list. Use counts go up when you copy or run a command, not when you only select it.
- Add, edit, and delete commands. Undo a delete with Ctrl+Z or the Undo button.
- Import and export JSON, and add built-in commands that are missing from your bank
- Desktop only: run AD/PowerShell commands, and GAM if it is installed, with the output shown live. GAM commands otherwise open in Google Cloud Shell.
- Light and dark themes, keyboard driven, mobile-friendly web layout

## Getting Started

### Windows Executable (Recommended)
Download `GAM_Command_Bank.exe` from the [Releases](https://github.com/JFLXCLOUD/GAM-Command-Bank/releases) page and run it. The built-in commands are bundled into the exe.

Windows may show a SmartScreen warning because the executable is unsigned. Click "More info", then "Run anyway".

### Desktop Version (Python)
Requires Python 3.9+ with tkinter.

```
python command_bank.py
```

### Web Version
Open `web-version/index.html` in a modern browser. Your commands are saved in that browser.

- When the page is served over http(s), for example from GitHub Pages or with `python -m http.server` in the repo root, it loads the full `commands.json` on first run.
- When you open it straight from disk (`file://`), browsers block that load, so the page starts with a small starter set. Use **⋯ › Import commands…** and choose `commands.json` to load everything.

## Using It

1. Search (Ctrl+F on desktop, `/` on the web) or choose a filter: All, Favorites, Recent, GAM, AD, or PowerShell.
2. Press Enter to jump into the command's fields and type the values. The preview shows filled values in blue and missing ones in amber.
3. Press Enter on the last field, or Ctrl+Enter, to copy. **Run** (desktop) asks for confirmation before it executes anything.

| Action | Desktop | Web |
| --- | --- | --- |
| Search | Ctrl+F | `/` or Ctrl+K |
| Copy | Ctrl+Enter | Ctrl+Enter |
| Run / Cloud Shell | Ctrl+R | button |
| New / Edit | Ctrl+N / Ctrl+E | N / E |
| Favorite | Ctrl+D | F |
| Delete / Undo | Del / Ctrl+Z | Del / Ctrl+Z |
| Filters | Ctrl+1 … 6 | 1 … 6 |
| All shortcuts | F1 | ? |

## Command Syntax

```
gam user <email> suspended on                          # free-text field
gam user <new_owner> add drivefileacl <file_id> user <new_owner>   # repeated field, filled once
gam user <email> add drivefileacl <file_id> user <share_with> role <reader|writer|owner>   # pick-list
```

By convention, descriptions use `Section › Action`, for example `Users › Suspend user`, so related commands group together in search.

## Where Data Is Stored

| Version | Location |
| --- | --- |
| Windows exe | `commands.json` and `settings.json` next to the exe (portable). If that folder is read-only, `%APPDATA%\GAM Command Bank`. |
| Python source | `%APPDATA%\GAM Command Bank` (Windows), `~/Library/Application Support/GAM Command Bank` (macOS), `~/.config/gam-command-bank` (Linux) |
| Web | Browser localStorage. Use Export to back it up or move it. |

Set `GAM_COMMAND_BANK_HOME` to use a different folder. **File › Open Data Folder** opens the current one, and the status bar shows the path.

Your data is safe from failed or partial saves:
- Saves are atomic (write to a temp file, then rename). The previous version is kept as `commands.json.bak`.
- If `commands.json` can't be read, for example after a bad hand edit, the app keeps a copy (`commands.corrupt-<time>.json`). It will not overwrite the file until you fix it and reload.
- The repository's `commands.json` is the clean built-in library. Your favorites and usage never end up in it.

A file exported from the web version imports into the desktop app, and the other way round. Files from older versions of either app also import.

## Project Structure

```
GAM-Command-Bank/
├── command_bank.py        # Desktop UI (tkinter)
├── command_store.py       # Storage, search and placeholder logic (no UI)
├── commands.json          # Built-in command library
├── GAM_Command_Bank.spec  # PyInstaller build
├── icon.ico
├── tests/                 # python -m unittest discover -s tests
│                          # node --test tests/web_core.test.js
└── web-version/
    ├── index.html
    ├── styles.css
    ├── core.js            # Shared command logic (mirrors command_store.py)
    ├── app.js             # Web UI
    └── starfield.js
```

## Building the Exe

```
pip install pyinstaller
pyinstaller GAM_Command_Bank.spec
```

## Publishing a Release

Pushing a version tag runs `.github/workflows/release.yml` on a Windows runner. The workflow runs the tests, builds the exe, zips the web version, and publishes a GitHub release. The release notes come from `.github/releases/<tag>.md`.

```
git tag v4.0.0
git push origin v4.0.0
```

You can also go to **Actions › Release › Run workflow** on GitHub and enter a tag name. That releases the latest commit on the branch you pick, and creates the tag if it doesn't exist.

## Author

Jeff Burns - Jeff.Burns@JFLX.CLOUD
