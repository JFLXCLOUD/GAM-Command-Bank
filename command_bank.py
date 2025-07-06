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
    A simple application to store and categorize common commands.
    """

    def __init__(self, root):
        """
        Initializes the main application window.

        Args:
            root (tk.Tk): The root Tkinter window.
        """
        self.root = root
        self.root.title("NYH Command Manager") 
        self.root.geometry("600x620")
        self.root.resizable(False, False)
        self.data_file = self._get_data_file_path("commands.json")
        self.commands = {}
        self.style = ttk.Style()
        self.configure_style()

        print(f"Data file path: {self.data_file}")

        self.create_menu()  
        self.create_widgets()
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

    def configure_style(self):
        """
        Configures the visual style of the application.
        """
        self.style.theme_use('clam')

       
        self.style.configure("TLabel", font=('Arial', 10), foreground="#333")  
        self.style.configure("TEntry", font=('Arial', 10), foreground="#555")  
        self.style.configure("TButton", font=('Arial', 10, 'bold'),  
                             foreground="#fff", background="#4CAF50",
                             relief="flat", borderwidth=0,
                             )
        self.style.configure("Red.TButton", font=('Arial', 10, 'bold'),  
                             foreground="#fff", background="#FF5252",
                             relief="flat", borderwidth=0)
        self.style.configure("Green.TButton", font=('Arial', 12, 'bold'),  
                             foreground="#000", background="#b6fcd5",
                             relief="flat", borderwidth=0)
        self.style.configure("Link.TLabel", font=('Arial', 10, 'underline'), foreground="blue", cursor="hand2") 
        self.style.configure("TCombobox", font=('Arial', 10), foreground="#555")  
        self.style.configure("TText", font=('Arial', 10), foreground="#555") 
        self.style.configure("Treeview", font=('Arial', 10),
                             background="#f0f0f0", foreground="#333",
                             rowheight=24)

        self.style.map("TButton",
                       foreground=[('active', '#fff'), ('disabled', '#888')],
                       background=[('active', '#45a049'), ('disabled', '#ccc')],
                       relief=[('pressed', 'flat'), ('!pressed', 'flat')]
                       )
        self.style.map("Red.TButton",
                       foreground=[('active', '#fff'), ('disabled', '#888')],
                       background=[('active', '#c83e4d'), ('disabled', '#ccc')],
                       relief=[('pressed', 'flat'), ('!pressed', 'flat')]
                       )
        self.style.map("Green.TButton",
                       foreground=[('active', '#000'), ('disabled', '#888')],
                       background=[('active', '#90ee90'), ('disabled', '#ccc')],
                       relief=[('pressed', 'flat'), ('!pressed', 'flat')]
                       )

        self.status_style = ttk.Style()
        self.status_style.configure("Statusbar.TLabel", font=('Arial', 8), foreground="#222",
                                     background="#e0e0e0")

    def create_widgets(self):
        """
        Creates the GUI widgets for the application.
        """
        self.notebook = ttk.Notebook(self.root, style="TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.gam_frame = ttk.Frame(self.notebook, style="TFrame")
        self.ad_frame = ttk.Frame(self.notebook, style="TFrame")
        self.powershell_frame = ttk.Frame(self.notebook, style="TFrame")

        self.notebook.add(self.gam_frame, text="GAM Commands")
        self.notebook.add(self.ad_frame, text="AD Commands")
        self.notebook.add(self.powershell_frame, text="PowerShell")

        self.create_category_content(self.gam_frame, "GAM", "GAM Command", "Add GAM Command", link_text="Complete List of GAM Commands", link_url="https://sites.google.com/view/gam--commands/home?authuser=0")
        self.create_category_content(self.ad_frame, "AD", "AD Command", "Add AD Command")
        self.create_category_content(self.powershell_frame, "PowerShell", "PowerShell Command",
                                     "Add PowerShell Command")

        self.load_commands_button = ttk.Button(self.root, text="Load Commands", command=self.load_all_commands,
                                             style="TButton")
        self.load_commands_button.pack(pady=5, anchor="center")

        self.status_bar = ttk.Label(self.root, text="Ready", anchor=tk.W, style="Statusbar.TLabel")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def open_web_link(self, url):
        """Opens the given URL in the default web browser."""
        webbrowser.open_new(url)

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
