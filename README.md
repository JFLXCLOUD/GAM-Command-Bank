# GAM Command Bank

A command management tool for GAM (Google Admin Management), Active Directory, and PowerShell commands. Available as both a Python desktop app and a web-based interface.

## Features

- Store and organize commands by category (GAM, Active Directory, PowerShell)
- Use `<placeholder>` syntax for dynamic parameter substitution
- Favorites and command history tracking
- Search across all commands
- Dark and light theme support

## Getting Started

### Web Version
Open `web-version/index.html` in any modern browser. Commands are saved to LocalStorage.

### Desktop Version
Requires Python 3.x with tkinter (included by default on most systems).

```
python command_bank.py
```

Commands are stored in `commands.json` in the same directory.

## Command Syntax

Use angle brackets for parameters that change per use:

```
gam user <user> suspended on
Get-ADUser -Identity <user>
Get-Process -Name <process_name>
```

The app will prompt for each parameter before copying or executing.

## Project Structure

```
GAM-Command-Bank/
├── command_bank.py       # Python desktop app
├── commands.json         # Command database
├── icon.ico              # App icon
└── web-version/
    ├── index.html
    ├── styles.css
    ├── app.js
    └── starfield.js
```

## Notes

- All data is stored locally. Nothing is transmitted externally.
- The desktop version saves to a local JSON file; the web version uses browser LocalStorage.
- Keep `commands.json` alongside the executable when distributing.

## Author

Jeff Burns - Jeff.Burns@JFLX.CLOUD
