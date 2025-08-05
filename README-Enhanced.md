# GAM Command Bank - Enhanced Edition

A modern, professional command management application for GAM (Google Admin Management), Active Directory, and PowerShell commands. This enhanced version features both a modernized Python GUI and a beautiful web-based interface with advanced features.

![GAM Command Bank](https://img.shields.io/badge/Version-2.0-blue) ![License](https://img.shields.io/badge/License-MIT-green) ![Platform](https://img.shields.io/badge/Platform-Web%20%7C%20Desktop-lightgrey)

## ✨ What's New in Enhanced Edition

### 🎨 Modern Web Interface
- **Beautiful Design**: Professional, modern UI with card-based layout
- **Dark Mode**: Toggle between light and dark themes
- **Interactive Starfield**: Calming animated background with mouse interaction
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile
- **Toast Notifications**: Real-time feedback for all actions
- **Keyboard Shortcuts**: Quick navigation with Ctrl+1/2/3 and Ctrl+D for dark mode

### 🚀 Enhanced Features
- **Smart Parameter Detection**: Automatically detects command placeholders
- **Real-time Command Building**: Live preview of commands as you type
- **Local Storage**: Commands persist between sessions
- **Copy to Clipboard**: One-click command copying
- **Export/Import**: Backup and restore your command library
- **Accessibility**: Full keyboard navigation and screen reader support

### 💻 Modernized Python GUI
- **Updated Styling**: Modern color scheme and typography
- **Better Layout**: Improved spacing and visual hierarchy
- **Enhanced UX**: Better error handling and user feedback
- **Resizable Interface**: Flexible window sizing

## 🌟 Features

### Command Management
- **Add Commands**: Store commands with descriptions for easy identification
- **Parameter Substitution**: Use `<placeholder>` syntax for dynamic values
- **Command Categories**: Organize by GAM, Active Directory, and PowerShell
- **Duplicate Prevention**: Automatic detection of duplicate commands
- **Quick Removal**: Easy command deletion with confirmation

### Execution Support
- **GAM Commands**: Opens Google Cloud Shell automatically
- **PowerShell/AD Commands**: Copies to clipboard for local execution
- **Parameter Input**: Dynamic form generation for command parameters
- **Command Preview**: See the final command before execution

### Data Persistence
- **Auto-save**: Commands automatically saved to local storage (web) or JSON file (desktop)
- **Import/Export**: Backup and share command libraries
- **Cross-platform**: Same data format across web and desktop versions

## 🚀 Quick Start

### Web Version (Recommended)
1. Open `web-version/index.html` in your web browser
2. Start adding and managing commands immediately
3. Toggle dark mode with the moon/sun icon
4. Use keyboard shortcuts for quick navigation

### Desktop Version
1. Run `python command_bank.py` (requires Python 3.x with tkinter)
2. Commands are stored in `commands.json` in the same directory
3. Keep the JSON file with the executable for persistence

## 📱 Web Interface Guide

### Navigation
- **Tabs**: Click GAM Commands, AD Commands, or PowerShell tabs
- **Keyboard**: Use Ctrl+1, Ctrl+2, Ctrl+3 to switch tabs
- **Dark Mode**: Click the theme toggle or press Ctrl+D

### Adding Commands
1. Enter your command using `<placeholder>` for variables
2. Add a descriptive name
3. Click "Add Command"
4. Commands are automatically saved

### Using Commands
1. Select a command from the dropdown
2. Fill in any required parameters
3. Click "Build Command" to preview
4. Click "Copy to Clipboard" or "Execute"

### Example Commands

#### GAM Commands
```bash
gam user <user> suspended on
gam group <group> members
gam user <user> change password newpassword <newpassword>
```

#### Active Directory Commands
```powershell
Get-ADUser -Identity <user>
Disable-ADAccount -Identity <user>
Add-ADGroupMember -Identity <group> -Members <user>
```

#### PowerShell Commands
```powershell
Get-Process -Name <process_name>
Stop-Service -Name <service_name>
Get-EventLog -LogName System -EntryType Error
```

## 🎨 Customization

### Starfield Background
The interactive starfield can be customized by modifying the configuration in `app.js`:

```javascript
this.starfield = new CalmingStarfield({
    container: '#starfield-background',
    starCount: 150,                    // Number of stars
    driftSensitivity: 0.3,            // Mouse interaction sensitivity
    colors: ['#3498DB', '#9B59B6', '#FFFFFF', '#F8C9D4', '#87CEEB'],
    reducedMotion: false              // Accessibility setting
});
```

### Theme Colors
Modify CSS custom properties in `styles.css`:

```css
:root {
    --primary-color: #2C3E50;
    --secondary-color: #3498DB;
    --accent-color: #E74C3C;
    --success-color: #27AE60;
    /* ... more colors */
}
```

## 🔧 Technical Details

### Web Version Stack
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Styling**: CSS Custom Properties, Flexbox, Grid
- **Storage**: LocalStorage API
- **Animation**: Canvas API for starfield
- **Icons**: Font Awesome 6

### Desktop Version Stack
- **Language**: Python 3.x
- **GUI Framework**: tkinter with ttk styling
- **Data Storage**: JSON file format
- **Cross-platform**: Windows, macOS, Linux

### Browser Compatibility
- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## 📁 Project Structure

```
GAM-Command-Bank/
├── web-version/                 # Modern web interface
│   ├── index.html              # Main HTML file
│   ├── styles.css              # Modern CSS with dark mode
│   ├── app.js                  # Application logic
│   └── starfield.js            # Interactive background
├── command_bank.py             # Enhanced Python GUI
├── commands.json               # Default command database
├── icon.ico                    # Application icon
├── README.md                   # Original documentation
└── README-Enhanced.md          # This enhanced documentation
```

## 🎯 Use Cases

### System Administrators
- Manage common GAM commands for Google Workspace
- Store frequently used PowerShell scripts
- Quick access to Active Directory management commands

### IT Support Teams
- Standardize command usage across team members
- Reduce errors with parameter validation
- Share command libraries between team members

### DevOps Engineers
- Automate routine administrative tasks
- Document command usage with descriptions
- Integrate with existing workflows

## 🔒 Security Notes

- Commands are stored locally (no cloud transmission)
- Web version uses browser's LocalStorage
- Desktop version uses local JSON files
- No sensitive data is logged or transmitted

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Bug Reports**: Open an issue with detailed reproduction steps
2. **Feature Requests**: Suggest new features or improvements
3. **Code Contributions**: Fork, create a feature branch, and submit a PR
4. **Documentation**: Help improve documentation and examples

### Development Setup
```bash
# Clone the repository
git clone <repository-url>
cd GAM-Command-Bank

# For web development
# Simply open web-version/index.html in your browser

# For Python development
python -m pip install tkinter  # Usually included with Python
python command_bank.py
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Original GAM Command Bank concept
- Font Awesome for beautiful icons
- Google Fonts for typography
- The Python and web development communities

## 📞 Support

- **Author**: Jeff Burns
- **Contact**: Jeff.Burns@JFLX.CLOUD
- **Issues**: Use GitHub Issues for bug reports and feature requests

---

**Made with ❤️ for system administrators and IT professionals**

*Transform your command-line workflow with GAM Command Bank Enhanced Edition*