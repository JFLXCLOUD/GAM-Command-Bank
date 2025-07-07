# GAM-Command-Bank
A simple application to store, fill, execute, and categorize common commands used by GAM, PS and AD.


The application stores your commands in a file named `commands.json`. For the application to function correctly, this `commands.json` file MUST be located in the SAME folder as the `GAM Command Bank.exe` file when you run the executable.

If the `commands.json` file is not found in the same folder, the application will start with an empty command list. Any commands you add during that session will be saved to a new `commands.json` file in that same folder.

Therefore, to ensure your saved commands are loaded when you open the application, please keep the `commands.json` file in the same directory as the `GAM Command Bank.exe`.

Usage:

1.  Run the `GAM_Command_Bank_v0.1.0.exe` file.

2.  Navigate through the tabs for GAM Commands, AD Commands, and PowerShell.

3.  To add a new command:
    * Enter the command in the "Command" field.
    * Optionally, add a description in the "Description (Optional)" field.
    * Click the "Add Command" button.

4.  To remove a command:
    * Select a description from the "Select Command:" dropdown.
    * Click the "Remove" button.

5.  To execute a command (PowerShell/AD):
    * Select a command from the dropdown (if you added descriptions).
    * If the command has placeholders (e.g., `<user>`), enter the specific values in the input fields that appear.
    * Click the "Build Command" button to see the final command.
    * Click the "Execute" button to run the command. The output will be displayed in the text area. The command will also be copied to your clipboard.

6.  To execute a GAM command:
    * Select a command from the dropdown (if you added descriptions).
    * If the command has placeholders, enter the specific values.
    * Click "Build Command".
    * Click "Execute". This will open the Google Cloud Shell in your web browser, and the command will be copied to your clipboard.

7.  Click "Copy to Clipboard" to manually copy the text in the output area.

8.  Click "Load Commands" to manually reload commands from the `commands.json` file (though this happens automatically on startup).

9.  For a complete list of GAM commands, click the "Complete List of GAM Commands" link on the GAM Commands tab.

10. The "About" menu in the application provides information about the application. The "File" menu allows you to exit.
