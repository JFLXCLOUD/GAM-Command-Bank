"""
Window chrome for GAM Command Bank.

These pieces make the desktop app look like its own program instead of a
generic Tk window:

* app identity and icons, so the taskbar and every window use the app icon
  rather than the Tk feather
* title bars coloured to match the theme (Windows 10/11)
* an in-app menu bar with themed drop-down menus, replacing the grey
  system menu bar
* themed message / confirm dialogs, replacing the system message boxes
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import ttk

import command_store as cs

IS_WINDOWS = sys.platform == "win32"
APP_USER_MODEL_ID = "JFLX.GAMCommandBank"
ICON_SIZES = (16, 32, 48, 64, 128, 256)


# ─────────────────────────────────────────────────────────────────────────────
# Identity and icons
# ─────────────────────────────────────────────────────────────────────────────
def set_app_identity():
    """Call before creating the Tk root.

    Gives the process its own taskbar identity, so Windows shows and groups
    it as GAM Command Bank rather than as Python, and makes it DPI aware so
    text is crisp on scaled displays.
    """
    if not IS_WINDOWS:
        return
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def load_icon_images(root):
    images = {}
    for size in ICON_SIZES:
        path = cs.resource_path(os.path.join("assets", f"icon-{size}.png"))
        if os.path.exists(path):
            try:
                images[size] = tk.PhotoImage(master=root, file=path)
            except tk.TclError:
                pass
    return images


def apply_app_icon(root, images):
    """Set the icon for the main window *and* every window created later.

    ``iconphoto(True, ...)`` sets both the small (title bar) and large
    (taskbar / Alt+Tab) icons. Setting only the small one is what left the
    Tk feather showing in the taskbar.
    """
    if images:
        try:
            root.iconphoto(True, *[images[s] for s in sorted(images, reverse=True)])
        except tk.TclError:
            pass
    if IS_WINDOWS:
        ico = cs.resource_path("icon.ico")
        if os.path.exists(ico):
            try:
                root.iconbitmap(default=ico)
            except tk.TclError:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# Title bar colours (Windows 10 1809+ dark mode, Windows 11 custom colours)
# ─────────────────────────────────────────────────────────────────────────────
def _hwnd(win):
    import ctypes
    win.update_idletasks()
    try:
        frame = win.wm_frame()
        if frame:
            return int(frame, 16)
    except (tk.TclError, ValueError):
        pass
    return ctypes.windll.user32.GetParent(win.winfo_id())


def style_title_bar(win, colors, dark):
    if not IS_WINDOWS:
        return
    try:
        import ctypes
        from ctypes import byref, c_int, sizeof

        hwnd = _hwnd(win)
        dwm = ctypes.windll.dwmapi

        on = c_int(1 if dark else 0)
        # 20 = DWMWA_USE_IMMERSIVE_DARK_MODE; 19 on builds before 20H1
        if dwm.DwmSetWindowAttribute(hwnd, 20, byref(on), sizeof(on)) != 0:
            dwm.DwmSetWindowAttribute(hwnd, 19, byref(on), sizeof(on))

        def colorref(hex_color):
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return c_int(r | (g << 8) | (b << 16))

        # Windows 11 only; ignored elsewhere
        for attr, key in ((35, "surface"), (36, "text"), (34, "border")):
            value = colorref(colors[key])
            dwm.DwmSetWindowAttribute(hwnd, attr, byref(value), sizeof(value))

        # Repaint the frame so a change of theme shows immediately.
        SWP_FLAGS = 0x0001 | 0x0002 | 0x0004 | 0x0020  # NOSIZE|NOMOVE|NOZORDER|FRAMECHANGED
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_FLAGS)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Menu bar
# ─────────────────────────────────────────────────────────────────────────────
SEPARATOR = None


class PopupMenu:
    """A themed drop-down list of (label, accelerator, command) items."""

    def __init__(self, bar, index, items, x, y):
        self.bar = bar
        C, F = bar.C, bar.F
        self.win = win = tk.Toplevel(bar.root)
        win.wm_overrideredirect(True)
        win.configure(bg=C["border"])
        try:
            win.wm_attributes("-topmost", True)
        except tk.TclError:
            pass
        body = tk.Frame(win, bg=C["surface"], padx=4, pady=4)
        body.pack(padx=1, pady=1)

        self.rows = []
        for item in items:
            if item is SEPARATOR:
                tk.Frame(body, bg=C["border"], height=1).pack(fill=tk.X, padx=6, pady=4)
                continue
            label, accel, command = item
            row = tk.Frame(body, bg=C["surface"], cursor="hand2")
            row.pack(fill=tk.X)
            name = tk.Label(row, text=label, font=F["base"], fg=C["text"], bg=C["surface"],
                            anchor=tk.W, padx=10, pady=5)
            name.pack(side=tk.LEFT, fill=tk.X, expand=True)
            key = tk.Label(row, text=accel or "", font=F["small"], fg=C["dim"], bg=C["surface"],
                           anchor=tk.E, padx=10)
            key.pack(side=tk.RIGHT)
            idx = len(self.rows)
            self.rows.append((row, name, key, command))
            for w in (row, name, key):
                w.bind("<Enter>", lambda e, i=idx: self.highlight(i))
                w.bind("<ButtonRelease-1>", lambda e, i=idx: self.activate(i))

        self.active = None
        win.bind("<Up>", lambda e: self.move(-1))
        win.bind("<Down>", lambda e: self.move(1))
        win.bind("<Return>", lambda e: self.activate(self.active))
        win.bind("<space>", lambda e: self.activate(self.active))
        win.bind("<Escape>", lambda e: bar.close())
        win.bind("<Left>", lambda e: bar.open(index - 1, keyboard=True))
        win.bind("<Right>", lambda e: bar.open(index + 1, keyboard=True))

        win.update_idletasks()
        # keep the menu on screen
        x = min(x, win.winfo_screenwidth() - win.winfo_reqwidth() - 4)
        win.geometry(f"+{max(x, 0)}+{y}")
        win.focus_force()

    def highlight(self, i):
        C = self.bar.C
        for j, (row, name, key, _) in enumerate(self.rows):
            on = j == i
            bg = C["primary"] if on else C["surface"]
            row.config(bg=bg)
            name.config(bg=bg, fg=C["on_primary"] if on else C["text"])
            key.config(bg=bg, fg=C["on_primary"] if on else C["dim"])
        self.active = i

    def move(self, delta):
        if not self.rows:
            return
        i = 0 if self.active is None else (self.active + delta) % len(self.rows)
        self.highlight(i)

    def activate(self, i):
        if i is None:
            return
        command = self.rows[i][3]
        self.bar.close()
        # run after the menu is gone so dialogs get focus
        self.bar.root.after(1, command)

    def destroy(self):
        self.win.destroy()


class MenuBar:
    """In-app menu bar. `menus` is a list of (title, items)."""

    def __init__(self, app, parent, menus):
        self.app = app
        self.root = app.root
        self.C, self.F = app.C, app.F
        self.menus = menus
        self.buttons = []
        self.popup = None
        self.open_index = None

        frame = tk.Frame(parent, bg=self.C["surface"])
        frame.pack(side=tk.LEFT, padx=(8, 0))
        for i, (title, _) in enumerate(menus):
            b = tk.Label(frame, text=title, font=self.F["base"], fg=self.C["muted"],
                         bg=self.C["surface"], padx=9, pady=5, cursor="hand2")
            b.pack(side=tk.LEFT)
            b.bind("<Button-1>", lambda e, i=i: self.toggle(i))
            b.bind("<Enter>", lambda e, i=i: self._on_enter(i))
            b.bind("<Leave>", lambda e, i=i: self._paint(i))
            self.buttons.append(b)

    # The app routes these root-level events here (bound once, so rebuilding
    # the UI for a theme change doesn't stack handlers):
    #   <Button-1> anywhere -> click_anywhere, <FocusOut> -> check_focus,
    #   root <Configure> -> close

    def _paint(self, i, hover=False):
        C = self.C
        on = i == self.open_index
        self.buttons[i].config(bg=C["surface2"] if (on or hover) else C["surface"],
                               fg=C["text"] if (on or hover) else C["muted"])

    def _on_enter(self, i):
        if self.popup is not None and i != self.open_index:
            self.open(i)
        else:
            self._paint(i, hover=True)

    def toggle(self, i):
        if self.open_index == i:
            self.close()
        else:
            self.open(i)
        return "break"

    def open(self, i, keyboard=False):
        i %= len(self.menus)
        self.close()
        self.open_index = i
        for j in range(len(self.buttons)):
            self._paint(j)
        b = self.buttons[i]
        self.popup = PopupMenu(self, i, self.menus[i][1], b.winfo_rootx(),
                               b.winfo_rooty() + b.winfo_height() + 2)
        if keyboard:
            self.popup.move(1)
        return "break"

    def close(self):
        if self.popup is not None:
            try:
                self.popup.destroy()
            except tk.TclError:
                pass
            self.popup = None
        prev, self.open_index = self.open_index, None
        if prev is not None:
            try:
                self._paint(prev)
            except tk.TclError:
                pass

    def click_anywhere(self, event):
        if self.popup is None:
            return
        try:
            top = event.widget.winfo_toplevel()
        except (AttributeError, KeyError, tk.TclError):
            return
        if top is self.popup.win or event.widget in self.buttons:
            return
        self.close()

    def check_focus(self):
        if self.popup is None:
            return
        try:
            if self.root.focus_get() is None:
                self.close()
        except (KeyError, tk.TclError):
            self.close()


# ─────────────────────────────────────────────────────────────────────────────
# Dialogs
# ─────────────────────────────────────────────────────────────────────────────
_KIND = {
    "info": ("i", "primary"),
    "warning": ("!", "warning"),
    "error": ("✕", "danger"),
    "question": ("?", "primary"),
}


def themed_dialog(app, title, message, *, kind="info", code=None,
                  buttons=(("OK", True, "P"),), cancel_value=None, default=0):
    """Show a modal themed dialog and return the chosen button's value.

    `buttons` is a sequence of (label, value, style) drawn left to right;
    `default` is the index activated by Enter, Esc returns `cancel_value`.
    """
    C, F = app.C, app.F
    glyph, color_key = _KIND.get(kind, _KIND["info"])
    result = {"value": cancel_value}

    win = tk.Toplevel(app.root)
    win.withdraw()
    win.title(title)
    win.configure(bg=C["surface"])
    win.resizable(False, False)
    win.transient(app.root)

    tk.Frame(win, bg=C[color_key], height=3).pack(fill=tk.X)
    body = tk.Frame(win, bg=C["surface"])
    body.pack(fill=tk.BOTH, expand=True, padx=22, pady=(18, 8))

    badge = tk.Canvas(body, width=34, height=34, bg=C["surface"], highlightthickness=0)
    badge.create_oval(1, 1, 33, 33, fill=C[color_key], outline="")
    badge.create_text(17, 17, text=glyph, fill="#FFFFFF", font=F["heading"])
    badge.grid(row=0, column=0, rowspan=3, sticky="n", padx=(0, 14))

    tk.Label(body, text=title, font=F["heading"], fg=C["text"], bg=C["surface"],
             anchor=tk.W, justify=tk.LEFT).grid(row=0, column=1, sticky="w")
    if message:
        tk.Label(body, text=message, font=F["base"], fg=C["muted"], bg=C["surface"],
                 anchor=tk.W, justify=tk.LEFT, wraplength=440).grid(row=1, column=1, sticky="w", pady=(4, 0))
    if code:
        box = tk.Text(body, font=F["mono"], bg=C["surface2"], fg=C["text"], relief="flat",
                      wrap=tk.WORD, width=56, padx=10, pady=8, highlightthickness=1,
                      highlightbackground=C["border"])
        box.insert("1.0", code)
        lines = int(box.index("end-1c").split(".")[0])
        box.config(height=min(max(lines, 1) + (len(code) // 56), 8), state=tk.DISABLED)
        box.grid(row=2, column=1, sticky="ew", pady=(10, 0))

    row = tk.Frame(win, bg=C["surface"])
    row.pack(fill=tk.X, padx=22, pady=(10, 18))

    def choose(value):
        result["value"] = value
        win.destroy()

    widgets = []
    for label, value, style in buttons:
        b = ttk.Button(row, text=label, style=f"{style}.TButton", command=lambda v=value: choose(v))
        widgets.append(b)
    for b in reversed(widgets):
        b.pack(side=tk.RIGHT, padx=(8, 0))

    win.bind("<Escape>", lambda e: choose(cancel_value))
    def on_return(event):
        focused = win.focus_get()
        (focused if focused in widgets else widgets[default]).invoke()

    win.bind("<Return>", on_return)
    win.protocol("WM_DELETE_WINDOW", lambda: choose(cancel_value))

    win.update_idletasks()
    x = app.root.winfo_rootx() + (app.root.winfo_width() - win.winfo_reqwidth()) // 2
    y = app.root.winfo_rooty() + max((app.root.winfo_height() - win.winfo_reqheight()) // 3, 40)
    win.geometry(f"+{max(x, 0)}+{max(y, 0)}")
    app.style_window(win)
    win.deiconify()
    win.grab_set()
    win.lift()
    widgets[default].focus_force()   # modal: take keyboard focus even if the app isn't active
    app.root.wait_window(win)
    return result["value"]
