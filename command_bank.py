import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import re
import subprocess
import webbrowser
import tempfile


class CommandManager:
    """
    GAM Command Bank - A modern application to store and categorize common commands.
    """

    def __init__(self, root):
        """
        Initializes the main application window.

        Args:
            root (tk.Tk): The root Tkinter window.
        """
        self.root = root
        self.root.title("GAM Command Bank - Professional Command Manager")
        self.root.geometry("900x750")
        self.root.resizable(True, True)
        self.root.minsize(800, 600)
        
        # Set application icon if available
        try:
            if os.path.exists("icon.ico"):
                self.root.iconbitmap("icon.ico")
        except:
            pass
            
        # Modern color scheme
        self.colors = {
            'primary': '#2C3E50',      # Dark blue-gray
            'secondary': '#3498DB',     # Bright blue
            'accent': '#E74C3C',        # Red
            'success': '#27AE60',       # Green
            'warning': '#F39C12',       # Orange
            'background': '#ECF0F1',    # Light gray
            'surface': '#FFFFFF',       # White
            'text': '#2C3E50',          # Dark text
            'text_light': '#7F8C8D',    # Light text
            'border': '#BDC3C7'         # Border gray
        }
        
        self.data_file = self._get_data_file_path("commands.json")
        self.commands = {}
        self.style = ttk.Style()
        self.configure_modern_style()

        print(f"Data file path: {self.data_file}")

        self.create_menu()
        self.create_modern_widgets()
        self.load_all_commands()

    def create_menu(self):
        """Creates the application menu."""
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.root.quit)

        about_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="About", menu=about_menu)
        about_menu.add_command(label="Info", command=self.show_about)

        self.root.config(menu=menubar)

    def show_about(self):
        """Displays the 'About' information."""
        about_text = "Author: Jeff Burns\nContact: Jeff.Burns@JFLX.CLOUD"
        messagebox.showinfo("About", about_text)

    def _get_data_file_path(self, filename):
        """ Get the absolute path to the data file. """
        if getattr(sys, 'frozen', False):
            
            base_path = os.path.dirname(sys.executable)
        else:
           
            base_path = os.path.dirname(os.path.abspath(__file__)) 
        return os.path.join(base_path, filename)

    def configure_modern_style(self):
        """
        Configures modern visual styling for the application.
        """
        self.style.theme_use('clam')
        
        # Configure root background
        self.root.configure(bg=self.colors['background'])

        # Modern fonts
        title_font = ('Segoe UI', 12, 'bold')
        body_font = ('Segoe UI', 10)
        button_font = ('Segoe UI', 10, 'bold')
        
        # Configure notebook (tabs)
        self.style.configure("TNotebook",
                           background=self.colors['background'],
                           borderwidth=0)
        self.style.configure("TNotebook.Tab",
                           padding=[20, 12],
                           font=title_font,
                           background=self.colors['surface'],
                           foreground=self.colors['text'],
                           borderwidth=1,
                           relief='solid')
        self.style.map("TNotebook.Tab",
                      background=[('selected', self.colors['secondary']),
                                ('active', self.colors['border'])],
                      foreground=[('selected', 'white'),
                                ('active', self.colors['text'])])

        # Configure frames
        self.style.configure("TFrame",
                           background=self.colors['background'],
                           relief='flat')
        self.style.configure("Card.TFrame",
                           background=self.colors['surface'],
                           relief='solid',
                           borderwidth=1)

        # Configure labels
        self.style.configure("TLabel",
                           font=body_font,
                           foreground=self.colors['text'],
                           background=self.colors['background'])
        self.style.configure("Title.TLabel",
                           font=title_font,
                           foreground=self.colors['primary'],
                           background=self.colors['background'])
        self.style.configure("Link.TLabel",
                           font=('Segoe UI', 10, 'underline'),
                           foreground=self.colors['secondary'],
                           background=self.colors['background'],
                           cursor="hand2")

        # Configure entries
        self.style.configure("TEntry",
                           font=body_font,
                           foreground=self.colors['text'],
                           fieldbackground=self.colors['surface'],
                           borderwidth=2,
                           relief='solid',
                           insertcolor=self.colors['secondary'])
        self.style.map("TEntry",
                      focuscolor=[('focus', self.colors['secondary'])],
                      bordercolor=[('focus', self.colors['secondary'])])

        # Configure buttons with modern styling
        self.style.configure("Modern.TButton",
                           font=button_font,
                           foreground='white',
                           background=self.colors['secondary'],
                           relief='flat',
                           borderwidth=0,
                           padding=[15, 8])
        self.style.configure("Success.TButton",
                           font=button_font,
                           foreground='white',
                           background=self.colors['success'],
                           relief='flat',
                           borderwidth=0,
                           padding=[15, 8])
        self.style.configure("Danger.TButton",
                           font=button_font,
                           foreground='white',
                           background=self.colors['accent'],
                           relief='flat',
                           borderwidth=0,
                           padding=[12, 6])
        self.style.configure("Warning.TButton",
                           font=button_font,
                           foreground='white',
                           background=self.colors['warning'],
                           relief='flat',
                           borderwidth=0,
                           padding=[15, 8])

        # Button hover effects
        self.style.map("Modern.TButton",
                      background=[('active', '#2980B9'), ('pressed', '#21618C')])
        self.style.map("Success.TButton",
                      background=[('active', '#229954'), ('pressed', '#1E8449')])
        self.style.map("Danger.TButton",
                      background=[('active', '#CB4335'), ('pressed', '#B03A2E')])
        self.style.map("Warning.TButton",
                      background=[('active', '#D68910'), ('pressed', '#B7950B')])

        # Configure combobox
        self.style.configure("TCombobox",
                           font=body_font,
                           foreground=self.colors['text'],
                           fieldbackground=self.colors['surface'],
                           borderwidth=2,
                           relief='solid')
        self.style.map("TCombobox",
                      focuscolor=[('focus', self.colors['secondary'])],
                      bordercolor=[('focus', self.colors['secondary'])])

        # Configure status bar
        self.style.configure("Statusbar.TLabel",
                           font=('Segoe UI', 9),
                           foreground=self.colors['text_light'],
                           background=self.colors['primary'],
                           padding=[10, 5])

    def create_modern_widgets(self):
        """
        Creates modern GUI widgets with improved layout and styling.
        """
        # Create main container with padding
        main_container = ttk.Frame(self.root, style="TFrame")
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Create header
        header_frame = ttk.Frame(main_container, style="TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # App title and description
        title_label = ttk.Label(header_frame,
                               text="GAM Command Bank",
                               style="Title.TLabel",
                               font=('Segoe UI', 18, 'bold'))
        title_label.pack(anchor=tk.W)
        
        subtitle_label = ttk.Label(header_frame,
                                  text="Professional command management for GAM, Active Directory, and PowerShell",
                                  style="TLabel",
                                  font=('Segoe UI', 10))
        subtitle_label.pack(anchor=tk.W, pady=(5, 0))

        # Create notebook with modern styling
        self.notebook = ttk.Notebook(main_container, style="TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Create frames for each category
        self.gam_frame = ttk.Frame(self.notebook, style="TFrame")
        self.ad_frame = ttk.Frame(self.notebook, style="TFrame")
        self.powershell_frame = ttk.Frame(self.notebook, style="TFrame")

        # Add tabs with icons (using Unicode symbols)
        self.notebook.add(self.gam_frame, text="🌐 GAM Commands")
        self.notebook.add(self.ad_frame, text="🏢 AD Commands")
        self.notebook.add(self.powershell_frame, text="💻 PowerShell")

        # Create content for each tab
        self.create_modern_category_content(self.gam_frame, "GAM", "GAM Command", "Add GAM Command",
                                          link_text="📚 Complete List of GAM Commands",
                                          link_url="https://sites.google.com/view/gam--commands/home?authuser=0")
        self.create_modern_category_content(self.ad_frame, "AD", "AD Command", "Add AD Command")
        self.create_modern_category_content(self.powershell_frame, "PowerShell", "PowerShell Command",
                                          "Add PowerShell Command")

        # Create bottom toolbar
        toolbar_frame = ttk.Frame(main_container, style="Card.TFrame")
        toolbar_frame.pack(fill=tk.X, pady=(0, 10))
        
        toolbar_inner = ttk.Frame(toolbar_frame, style="TFrame")
        toolbar_inner.pack(fill=tk.X, padx=15, pady=10)
        
        self.load_commands_button = ttk.Button(toolbar_inner,
                                             text="🔄 Reload Commands",
                                             command=self.load_all_commands,
                                             style="Modern.TButton")
        self.load_commands_button.pack(side=tk.LEFT)
        
        # Add version info
        version_label = ttk.Label(toolbar_inner,
                                 text="v2.0 - Enhanced Edition",
                                 style="TLabel",
                                 font=('Segoe UI', 9))
        version_label.pack(side=tk.RIGHT)

        # Create modern status bar
        self.status_bar = ttk.Label(self.root,
                                   text="Ready - GAM Command Bank Enhanced Edition",
                                   anchor=tk.W,
                                   style="Statusbar.TLabel")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def open_web_link(self, url):
        """Opens the given URL in the default web browser."""
        webbrowser.open_new(url)

    def create_modern_category_content(self, frame, category_name, command_label_text, add_button_text, link_text=None, link_url=None):
        """
        Creates modern content for a category frame with improved layout and styling.

        Args:
            frame (ttk.Frame): The frame to add the content to.
            category_name (str): The name of the category.
            command_label_text (str): The text for the command label.
            add_button_text (str): The text for the add button.
            link_text (str, optional): Text for the clickable link. Defaults to None.
            link_url (str, optional): URL to open when the link is clicked. Defaults to None.
        """
        # Create main container with padding
        main_container = ttk.Frame(frame, style="TFrame")
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Create input section card
        input_card = ttk.Frame(main_container, style="Card.TFrame")
        input_card.pack(fill=tk.X, pady=(0, 15))
        
        input_container = ttk.Frame(input_card, style="TFrame")
        input_container.pack(fill=tk.X, padx=20, pady=15)
        
        # Input section title
        input_title = ttk.Label(input_container, text=f"Add New {category_name} Command", style="Title.TLabel")
        input_title.pack(anchor=tk.W, pady=(0, 15))

        # Command input with modern styling
        command_label = ttk.Label(input_container, text=command_label_text + ":", style="TLabel")
        command_label.pack(anchor=tk.W, pady=(0, 5))
        command_entry = ttk.Entry(input_container, width=70, style="TEntry", font=('Consolas', 10))
        command_entry.pack(fill=tk.X, pady=(0, 15))

        # Description input
        description_label = ttk.Label(input_container, text="Description:", style="TLabel")
        description_label.pack(anchor=tk.W, pady=(0, 5))
        description_entry = ttk.Entry(input_container, width=70, style="TEntry")
        description_entry.pack(fill=tk.X, pady=(0, 15))

        # Action buttons
        button_container = ttk.Frame(input_container, style="TFrame")
        button_container.pack(fill=tk.X)

        add_button = ttk.Button(button_container, text=f"➕ {add_button_text}",
                                command=lambda: self.add_command(category_name, command_entry.get(),
                                                                 description_entry.get()),
                                style="Success.TButton")
        add_button.pack(side=tk.LEFT, padx=(0, 10))

        remove_button = ttk.Button(button_container, text="🗑️ Remove Selected",
                                   command=lambda: self.remove_command(category_name, frame),
                                   style="Danger.TButton")
        remove_button.pack(side=tk.LEFT)

        # Add link for GAM commands
        if category_name == "GAM" and link_text and link_url:
            link_label = ttk.Label(button_container, text=link_text, style="Link.TLabel")
            link_label.pack(side=tk.RIGHT)
            link_label.bind("<Button-1>", lambda event, url=link_url: self.open_web_link(url))

        # Command execution section
        execution_card = ttk.Frame(main_container, style="Card.TFrame")
        execution_card.pack(fill=tk.BOTH, expand=True)
        
        execution_container = ttk.Frame(execution_card, style="TFrame")
        execution_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # Execution section title
        execution_title = ttk.Label(execution_container, text="Execute Commands", style="Title.TLabel")
        execution_title.pack(anchor=tk.W, pady=(0, 15))

        # Command selection
        select_label = ttk.Label(execution_container, text="Select Command:", style="TLabel")
        select_label.pack(anchor=tk.W, pady=(0, 5))
        description_combobox = ttk.Combobox(execution_container, width=70, state="readonly", style="TCombobox")
        description_combobox.pack(fill=tk.X, pady=(0, 15))
        description_combobox.bind("<<ComboboxSelected>>",
                                 lambda event: self.update_command_display(event, category_name, frame))

        # Dynamic input fields container
        input_frame = ttk.Frame(execution_container, style="TFrame")
        input_frame.pack(fill=tk.X, pady=(0, 15))

        # Command output area with modern styling
        output_label = ttk.Label(execution_container, text="Command Output:", style="TLabel")
        output_label.pack(anchor=tk.W, pady=(0, 5))
        
        text_frame = ttk.Frame(execution_container, style="TFrame")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        text_area = tk.Text(text_frame, height=12, state=tk.DISABLED,
                           font=('Consolas', 10),
                           bg=self.colors['surface'],
                           fg=self.colors['text'],
                           selectbackground=self.colors['secondary'],
                           relief='solid',
                           borderwidth=2,
                           wrap=tk.WORD)
        
        # Add scrollbar to text area
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_area.yview)
        text_area.configure(yscrollcommand=scrollbar.set)
        
        text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Action buttons for command execution
        action_frame = ttk.Frame(execution_container, style="TFrame")
        action_frame.pack(fill=tk.X)

        build_button = ttk.Button(action_frame, text="🔧 Build Command",
                                  command=lambda: self.display_constructed_command(category_name, frame),
                                  style="Modern.TButton")
        build_button.pack(side=tk.LEFT, padx=(0, 10))

        copy_button = ttk.Button(action_frame, text="📋 Copy to Clipboard",
                                 command=lambda: self.copy_command(text_area.get("1.0", tk.END)),
                                 style="Modern.TButton")
        copy_button.pack(side=tk.LEFT, padx=(0, 10))

        execute_button = ttk.Button(action_frame, text="▶️ Execute",
                                    command=lambda: self.execute_command(category_name, text_area.get("1.0", tk.END), frame),
                                    style="Success.TButton")
        execute_button.pack(side=tk.LEFT)

        # Store references for later use
        frame.button_frame = action_frame
        frame.command_entry = command_entry
        frame.description_entry = description_entry
        frame.text_area = text_area
        frame.description_combobox = description_combobox
        frame.input_widgets = {}
        frame.input_frame = input_frame

    def create_category_content(self, frame, category_name, command_label_text, add_button_text, link_text=None, link_url=None):
        """
        Creates the content for a category frame.

        Args:
            frame (ttk.Frame): The frame to add the content to.
            category_name (str): The name of the category.
            command_label_text (str): The text for the command label.
            add_button_text (str): The text for the add button.
            link_text (str, optional): Text for the clickable link. Defaults to None.
            link_url (str, optional): URL to open when the link is clicked. Defaults to None.
        """
        command_label = ttk.Label(frame, text=command_label_text, style="TLabel")
        command_label.pack(pady=(5, 0))
        command_entry = ttk.Entry(frame, width=50, style="TEntry")
        command_entry.pack(pady=(0, 5))

        description_label = ttk.Label(frame, text="Description:", style="TLabel")
        description_label.pack(pady=(5, 0))
        description_entry = ttk.Entry(frame, width=50, style="TEntry")
        description_entry.pack(pady=(0, 5))

        add_remove_frame = ttk.Frame(frame, style="TFrame")
        add_remove_frame.pack(pady=(5, 5), anchor="center")

        add_button = ttk.Button(add_remove_frame, text=add_button_text,
                                command=lambda: self.add_command(category_name, command_entry.get(),
                                                                 description_entry.get()),
                                style="TButton")
        add_button.pack(side=tk.LEFT, padx=(0, 5))

        remove_button = ttk.Button(add_remove_frame, text="Remove",
                                   command=lambda: self.remove_command(category_name, frame),
                                   style="Red.TButton")
        remove_button.pack(side=tk.LEFT)

        
        if category_name == "GAM" and link_text and link_url:
            link_label = ttk.Label(frame, text=link_text, style="Link.TLabel")
            link_label.pack(pady=(5, 0), anchor="w", padx=5)
            link_label.bind("<Button-1>", lambda event, url=link_url: self.open_web_link(url))

     
        select_command_label = ttk.Label(frame, text="Select Command:", style="TLabel")
        select_command_label.pack(pady=(5, 0))
        description_combobox = ttk.Combobox(frame, width=50, state="readonly", style="TCombobox")
        description_combobox.pack(padx=5, pady=5)
        description_combobox.bind("<<ComboboxSelected>>",
                                 lambda event: self.update_command_display(event, category_name, frame))

        text_area = tk.Text(frame, height=10, width=60, state=tk.DISABLED, font=('Arial', 10),
                             bg="#f8f8f8", fg="#333")
        text_area.pack(padx=5, pady=5)

        button_frame = ttk.Frame(frame, style="TFrame")
        button_frame.pack(pady=(5, 5), anchor="center")

        copy_button = ttk.Button(button_frame, text="Copy to Clipboard",
                                 command=lambda: self.copy_command(text_area.get("1.0", tk.END)),
                                 style="TButton")
        copy_button.pack(side=tk.LEFT)

        build_button = ttk.Button(button_frame, text="Build Command",
                                  command=lambda: self.display_constructed_command(category_name, frame),
                                  style="TButton")
        build_button.pack(side=tk.LEFT, padx=(5, 0))

        execute_button = ttk.Button(button_frame, text="Execute",
                                    command=lambda: self.execute_command(category_name, text_area.get("1.0", tk.END), frame),
                                    style="Green.TButton")
        execute_button.pack(side=tk.LEFT, padx=(5, 0))

        frame.button_frame = button_frame
        frame.command_entry = command_entry
        frame.description_entry = description_entry
        frame.text_area = text_area
        frame.description_combobox = description_combobox
        frame.input_widgets = {}
        frame.input_frame = ttk.Frame(frame, style="TFrame")
        frame.input_frame.pack(padx=5, pady=5, fill=tk.X)

    def add_command(self, category, command, description=""):
        """
        Adds a command to the specified category.

        Args:
            category (str): The category to add the command to.
            command (str): The command to add.
            description (str, optional): A description of the command. Defaults to "".
        """
        if not command:
            self.set_status_text("Error: Command cannot be empty.")
            messagebox.showerror("Error", "Command cannot be empty.")
            return

     
        if not description.strip():
            self.set_status_text("Error: Description cannot be empty.")
            messagebox.showerror("Error", "Description cannot be empty. Please provide a description for the command.")
            return

        if category not in self.commands:
            self.commands[category] = []
        for cmd_data in self.commands[category]:
            if cmd_data["command"] == command and cmd_data["description"] == description:
                self.set_status_text("Error: Duplicate command.")
                messagebox.showerror("Error", "Duplicate command.")
                return
        self.commands[category].append({"command": command, "description": description})
        self.save_commands()
        self.update_description_options(category)
        self.set_status_text(f"Command added to {category} category.")
        if category == "GAM":
            self.gam_frame.command_entry.delete(0, tk.END)
            self.gam_frame.description_entry.delete(0, tk.END)
        elif category == "AD":
            self.ad_frame.command_entry.delete(0, tk.END)
            self.ad_frame.description_entry.delete(0, tk.END)
        elif category == "PowerShell":
            self.powershell_frame.command_entry.delete(0, tk.END)
            self.powershell_frame.description_entry.delete(0, tk.END)

    def display_commands(self, category):
        """
        Displays the commands for the specified category in the text area.

        Args:
            category (str): The category to display the commands for.
        """
        if category not in self.commands:
            self.commands[category] = []

        text_area = None
        if category == "GAM":
            text_area = self.gam_frame.text_area
        elif category == "AD":
            text_area = self.ad_frame.text_area
        elif category == "PowerShell":
            text_area = self.powershell_frame.text_area

        text_area.config(state=tk.DISABLED)
        text_area.delete("1.0", tk.END)

    def update_command_display(self, event, category, frame):
        """
        Updates the command display based on the selected description.  Also creates input fields.

        Args:
            event (tkinter.Event): The event that triggered the update.
            category (str): The category of the command.
            frame (ttk.Frame): The frame containing the widgets.
        """
        if category not in self.commands:
            return

        selected_description = frame.description_combobox.get()

        for cmd_data in self.commands[category]:
            if cmd_data["description"] == selected_description:
                command_template = cmd_data["command"]
                break
        else:
            return

        for widget in frame.input_widgets.values():
            widget.destroy()
        frame.input_widgets = {}

        for widget in frame.input_frame.winfo_children():
            widget.destroy()

        placeholders = re.findall(r"<([^>]+)>", command_template)
        if placeholders:
            for i, placeholder in enumerate(placeholders):
                label = ttk.Label(frame.input_frame, text=placeholder + ":", style="TLabel")
                label.grid(row=i, column=0, sticky=tk.W)
                entry = ttk.Entry(frame.input_frame, width=30, style="TEntry")
                entry.grid(row=i, column=1, sticky=tk.W)
                frame.input_widgets[placeholder] = entry

        self.display_constructed_command(category, frame)

    def display_constructed_command(self, category, frame):
        """
        Displays the constructed command in the text area.

        Args:
            category (str): The category of the command.
            frame (ttk.Frame): The frame containing the widgets.
        """
        if category not in self.commands:
            return

        selected_description = frame.description_combobox.get()
        for cmd_data in self.commands[category]:
            if cmd_data["description"] == selected_description:
                command_template = cmd_data["command"]
                break
        else:
            return
        constructed_command = command_template
        for placeholder, entry_widget in frame.input_widgets.items():
            constructed_command = constructed_command.replace(f"<{placeholder}>", entry_widget.get())

        frame.text_area.config(state=tk.NORMAL)
        frame.text_area.delete("1.0", tk.END)
        frame.text_area.insert(tk.END, constructed_command)
        frame.text_area.config(state=tk.DISABLED)

    def update_description_options(self, category):
        """
        Updates the options in the description combobox for the given category.

        Args:
            category (str): The category to update the combobox for.
        """
        if category not in self.commands:
            self.commands[category] = []
        descriptions = [""]
        for cmd_data in self.commands[category]:
            if cmd_data["description"]:
                descriptions.append(cmd_data["description"])
        if category == "GAM":
            self.gam_frame.description_combobox["values"] = (
                descriptions
            )
            if descriptions:
                self.gam_frame.description_combobox.current(0)
        elif category == "AD":
            self.ad_frame.description_combobox["values"] = (
                descriptions
            )
            if descriptions:
                self.ad_frame.description_combobox.current(0)
        elif category == "PowerShell":
            self.powershell_frame.description_combobox["values"] = (
                descriptions
            )
            if descriptions:
                self.powershell_frame.description_combobox.current(0)

    def copy_command(self, text):
        """
        Copies the given text to the clipboard.

        Args:
            text (str): The text to copy.
        """
        if not text.strip():
            self.set_status_text("Nothing to copy.")
            messagebox.showinfo("Info", "Nothing to copy.")
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.set_status_text("Command copied to clipboard.")
        messagebox.showinfo("Copied", "Command copied to clipboard!")

    def execute_command(self, category, command, frame):
        """
        Executes the command based on the category and copies the command.

        Args:
            category (str): The category of the command.
            command (str): The command to execute.
            frame (ttk.Frame): The frame containing the widgets.
        """
        if not command.strip():
            self.set_status_text("Nothing to execute.")
            messagebox.showinfo("Info", "Nothing to execute.")
            return

        self.copy_command(command) 

        if category == "PowerShell" or category == "AD":
            try:
                process = subprocess.Popen(["powershell.exe", "-Command", command],
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                output = stdout.decode("utf-8").strip()
                error_message = stderr.decode("utf-8").strip()

                if process.returncode != 0:
                    self.set_status_text(f"PowerShell/AD Command Execution Failed. Error: {error_message}")
                    messagebox.showerror("Error",
                                         f"PowerShell/AD Command Execution Failed.\nError Details:\n{error_message}\n\nOutput:\n{output}")
                else:
                    self.set_status_text("PowerShell/AD command executed successfully. Command copied to clipboard.")
                    messagebox.showinfo("Success", f"PowerShell/AD command executed successfully.\n\nOutput:\n{output}\n\nCommand copied to clipboard!")
                frame.text_area.config(state=tk.NORMAL)
                frame.text_area.delete("1.0", tk.END)
                frame.text_area.insert(tk.END, output)
                frame.text_area.config(state=tk.DISABLED)

            except Exception as e:
                error_message = str(e)
                self.set_status_text(f"Error executing PowerShell/AD command: {error_message}")
                messagebox.showerror("Error", f"Could not execute PowerShell/AD command:\n{error_message}\n\nCommand copied to clipboard!")

        elif category == "GAM":
            webbrowser.open("https://shell.cloud.google.com/")
            self.set_status_text("Opening Google Cloud Shell... Command copied to clipboard.")
            messagebox.showinfo("Info", "Opening Google Cloud Shell...\n\nCommand copied to clipboard!")
        else:
            self.set_status_text(f"Cannot execute command for category: {category}")
            messagebox.showerror("Error", f"Cannot execute command for category: {category}\n\nCommand copied to clipboard!")

    def remove_command(self, category, frame):
        """
        Removes the selected command from the specified category.

        Args:
            category (str): The category to remove the command from.
            frame (ttk.Frame): The frame containing the widgets.
        """
        if category not in self.commands:
            return

        selected_description = frame.description_combobox.get()
        for i, cmd_data in enumerate(self.commands[category]):
            if cmd_data["description"] == selected_description:
                del self.commands[category][i]
                self.save_commands()
                self.update_description_options(category)
                self.display_commands(category)
                self.set_status_text(f"Command removed from {category} category.")
                return

        self.set_status_text("No command selected to remove.")
        messagebox.showinfo("Info", "No command selected to remove.")

    def load_all_commands(self):
        """
        Loads all commands from the data file.
        """
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r") as f:
                    self.commands = json.load(f)
                self.set_status_text("Command data loaded.")
                self.remove_duplicate_commands()  
            else:
                self.commands = {"GAM": [], "AD": [], "PowerShell": []}  
                self.set_status_text("No command data found. Starting with empty data.")
        except FileNotFoundError:
            self.commands = {"GAM": [], "AD": [], "PowerShell": []}  
            self.set_status_text("No command data found. Starting with empty data.")
        except json.JSONDecodeError:
            self.commands = {"GAM": [], "AD": [], "PowerShell": []}  
            self.set_status_text("Command data file is corrupted. Starting with empty data.")
        except Exception as e:
            self.commands = {"GAM": [], "AD": [], "PowerShell": []}  
            self.set_status_text(f"Error loading command data: {e}. Starting with empty data.")

        self.update_description_options("GAM")
        self.update_description_options("AD")
        self.update_description_options("PowerShell")

    def save_commands(self):
        """
        Saves all commands to the data file.
        """
        try:
            with open(self.data_file, "w") as f:
                json.dump(self.commands, f, indent=4)
            self.set_status_text("Command data saved.")
        except Exception as e:
            self.set_status_text(f"Error saving command data: {e}")
            messagebox.showerror("Error", f"Could not save commands: {e}")

    def set_status_text(self, text):
        """
        Sets the text of the status bar.

        Args:
            text (str): The text to display.
        """
        if hasattr(self, 'status_bar'):
            self.status_bar.config(text=text)

    def remove_duplicate_commands(self):
        """Removes duplicate commands from the loaded data."""
        for category in self.commands:
            unique_commands = []
            seen_commands = set()
            for cmd_data in self.commands[category]:
                cmd_tuple = (cmd_data["command"], cmd_data["description"])
                if cmd_tuple not in seen_commands:
                    seen_commands.add(cmd_tuple)
                    unique_commands.append(cmd_data)
            self.commands[category] = unique_commands
        self.save_commands()


def main():
    """
    Main function to run the application.
    """
    root = tk.Tk()
    app = CommandManager(root)
    root.mainloop()


if __name__ == "__main__":
    
    if getattr(sys, 'frozen', False):
        
        os.chdir(sys._MEIPASS)
    main()
