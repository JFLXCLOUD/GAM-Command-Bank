// GAM Command Bank - Web Application JavaScript

class CommandBankApp {
    constructor() {
        this.commands = {
            gam: [],
            ad: [],
            powershell: []
        };
        
        this.currentTheme = localStorage.getItem('theme') || 'light';
        this.starfield = null;
        
        this.init();
    }

    init() {
        this.loadCommands();
        this.setupEventListeners();
        this.initializeStarfield();
        this.applyTheme();
        this.populateCommandSelects();
        this.showToast('Welcome to GAM Command Bank Enhanced Web Edition!', 'success');
    }

    // Theme Management
    applyTheme() {
        document.documentElement.setAttribute('data-theme', this.currentTheme);
        const themeIcon = document.querySelector('#themeToggle i');
        themeIcon.className = this.currentTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        localStorage.setItem('theme', this.currentTheme);
    }

    toggleTheme() {
        this.currentTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme();
        this.showToast(`Switched to ${this.currentTheme} mode`, 'success');
    }

    // Starfield Integration
    initializeStarfield() {
        try {
            this.starfield = new CalmingStarfield({
                container: '#starfield-background',
                starCount: 150,
                driftSensitivity: 0.3,
                colors: ['#3498DB', '#9B59B6', '#FFFFFF', '#F8C9D4', '#87CEEB'],
                reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches
            });
        } catch (error) {
            console.warn('Starfield component not available:', error);
        }
    }

    // Event Listeners
    setupEventListeners() {
        // Theme toggle
        document.getElementById('themeToggle').addEventListener('click', () => this.toggleTheme());

        // Tab navigation
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.closest('.tab-btn').dataset.tab));
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));

        // Auto-save on input changes
        document.querySelectorAll('input, select, textarea').forEach(element => {
            element.addEventListener('change', () => this.saveCommands());
        });
    }

    handleKeyboardShortcuts(e) {
        if (e.ctrlKey || e.metaKey) {
            switch (e.key) {
                case '1':
                    e.preventDefault();
                    this.switchTab('gam');
                    break;
                case '2':
                    e.preventDefault();
                    this.switchTab('ad');
                    break;
                case '3':
                    e.preventDefault();
                    this.switchTab('powershell');
                    break;
                case 'd':
                    e.preventDefault();
                    this.toggleTheme();
                    break;
            }
        }
    }

    // Tab Management
    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');

        this.updateStatus(`Switched to ${tabName.toUpperCase()} commands`);
    }

    // Command Management
    loadCommands() {
        const savedCommands = localStorage.getItem('gamCommandBankCommands');
        if (savedCommands) {
            try {
                this.commands = JSON.parse(savedCommands);
            } catch (error) {
                console.error('Error loading saved commands:', error);
                this.loadDefaultCommands();
            }
        } else {
            this.loadDefaultCommands();
        }
    }

    loadDefaultCommands() {
        // Load default commands from the original commands.json structure
        this.commands = {
            gam: [
                { command: "gam group <group> members", description: "List members of a group" },
                { command: "gam user <user> suspended on", description: "Suspend a user" },
                { command: "gam user <user> unsuspended", description: "Unsuspend a user" },
                { command: "gam user <user> change password newpassword <newpassword>", description: "Change a user's password" },
                { command: "gam create group <group>", description: "Create a new group" },
                { command: "gam delete group <group>", description: "Delete a group" },
                { command: "gam user <user> add group <group>", description: "Add a user to a group" },
                { command: "gam user <user> remove group <group>", description: "Remove a user from a group" },
                { command: "gam info domain", description: "Show domain information" },
                { command: "gam info user <Email Address>", description: "Show User Info" }
            ],
            ad: [
                { command: "Get-ADUser -Identity <user>", description: "Get a specific user" },
                { command: "Get-ADGroup -Identity <group>", description: "Get a specific group" },
                { command: "Disable-ADAccount -Identity <user>", description: "Disable a user account" },
                { command: "Enable-ADAccount -Identity <user>", description: "Enable a user account" },
                { command: "Set-ADUser -Identity <user> -Password <securepassword>", description: "Set a user's password (use SecureString)" },
                { command: "New-ADGroup -Name <group> -GroupCategory Security -GroupScope Global", description: "Create a new security group" },
                { command: "Remove-ADGroup -Identity <group>", description: "Delete a group" },
                { command: "Add-ADGroupMember -Identity <group> -Members <user>", description: "Add a user to a group" },
                { command: "Remove-ADGroupMember -Identity <group> -Members <user>", description: "Remove a user from a group" },
                { command: "Get-ADDomain", description: "Get domain information" }
            ],
            powershell: [
                { command: "Get-Process", description: "List all running processes" },
                { command: "Stop-Process -Id <process_id>", description: "Stop a process by its ID" },
                { command: "Get-Service", description: "List all services" },
                { command: "Start-Service -Name <service_name>", description: "Start a service" },
                { command: "Stop-Service -Name <service_name>", description: "Stop a service" },
                { command: "Get-Item <path>", description: "Get a file or folder" },
                { command: "Set-Content -Path <path> -Value <content>", description: "Set the content of a file" },
                { command: "New-Item -Path <path> -ItemType File", description: "Create a new file" },
                { command: "New-Item -Path <path> -ItemType Directory", description: "Create a new folder" },
                { command: "Remove-Item -Path <path>", description: "Delete a file or folder" },
                { command: "Get-ChildItem -Path <path>", description: "Get the files and folders in a path" },
                { command: "Get-EventLog -LogName System -EntryType Error", description: "Get system error events" },
                { command: "Restart-Computer", description: "Restart the computer" },
                { command: "Get-Credential", description: "Get a user's credentials" },
                { command: "$PSVersionTable.PSVersion", description: "Show the current PowerShell version" }
            ]
        };
        this.saveCommands();
    }

    saveCommands() {
        try {
            localStorage.setItem('gamCommandBankCommands', JSON.stringify(this.commands));
        } catch (error) {
            console.error('Error saving commands:', error);
            this.showToast('Error saving commands to local storage', 'error');
        }
    }

    populateCommandSelects() {
        ['gam', 'ad', 'powershell'].forEach(category => {
            const select = document.getElementById(`${category}-select`);
            select.innerHTML = '<option value="">Choose a command...</option>';
            
            this.commands[category].forEach((cmd, index) => {
                const option = document.createElement('option');
                option.value = index;
                option.textContent = cmd.description;
                select.appendChild(option);
            });
        });
    }

    // Command Operations
    addCommand(category) {
        const commandInput = document.getElementById(`${category}-command`);
        const descriptionInput = document.getElementById(`${category}-description`);
        
        const command = commandInput.value.trim();
        const description = descriptionInput.value.trim();
        
        if (!command) {
            this.showToast('Command cannot be empty', 'error');
            commandInput.focus();
            return;
        }
        
        if (!description) {
            this.showToast('Description cannot be empty', 'error');
            descriptionInput.focus();
            return;
        }
        
        // Check for duplicates
        const isDuplicate = this.commands[category].some(cmd => 
            cmd.command === command && cmd.description === description
        );
        
        if (isDuplicate) {
            this.showToast('This command already exists', 'warning');
            return;
        }
        
        // Add the command
        this.commands[category].push({ command, description });
        this.saveCommands();
        this.populateCommandSelects();
        
        // Clear inputs
        commandInput.value = '';
        descriptionInput.value = '';
        
        this.showToast(`Command added to ${category.toUpperCase()} category`, 'success');
        this.updateStatus(`Added new ${category.toUpperCase()} command`);
    }

    removeCommand(category) {
        const select = document.getElementById(`${category}-select`);
        const selectedIndex = select.value;
        
        if (!selectedIndex) {
            this.showToast('Please select a command to remove', 'warning');
            return;
        }
        
        const commandToRemove = this.commands[category][selectedIndex];
        
        if (confirm(`Are you sure you want to remove "${commandToRemove.description}"?`)) {
            this.commands[category].splice(selectedIndex, 1);
            this.saveCommands();
            this.populateCommandSelects();
            
            // Clear the output and parameters
            document.getElementById(`${category}-output`).value = '';
            document.getElementById(`${category}-params`).innerHTML = '';
            
            this.showToast(`Command removed from ${category.toUpperCase()} category`, 'success');
            this.updateStatus(`Removed ${category.toUpperCase()} command`);
        }
    }

    updateCommandDisplay(category) {
        const select = document.getElementById(`${category}-select`);
        const selectedIndex = select.value;
        const paramsContainer = document.getElementById(`${category}-params`);
        
        // Clear previous parameters
        paramsContainer.innerHTML = '';
        
        if (!selectedIndex) {
            document.getElementById(`${category}-output`).value = '';
            return;
        }
        
        const command = this.commands[category][selectedIndex];
        const placeholders = this.extractPlaceholders(command.command);
        
        if (placeholders.length > 0) {
            placeholders.forEach(placeholder => {
                const paramGroup = document.createElement('div');
                paramGroup.className = 'param-group';
                
                const label = document.createElement('label');
                label.textContent = `${placeholder}:`;
                
                const input = document.createElement('input');
                input.type = 'text';
                input.className = 'param-input';
                input.placeholder = `Enter ${placeholder}`;
                input.dataset.placeholder = placeholder;
                input.addEventListener('input', () => this.buildCommand(category));
                
                paramGroup.appendChild(label);
                paramGroup.appendChild(input);
                paramsContainer.appendChild(paramGroup);
            });
        }
        
        this.buildCommand(category);
    }

    extractPlaceholders(command) {
        const matches = command.match(/<([^>]+)>/g);
        return matches ? matches.map(match => match.slice(1, -1)) : [];
    }

    buildCommand(category) {
        const select = document.getElementById(`${category}-select`);
        const selectedIndex = select.value;
        const output = document.getElementById(`${category}-output`);
        
        if (!selectedIndex) {
            output.value = '';
            return;
        }
        
        let command = this.commands[category][selectedIndex].command;
        const paramInputs = document.querySelectorAll(`#${category}-params .param-input`);
        
        paramInputs.forEach(input => {
            const placeholder = input.dataset.placeholder;
            const value = input.value.trim();
            command = command.replace(`<${placeholder}>`, value || `<${placeholder}>`);
        });
        
        output.value = command;
        this.updateStatus('Command built successfully');
    }

    copyCommand(category) {
        const output = document.getElementById(`${category}-output`);
        const command = output.value.trim();
        
        if (!command) {
            this.showToast('No command to copy', 'warning');
            return;
        }
        
        navigator.clipboard.writeText(command).then(() => {
            this.showToast('Command copied to clipboard!', 'success');
            this.updateStatus('Command copied to clipboard');
        }).catch(err => {
            console.error('Failed to copy command:', err);
            this.showToast('Failed to copy command', 'error');
        });
    }

    executeCommand(category) {
        const output = document.getElementById(`${category}-output`);
        const command = output.value.trim();
        
        if (!command) {
            this.showToast('No command to execute', 'warning');
            return;
        }
        
        // Copy command to clipboard first
        this.copyCommand(category);
        
        if (category === 'gam') {
            // Open Google Cloud Shell for GAM commands
            window.open('https://shell.cloud.google.com/', '_blank');
            this.showToast('Opening Google Cloud Shell... Command copied to clipboard!', 'success');
            this.updateStatus('Opened Google Cloud Shell');
        } else {
            // For AD and PowerShell commands, just copy and inform user
            this.showToast(`${category.toUpperCase()} command copied to clipboard! Execute in your terminal.`, 'success');
            this.updateStatus(`${category.toUpperCase()} command ready for execution`);
        }
    }

    // UI Helpers
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        // Auto-remove after 4 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => {
                if (container.contains(toast)) {
                    container.removeChild(toast);
                }
            }, 300);
        }, 4000);
    }

    updateStatus(message) {
        document.getElementById('status-text').textContent = message;
    }

    // Export/Import functionality
    exportCommands() {
        const dataStr = JSON.stringify(this.commands, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = 'gam-command-bank-export.json';
        link.click();
        
        URL.revokeObjectURL(url);
        this.showToast('Commands exported successfully!', 'success');
    }

    importCommands(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const importedCommands = JSON.parse(e.target.result);
                this.commands = importedCommands;
                this.saveCommands();
                this.populateCommandSelects();
                this.showToast('Commands imported successfully!', 'success');
            } catch (error) {
                console.error('Import error:', error);
                this.showToast('Error importing commands. Please check the file format.', 'error');
            }
        };
        reader.readAsText(file);
    }
}

// Global functions for HTML onclick handlers
function addCommand(category) {
    app.addCommand(category);
}

function removeCommand(category) {
    app.removeCommand(category);
}

function updateCommandDisplay(category) {
    app.updateCommandDisplay(category);
}

function buildCommand(category) {
    app.buildCommand(category);
}

function copyCommand(category) {
    app.copyCommand(category);
}

function executeCommand(category) {
    app.executeCommand(category);
}

// Add slideOut animation to CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new CommandBankApp();
});