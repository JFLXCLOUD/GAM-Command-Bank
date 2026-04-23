import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import re
import subprocess
import webbrowser
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# Tooltip helper
# ─────────────────────────────────────────────────────────────────────────────
class Tooltip:
    def __init__(self, widget, text, bg="#161B22", fg="#8B949E", border="#30363D"):
        self.widget = widget
        self.text = text
        self._bg = bg
        self._fg = fg
        self._border = border
        self.tip_window = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text,
                 background=self._bg, foreground=self._fg,
                 font=("Segoe UI", 9), relief="flat",
                 padx=8, pady=4, borderwidth=1,
                 highlightbackground=self._border,
                 highlightthickness=1).pack()

    def hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


# ─────────────────────────────────────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────────────────────────────────────
class CommandManager:

    # ── palettes ─────────────────────────────────────────────────────────────
    DARK = {
        "bg":         "#0D1117",
        "surface":    "#161B22",
        "surface2":   "#21262D",
        "border":     "#30363D",
        "primary":    "#2F81F7",
        "primary_dk": "#1F6FEB",
        "success":    "#3FB950",
        "success_dk": "#2EA043",
        "danger":     "#F85149",
        "danger_dk":  "#DA3633",
        "warning":    "#D29922",
        "warning_dk": "#BB8009",
        "purple":     "#BC8CFF",
        "text":       "#E6EDF3",
        "muted":      "#8B949E",
        "dim":        "#484F58",
        "accent":     "#58A6FF",
        "star":       "#E3B341",
        "tab_sel":    "#2F81F7",
        "header_bar": "#161B22",
    }
    LIGHT = {
        "bg":         "#F6F8FA",
        "surface":    "#FFFFFF",
        "surface2":   "#EFF2F5",
        "border":     "#D0D7DE",
        "primary":    "#0969DA",
        "primary_dk": "#0550AE",
        "success":    "#1A7F37",
        "success_dk": "#116329",
        "danger":     "#CF222E",
        "danger_dk":  "#A40E26",
        "warning":    "#9A6700",
        "warning_dk": "#7D4E00",
        "purple":     "#8250DF",
        "text":       "#1F2328",
        "muted":      "#636C76",
        "dim":        "#9198A1",
        "accent":     "#0969DA",
        "star":       "#BF8700",
        "tab_sel":    "#0969DA",
        "header_bar": "#FFFFFF",
    }

    def __init__(self, root):
        self.root = root
        self._is_dark = True
        self.C = dict(self.DARK)
        self.root.title("GAM Command Bank")
        self.root.geometry("1020x660")
        self.root.resizable(True, True)
        self.root.minsize(820, 540)
        self.root.configure(bg=self.C["bg"])

        try:
            if getattr(sys, "frozen", False):
                icon_path = os.path.join(sys._MEIPASS, "icon.ico")
            else:
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

        self.data_file = self._get_data_file_path("commands.json")
        self.commands: dict = {}
        self._status_job = None
        self._add_visible: dict = {}  # per-category toggle state

        self.style = ttk.Style()
        self._configure_style()
        self._create_menu()
        self._create_widgets()
        self.load_all_commands()

    # =========================================================================
    # STYLE
    # =========================================================================
    def _configure_style(self):
        self.style.theme_use("clam")
        C = self.C

        F  = ("Segoe UI", 10)
        FB = ("Segoe UI", 10, "bold")
        FS = ("Segoe UI", 9)

        # frames
        for name, bg in [("TFrame", C["bg"]), ("S.TFrame", C["surface"]),
                          ("S2.TFrame", C["surface2"])]:
            self.style.configure(name, background=bg)

        # labels
        for name, fg, bg in [
            ("TLabel",    C["text"],  C["bg"]),
            ("S.TLabel",  C["text"],  C["surface"]),
            ("S2.TLabel", C["text"],  C["surface2"]),
            ("M.TLabel",  C["muted"], C["bg"]),
            ("SM.TLabel", C["muted"], C["surface"]),
            ("D.TLabel",  C["dim"],   C["bg"]),
        ]:
            self.style.configure(name, font=F, foreground=fg, background=bg)

        self.style.configure("Link.TLabel",
                             font=("Segoe UI", 9, "underline"),
                             foreground=C["accent"], background=C["surface"],
                             cursor="hand2")

        # notebook
        self.style.configure("TNotebook", background=C["bg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", font=F,
                             background=C["surface"], foreground=C["muted"],
                             padding=[14, 7], borderwidth=0)
        self.style.map("TNotebook.Tab",
                       background=[("selected", C["primary"]), ("active", C["surface2"])],
                       foreground=[("selected", "#FFFFFF"),    ("active", C["text"])],
                       font=[("selected", F), ("active", F)])

        # entry / combobox
        for name in ("TEntry", "TCombobox"):
            self.style.configure(name, font=F, foreground=C["text"],
                                 fieldbackground=C["surface2"],
                                 borderwidth=1, insertcolor=C["primary"],
                                 arrowcolor=C["muted"])
            self.style.map(name,
                           bordercolor=[("focus", C["primary"])],
                           fieldbackground=[("readonly", C["surface2"]),
                                            ("focus",    C["surface2"])])

        # scrollbar
        self.style.configure("TScrollbar",
                             background=C["surface2"], troughcolor=C["surface"],
                             arrowcolor=C["dim"], borderwidth=0, relief="flat")

        # buttons
        def _btn(name, bg, hover, fg="#FFFFFF", pad=(12, 6)):
            self.style.configure(f"{name}.TButton",
                                 font=FB, foreground=fg, background=bg,
                                 relief="flat", borderwidth=0, padding=list(pad))
            self.style.map(f"{name}.TButton",
                           background=[("active", hover), ("pressed", hover)],
                           foreground=[("active", fg)])

        _btn("P",  C["primary"],  C["primary_dk"])
        _btn("G",  C["success"],  C["success_dk"])
        _btn("R",  C["danger"],   C["danger_dk"])
        _btn("W",  C["warning"],  C["warning_dk"])
        _btn("Gh", C["surface2"], C["border"],    fg=C["text"],  pad=(10, 5))

        # combobox dropdown popup
        self.root.option_add("*TCombobox*Listbox*Background",       C["surface2"])
        self.root.option_add("*TCombobox*Listbox*Foreground",       C["text"])
        self.root.option_add("*TCombobox*Listbox*selectBackground", C["primary"])
        self.root.option_add("*TCombobox*Listbox*selectForeground", "#FFFFFF")

    # =========================================================================
    # MENU
    # =========================================================================
    def _create_menu(self):
        C = self.C
        kw = dict(bg=C["surface"], fg=C["text"],
                  activebackground=C["primary"], activeforeground="#fff",
                  borderwidth=0, relief="flat")
        menubar = tk.Menu(self.root, **kw)

        file_m = tk.Menu(menubar, tearoff=0, **kw)
        file_m.add_command(label="⟳  Reload",        command=self.load_all_commands)
        file_m.add_separator()
        file_m.add_command(label="✕  Exit",           command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_m)

        view_m = tk.Menu(menubar, tearoff=0, **kw)
        view_m.add_command(label="★  Favorites",        command=self._show_favorites_window)
        view_m.add_command(label="⌚  Recently Copied",  command=self._show_recent_window)
        view_m.add_separator()
        view_m.add_command(label="☀  Toggle Theme",     command=self._toggle_theme)
        menubar.add_cascade(label="View", menu=view_m)

        ref_m = tk.Menu(menubar, tearoff=0, **kw)
        ref_m.add_command(label="◈ GAM People",       command=lambda: webbrowser.open("https://sites.google.com/view/gam--commands/people"))
        ref_m.add_command(label="◈ GAM Services",     command=lambda: webbrowser.open("https://sites.google.com/view/gam--commands/services"))
        ref_m.add_command(label="◈ Full Reference",   command=lambda: webbrowser.open("https://sites.google.com/view/gam--commands/home"))
        menubar.add_cascade(label="Reference", menu=ref_m)

        about_m = tk.Menu(menubar, tearoff=0, **kw)
        about_m.add_command(label="ℹ  About",         command=self._show_about)
        menubar.add_cascade(label="About", menu=about_m)

        self.root.config(menu=menubar)

    # =========================================================================
    # ROOT LAYOUT
    # =========================================================================
    def _create_widgets(self):
        C = self.C

        # ── Compact header bar ────────────────────────────────────────────
        hbar = tk.Frame(self.root, bg=C["header_bar"], height=46)
        hbar.pack(fill=tk.X)
        hbar.pack_propagate(False)

        # left accent line
        tk.Frame(hbar, bg=C["primary"], width=3).pack(side=tk.LEFT, fill=tk.Y)

        # title
        tk.Label(hbar, text="GAM Command Bank",
                 font=("Segoe UI", 13, "bold"),
                 fg=C["text"], bg=C["header_bar"],
                 padx=14).pack(side=tk.LEFT, fill=tk.Y)

        # version badge
        tk.Label(hbar, text="v3",
                 font=("Segoe UI", 8),
                 fg=C["muted"], bg=C["header_bar"]).pack(side=tk.LEFT)

        # theme toggle button (packs right-to-left so add before search)
        _theme_icon = "☽" if self._is_dark else "☀"
        theme_btn = tk.Label(hbar, text=_theme_icon,
                             font=("Segoe UI", 12),
                             fg=C["muted"], bg=C["header_bar"],
                             cursor="hand2", padx=8)
        theme_btn.pack(side=tk.RIGHT, padx=(0, 4))
        theme_btn.bind("<Button-1>", lambda e: self._toggle_theme())
        Tooltip(theme_btn, "Toggle light / dark mode",
                C["surface"], C["muted"], C["border"])

        # right side: search
        tk.Label(hbar, text="⌕",
                 font=("Segoe UI", 12),
                 fg=C["muted"], bg=C["header_bar"],
                 padx=(6)).pack(side=tk.RIGHT, padx=(0, 4))

        clr_btn = tk.Label(hbar, text="✕",
                           font=("Segoe UI", 10),
                           fg=C["muted"], bg=C["header_bar"],
                           cursor="hand2", padx=6)
        clr_btn.pack(side=tk.RIGHT)
        clr_btn.bind("<Button-1>", lambda e: self._clear_search())
        Tooltip(clr_btn, "Clear search", C["surface"], C["muted"], C["border"])

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        se = tk.Entry(hbar, textvariable=self.search_var,
                      width=32, insertbackground=C["primary"],
                      bg=C["surface2"], fg=C["text"],
                      relief="flat", font=("Segoe UI", 10),
                      highlightthickness=1,
                      highlightbackground=C["border"],
                      highlightcolor=C["primary"])
        se.pack(side=tk.RIGHT, pady=8, padx=(0, 2))
        se.insert(0, "Search commands…")
        se.bind("<FocusIn>",  lambda e: se.delete(0, tk.END) if se.get() == "Search commands…" else None)
        se.bind("<FocusOut>", lambda e: se.insert(0, "Search commands…") if not se.get() else None)

        # ── Notebook ──────────────────────────────────────────────────────
        nb_wrap = tk.Frame(self.root, bg=C["bg"])
        nb_wrap.pack(fill=tk.BOTH, expand=True, padx=12, pady=(10, 0))

        self.notebook = ttk.Notebook(nb_wrap, style="TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.gam_frame        = ttk.Frame(self.notebook, style="TFrame")
        self.ad_frame         = ttk.Frame(self.notebook, style="TFrame")
        self.powershell_frame = ttk.Frame(self.notebook, style="TFrame")

        self.notebook.add(self.gam_frame,        text="  ◈ GAM  ")
        self.notebook.add(self.ad_frame,          text="  ⊞ AD  ")
        self.notebook.add(self.powershell_frame,  text="  ⌨ PowerShell  ")

        self._build_tab(self.gam_frame,        "GAM")
        self._build_tab(self.ad_frame,         "AD")
        self._build_tab(self.powershell_frame, "PowerShell")

        # ── Status bar ────────────────────────────────────────────────────
        sb = tk.Frame(self.root, bg=C["surface"], height=28)
        sb.pack(side=tk.BOTTOM, fill=tk.X)
        sb.pack_propagate(False)
        tk.Frame(sb, bg=C["primary"], height=1).pack(fill=tk.X, side=tk.TOP)

        self.status_bar = tk.Label(sb, text="● Ready", anchor=tk.W,
                                   font=("Segoe UI", 8),
                                   fg=C["muted"], bg=C["surface"],
                                   padx=12)
        self.status_bar.pack(side=tk.LEFT, fill=tk.Y)

        self._count_label = tk.Label(sb, text="", anchor=tk.E,
                                     font=("Segoe UI", 8),
                                     fg=C["dim"], bg=C["surface"],
                                     padx=12)
        self._count_label.pack(side=tk.RIGHT, fill=tk.Y)

    # =========================================================================
    # TAB BUILDER  (compact single-surface layout)
    # =========================================================================
    def _build_tab(self, frame, category):
        C = self.C
        self._add_visible[category] = False

        # ── Main surface card ─────────────────────────────────────────────
        card = tk.Frame(frame, bg=C["surface"],
                        highlightbackground=C["border"], highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # top accent
        tk.Frame(card, bg=C["primary"], height=2).pack(fill=tk.X)

        inner = tk.Frame(card, bg=C["surface"])
        inner.pack(fill=tk.BOTH, expand=True, padx=14, pady=10)

        # ── Row 1: command selector ───────────────────────────────────────
        row1 = tk.Frame(inner, bg=C["surface"])
        row1.pack(fill=tk.X, pady=(0, 6))

        combo = ttk.Combobox(row1, state="readonly", style="TCombobox")
        combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        combo.bind("<<ComboboxSelected>>",
                   lambda e: self.update_command_display(e, category, frame))

        # star
        fav_btn = tk.Label(row1, text="☆", font=("Segoe UI", 13),
                           fg=C["star"], bg=C["surface"],
                           cursor="hand2", padx=6)
        fav_btn.pack(side=tk.LEFT)
        fav_btn.bind("<Button-1>", lambda e: self._toggle_favorite(category, frame))
        Tooltip(fav_btn, "Toggle favorite", C["surface"], C["muted"], C["border"])

        # remove
        rem_btn = ttk.Button(row1, text="⌫",
                             command=lambda: self.remove_command(category, frame),
                             style="R.TButton", width=3)
        rem_btn.pack(side=tk.LEFT, padx=(4, 0))
        Tooltip(rem_btn, "Remove selected command", C["surface"], C["muted"], C["border"])

        # add toggle
        add_toggle = ttk.Button(row1, text="＋",
                                command=lambda: self._toggle_add_panel(category, add_panel),
                                style="Gh.TButton", width=3)
        add_toggle.pack(side=tk.LEFT, padx=(4, 0))
        Tooltip(add_toggle, "Add new command", C["surface"], C["muted"], C["border"])

        # reference link (GAM only)
        if category == "GAM":
            lk = tk.Label(row1, text="↗ Docs",
                          font=("Segoe UI", 9, "underline"),
                          fg=C["accent"], bg=C["surface"],
                          cursor="hand2", padx=6)
            lk.pack(side=tk.LEFT, padx=(6, 0))
            lk.bind("<Button-1>", lambda e: webbrowser.open("https://sites.google.com/view/gam--commands/home"))
            Tooltip(lk, "Open GAM reference site", C["surface"], C["muted"], C["border"])

        # ── Add panel (hidden by default) ─────────────────────────────────
        add_panel = tk.Frame(inner, bg=C["surface2"],
                             highlightbackground=C["border"], highlightthickness=1)
        # NOT packed yet — toggled by button

        ap_inner = tk.Frame(add_panel, bg=C["surface2"])
        ap_inner.pack(fill=tk.X, padx=10, pady=8)

        cmd_row = tk.Frame(ap_inner, bg=C["surface2"])
        cmd_row.pack(fill=tk.X, pady=(0, 4))
        tk.Label(cmd_row, text="Command", font=("Segoe UI", 9),
                 fg=C["muted"], bg=C["surface2"], width=10,
                 anchor=tk.W).pack(side=tk.LEFT)
        cmd_entry = tk.Entry(cmd_row, bg=C["surface2"], fg=C["text"],
                             insertbackground=C["primary"], relief="flat",
                             font=("Consolas", 10),
                             highlightthickness=1,
                             highlightbackground=C["border"],
                             highlightcolor=C["primary"])
        cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        desc_row = tk.Frame(ap_inner, bg=C["surface2"])
        desc_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(desc_row, text="Description", font=("Segoe UI", 9),
                 fg=C["muted"], bg=C["surface2"], width=10,
                 anchor=tk.W).pack(side=tk.LEFT)
        desc_entry = tk.Entry(desc_row, bg=C["surface2"], fg=C["text"],
                              insertbackground=C["primary"], relief="flat",
                              font=("Segoe UI", 10),
                              highlightthickness=1,
                              highlightbackground=C["border"],
                              highlightcolor=C["primary"])
        desc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        save_btn = ttk.Button(ap_inner, text="＋ Save",
                              command=lambda: self._do_add(category, cmd_entry, desc_entry, add_panel),
                              style="G.TButton")
        save_btn.pack(side=tk.LEFT)

        tk.Label(ap_inner,
                 text="Use <placeholder> for variable fields",
                 font=("Segoe UI", 8), fg=C["dim"],
                 bg=C["surface2"]).pack(side=tk.LEFT, padx=(10, 0))

        # ── Row 2: dynamic placeholder inputs ────────────────────────────
        input_frame = tk.Frame(inner, bg=C["surface"])
        input_frame.pack(fill=tk.X, pady=(0, 4))

        # ── Row 3: output area ────────────────────────────────────────────
        out_wrap = tk.Frame(inner, bg=C["surface2"],
                            highlightbackground=C["border"], highlightthickness=1)
        out_wrap.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        text_area = tk.Text(out_wrap, height=6,
                            font=("Consolas", 10),
                            bg=C["surface2"], fg=C["text"],
                            selectbackground=C["primary"],
                            insertbackground=C["primary"],
                            relief="flat", borderwidth=0,
                            wrap=tk.WORD, state=tk.DISABLED,
                            padx=10, pady=6)
        vsb = ttk.Scrollbar(out_wrap, orient=tk.VERTICAL, command=text_area.yview)
        text_area.configure(yscrollcommand=vsb.set)
        text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # ── Row 4: action buttons ─────────────────────────────────────────
        act = tk.Frame(inner, bg=C["surface"])
        act.pack(fill=tk.X)

        btns = [
            ("⎘ Copy",    "P",   "Copy command to clipboard",lambda: self.copy_command(text_area.get("1.0", tk.END), category, frame)),
            ("▶ Execute", "G",   "Execute command",          lambda: self.execute_command(category, text_area.get("1.0", tk.END), frame)),
            ("⊘ Clear",   "W",   "Clear output",             lambda: self._clear_output(text_area)),
        ]
        for label, style, tip, cmd in btns:
            b = ttk.Button(act, text=label, command=cmd, style=f"{style}.TButton")
            b.pack(side=tk.LEFT, padx=(0, 6))
            Tooltip(b, tip, C["surface"], C["muted"], C["border"])

        # store refs on frame
        frame.command_entry        = cmd_entry
        frame.description_entry    = desc_entry
        frame.text_area            = text_area
        frame.description_combobox = combo
        frame.input_widgets        = {}
        frame.input_frame          = input_frame
        frame.fav_btn              = fav_btn

    def _toggle_add_panel(self, category, panel):
        if self._add_visible.get(category):
            panel.pack_forget()
            self._add_visible[category] = False
        else:
            panel.pack(fill=tk.X, pady=(0, 8), before=self._frame_for(category).input_frame)
            self._add_visible[category] = True

    def _do_add(self, category, cmd_entry, desc_entry, panel):
        self.add_command(category, cmd_entry.get(), desc_entry.get())
        if cmd_entry.get() == "" or desc_entry.get() == "":
            return
        cmd_entry.delete(0, tk.END)
        desc_entry.delete(0, tk.END)
        # collapse panel after save
        panel.pack_forget()
        self._add_visible[category] = False

    # =========================================================================
    # SEARCH
    # =========================================================================
    def _on_search(self, *_):
        query = self.search_var.get().strip().lower()
        if query in ("", "search commands…"):
            self._restore_all_combos()
            return
        for category, frame in self._category_frames():
            if category not in self.commands:
                continue
            matches = [cmd["description"] for cmd in self.commands[category]
                       if query in cmd["command"].lower()
                       or query in cmd["description"].lower()]
            frame.description_combobox["values"] = matches or ["— no results —"]
            if matches:
                frame.description_combobox.current(0)
                self.update_command_display(None, category, frame)

    def _clear_search(self):
        self.search_var.set("")
        self._restore_all_combos()

    def _restore_all_combos(self):
        for cat, _ in self._category_frames():
            self.update_description_options(cat)

    def _category_frames(self):
        return [("GAM",        self.gam_frame),
                ("AD",         self.ad_frame),
                ("PowerShell", self.powershell_frame)]

    # =========================================================================
    # FAVORITES
    # =========================================================================
    def _toggle_favorite(self, category, frame):
        sel = frame.description_combobox.get()
        if not sel:
            return
        for cmd in self.commands.get(category, []):
            if cmd["description"] == sel:
                cmd["favorite"] = not cmd.get("favorite", False)
                frame.fav_btn.config(text="★" if cmd["favorite"] else "☆")
                self.save_commands()
                verb = "added to" if cmd["favorite"] else "removed from"
                self.set_status(f"★ '{sel}' {verb} favorites.")
                return

    def _update_fav_icon(self, category, frame):
        sel = frame.description_combobox.get()
        for cmd in self.commands.get(category, []):
            if cmd["description"] == sel:
                frame.fav_btn.config(text="★" if cmd.get("favorite") else "☆")
                return
        frame.fav_btn.config(text="☆")

    def _show_favorites_window(self):
        C = self.C
        favs = [
            (cat, cmd["description"], cmd["command"])
            for cat in ["GAM", "AD", "PowerShell"]
            for cmd in self.commands.get(cat, [])
            if cmd.get("favorite")
        ]
        win = tk.Toplevel(self.root)
        win.title("★ Favorites")
        win.geometry("820x400")
        win.configure(bg=C["bg"])
        win.grab_set()
        tk.Frame(win, bg=C["star"], height=2).pack(fill=tk.X)
        hdr = tk.Frame(win, bg=C["bg"])
        hdr.pack(fill=tk.X, padx=18, pady=(12, 4))
        tk.Label(hdr, text="★ Favorites", font=("Segoe UI", 12, "bold"),
                 fg=C["text"], bg=C["bg"]).pack(side=tk.LEFT)
        tk.Label(hdr, text="double-click or ↗ Go to navigate",
                 font=("Segoe UI", 9), fg=C["muted"],
                 bg=C["bg"]).pack(side=tk.LEFT, padx=(12, 0))
        wrap = tk.Frame(win, bg=C["surface2"],
                        highlightbackground=C["border"], highlightthickness=1)
        wrap.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 8))
        lb = tk.Listbox(wrap, font=("Segoe UI", 10),
                        bg=C["surface2"], fg=C["text"],
                        selectbackground=C["primary"], selectforeground="#FFFFFF",
                        relief="flat", borderwidth=0, activestyle="none",
                        cursor="hand2")
        sb = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        if favs:
            for cat, desc, cmd_text in favs:
                lb.insert(tk.END, f"  [{cat}]  {desc}")
        else:
            lb.insert(tk.END, "  — no favorites yet — add one with the ★ button")
        def _navigate(event=None):
            sel = lb.curselection()
            if not sel or not favs or sel[0] >= len(favs):
                return
            cat, desc, _ = favs[sel[0]]
            win.destroy()
            tab_map = {"GAM": 0, "AD": 1, "PowerShell": 2}
            if cat in tab_map:
                self.notebook.select(tab_map[cat])
            frame = self._frame_for(cat)
            if frame:
                frame.description_combobox.set(desc)
                self.update_command_display(None, cat, frame)
        lb.bind("<Double-Button-1>", _navigate)
        lb.bind("<Return>", _navigate)
        btn_row = tk.Frame(win, bg=C["bg"])
        btn_row.pack(pady=(0, 14))
        ttk.Button(btn_row, text="↗ Go to Selected",
                   command=_navigate, style="P.TButton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_row, text="Close",
                   command=win.destroy, style="Gh.TButton").pack(side=tk.LEFT)

    def _show_recent_window(self):
        C = self.C
        recent = [
            (cat, cmd)
            for cat in ["GAM", "AD", "PowerShell"]
            for cmd in self.commands.get(cat, [])
            if cmd.get("copied_at")
        ]
        recent.sort(key=lambda x: x[1].get("copied_at", ""), reverse=True)
        recent = recent[:20]
        win = tk.Toplevel(self.root)
        win.title("⌚ Recently Copied")
        win.geometry("820x400")
        win.configure(bg=C["bg"])
        win.grab_set()
        tk.Frame(win, bg=C["primary"], height=2).pack(fill=tk.X)
        hdr = tk.Frame(win, bg=C["bg"])
        hdr.pack(fill=tk.X, padx=18, pady=(12, 4))
        tk.Label(hdr, text="⌚ Recently Copied", font=("Segoe UI", 12, "bold"),
                 fg=C["text"], bg=C["bg"]).pack(side=tk.LEFT)
        tk.Label(hdr, text="double-click or ↗ Go to navigate",
                 font=("Segoe UI", 9), fg=C["muted"],
                 bg=C["bg"]).pack(side=tk.LEFT, padx=(12, 0))
        wrap = tk.Frame(win, bg=C["surface2"],
                        highlightbackground=C["border"], highlightthickness=1)
        wrap.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 8))
        lb = tk.Listbox(wrap, font=("Segoe UI", 10),
                        bg=C["surface2"], fg=C["text"],
                        selectbackground=C["primary"], selectforeground="#FFFFFF",
                        relief="flat", borderwidth=0, activestyle="none",
                        cursor="hand2")
        sb = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        if recent:
            for cat, cmd in recent:
                ts = cmd.get("copied_at", "")[:16].replace("T", "  ")
                lb.insert(tk.END, f"  {ts}   [{cat}]  {cmd['description']}")
        else:
            lb.insert(tk.END, "  — nothing copied yet — use the ⎘ Copy button")
        def _navigate(event=None):
            sel = lb.curselection()
            if not sel or not recent or sel[0] >= len(recent):
                return
            cat, cmd = recent[sel[0]]
            desc = cmd["description"]
            win.destroy()
            tab_map = {"GAM": 0, "AD": 1, "PowerShell": 2}
            if cat in tab_map:
                self.notebook.select(tab_map[cat])
            frame = self._frame_for(cat)
            if frame:
                frame.description_combobox.set(desc)
                self.update_command_display(None, cat, frame)
        lb.bind("<Double-Button-1>", _navigate)
        lb.bind("<Return>", _navigate)
        btn_row = tk.Frame(win, bg=C["bg"])
        btn_row.pack(pady=(0, 14))
        ttk.Button(btn_row, text="↗ Go to Selected",
                   command=_navigate, style="P.TButton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_row, text="Close",
                   command=win.destroy, style="Gh.TButton").pack(side=tk.LEFT)

    def _show_list_window(self, title, items):
        C = self.C
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("780x380")
        win.configure(bg=C["bg"])
        win.grab_set()
        tk.Frame(win, bg=C["primary"], height=2).pack(fill=tk.X)
        tk.Label(win, text=title, font=("Segoe UI", 12, "bold"),
                 fg=C["text"], bg=C["bg"]).pack(padx=18, pady=(14, 8), anchor=tk.W)
        wrap = tk.Frame(win, bg=C["surface2"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 10))
        lb = tk.Listbox(wrap, font=("Consolas", 10),
                        bg=C["surface2"], fg=C["text"],
                        selectbackground=C["primary"],
                        relief="flat", borderwidth=0, activestyle="none")
        sb = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        for item in (items or ["  — none yet —"]):
            lb.insert(tk.END, "  " + item)
        ttk.Button(win, text="Close", command=win.destroy,
                   style="Gh.TButton").pack(pady=(0, 14))

    # =========================================================================
    # COMMAND CRUD
    # =========================================================================
    def add_command(self, category, command, description=""):
        if not command.strip():
            messagebox.showerror("Error", "Command cannot be empty.")
            return
        if not description.strip():
            messagebox.showerror("Error", "Description cannot be empty.")
            return
        if category not in self.commands:
            self.commands[category] = []
        for cmd in self.commands[category]:
            if cmd["command"] == command and cmd["description"] == description:
                messagebox.showerror("Error", "Duplicate command.")
                return
        self.commands[category].append({
            "command":     command,
            "description": description,
            "category":    category,
            "favorite":    False,
            "last_used":   None,
            "use_count":   0,
        })
        self.save_commands()
        self.update_description_options(category)
        self._update_tab_titles()
        self.set_status(f"✔ Added to {category}.")

    def remove_command(self, category, frame):
        sel = frame.description_combobox.get()
        if not sel:
            self.set_status("No command selected.")
            return
        if not messagebox.askyesno("Confirm", f"Remove  '{sel}'  from {category}?"):
            return
        for i, cmd in enumerate(self.commands.get(category, [])):
            if cmd["description"] == sel:
                del self.commands[category][i]
                self.save_commands()
                self.update_description_options(category)
                self._update_tab_titles()
                self._clear_output(frame.text_area)
                self.set_status(f"⌫ Removed '{sel}'.")
                return

    def update_command_display(self, event, category, frame):
        if category not in self.commands:
            return
        sel = frame.description_combobox.get()
        template = next((c["command"] for c in self.commands[category]
                         if c["description"] == sel), None)
        if not template:
            return

        for cmd in self.commands[category]:
            if cmd["description"] == sel:
                cmd["last_used"] = datetime.now().isoformat()
                cmd["use_count"] = cmd.get("use_count", 0) + 1
                cmd.setdefault("category", category)
                break
        self.save_commands()
        self._update_fav_icon(category, frame)

        for w in frame.input_frame.winfo_children():
            w.destroy()
        frame.input_widgets = {}

        placeholders = re.findall(r"<([^>]+)>", template)
        C = self.C
        for ph in placeholders:
            row = tk.Frame(frame.input_frame, bg=C["surface"])
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=f"‹{ph}›",
                     font=("Segoe UI", 9), fg=C["muted"],
                     bg=C["surface"], width=18, anchor=tk.W).pack(side=tk.LEFT)
            entry = tk.Entry(row, bg=C["surface2"], fg=C["text"],
                             insertbackground=C["primary"], relief="flat",
                             font=("Consolas", 10),
                             highlightthickness=1,
                             highlightbackground=C["border"],
                             highlightcolor=C["primary"])
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entry.bind("<KeyRelease>",
                       lambda e, cat=category, fr=frame: self.display_constructed_command(cat, fr))
            frame.input_widgets[ph] = entry

        self.display_constructed_command(category, frame)

    def display_constructed_command(self, category, frame):
        if category not in self.commands:
            return
        sel = frame.description_combobox.get()
        template = next((c["command"] for c in self.commands[category]
                         if c["description"] == sel), None)
        if not template:
            return
        result = template
        for ph, widget in frame.input_widgets.items():
            val = widget.get() or f"<{ph}>"
            result = result.replace(f"<{ph}>", val)
        frame.text_area.config(state=tk.NORMAL)
        frame.text_area.delete("1.0", tk.END)
        frame.text_area.insert(tk.END, result)
        frame.text_area.config(state=tk.DISABLED)

    def update_description_options(self, category):
        frame = self._frame_for(category)
        if not frame:
            return
        descs = [""] + [c["description"] for c in self.commands.get(category, [])
                        if c["description"]]
        frame.description_combobox["values"] = descs
        frame.description_combobox.current(0)

    # =========================================================================
    # COPY / EXECUTE / CLEAR
    # =========================================================================
    def copy_command(self, text, category=None, frame=None):
        if not text.strip():
            self.set_status("Nothing to copy.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text.strip())
        if category and frame:
            sel = frame.description_combobox.get()
            for cmd in self.commands.get(category, []):
                if cmd["description"] == sel:
                    cmd["copied_at"] = datetime.now().isoformat()
                    cmd.setdefault("category", category)
                    self.save_commands()
                    break
        self.set_status("⎘ Copied to clipboard.")

    def execute_command(self, category, command, frame):
        if not command.strip():
            self.set_status("Nothing to execute.")
            return
        self.copy_command(command, category, frame)
        if category in ("PowerShell", "AD"):
            self._run_powershell(command, frame)
        elif category == "GAM":
            webbrowser.open("https://shell.cloud.google.com/")
            self._append_output(frame.text_area,
                                "↗ Google Cloud Shell opened — command is on your clipboard.")
            self.set_status("↗ Cloud Shell opened.")

    def _run_powershell(self, command, frame):
        self._append_output(frame.text_area,
                            f"▶ Running…\n{command}\n{'─' * 56}\n")
        try:
            proc = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = proc.communicate(timeout=60)
            stdout = out.decode("utf-8", errors="replace").strip()
            stderr = err.decode("utf-8", errors="replace").strip()
            if proc.returncode == 0:
                self._append_output(frame.text_area, stdout or "✔ Completed.")
                self.set_status("✔ Executed successfully.")
            else:
                self._append_output(frame.text_area,
                                    f"✖ Exit {proc.returncode}\n{stderr or stdout}")
                self.set_status(f"✖ Error (exit {proc.returncode}).")
        except subprocess.TimeoutExpired:
            self._append_output(frame.text_area, "✖ Timed out after 60 s.")
            self.set_status("✖ Command timed out.")
        except Exception as exc:
            self._append_output(frame.text_area, f"✖ {exc}")
            self.set_status(f"✖ {exc}")

    def _append_output(self, text_area, text):
        text_area.config(state=tk.NORMAL)
        text_area.insert(tk.END, text + "\n")
        text_area.see(tk.END)
        text_area.config(state=tk.DISABLED)

    def _clear_output(self, text_area):
        text_area.config(state=tk.NORMAL)
        text_area.delete("1.0", tk.END)
        text_area.config(state=tk.DISABLED)

    # =========================================================================
    # PERSISTENCE
    # =========================================================================
    def _get_data_file_path(self, filename):
        if getattr(sys, "frozen", False):
            # EXE directory — writable, persists between runs
            exe_dir = os.path.dirname(sys.executable)
            dest = os.path.join(exe_dir, filename)
            # First run: extract bundled file from the PyInstaller temp dir
            if not os.path.exists(dest):
                import shutil
                src = os.path.join(sys._MEIPASS, filename)
                if os.path.exists(src):
                    shutil.copy2(src, dest)
            return dest
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

    def load_all_commands(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.commands = json.load(f)
                self._remove_duplicates()
                self.set_status("✔ Commands loaded.")
            else:
                self.commands = {"GAM": [], "AD": [], "PowerShell": []}
                self.set_status("No data file — starting fresh.")
        except Exception as exc:
            self.commands = {"GAM": [], "AD": [], "PowerShell": []}
            self.set_status(f"✖ Load error: {exc}")

        for cat, _ in self._category_frames():
            self.update_description_options(cat)
        self._update_tab_titles()
        self._update_count_label()

    def save_commands(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.commands, f, indent=4, ensure_ascii=False)
        except Exception as exc:
            messagebox.showerror("Save Error", str(exc))

    def _remove_duplicates(self):
        for cat in self.commands:
            seen, unique = set(), []
            for cmd in self.commands[cat]:
                key = (cmd.get("command", ""), cmd.get("description", ""))
                if key not in seen:
                    seen.add(key)
                    unique.append(cmd)
            self.commands[cat] = unique
        self.save_commands()

    # =========================================================================
    # HELPERS
    # =========================================================================
    def _frame_for(self, category):
        return {"GAM":        self.gam_frame,
                "AD":         self.ad_frame,
                "PowerShell": self.powershell_frame}.get(category)

    def _update_tab_titles(self):
        labels = [
            f"  ◈ GAM ({len(self.commands.get('GAM', []))})  ",
            f"  ⊞ AD ({len(self.commands.get('AD', []))})  ",
            f"  ⌨ PS ({len(self.commands.get('PowerShell', []))})  ",
        ]
        for i, text in enumerate(labels):
            self.notebook.tab(i, text=text)

    def _update_count_label(self):
        total = sum(len(v) for v in self.commands.values())
        self._count_label.config(text=f"{total} total")

    def set_status(self, text, duration_ms=4000):
        self.status_bar.config(text=text)
        if self._status_job:
            self.root.after_cancel(self._status_job)
        self._status_job = self.root.after(
            duration_ms, lambda: self.status_bar.config(text="● Ready"))

    # legacy alias
    def set_status_text(self, text):
        self.set_status(text)

    def _toggle_theme(self):
        self._is_dark = not self._is_dark
        self.C = dict(self.DARK if self._is_dark else self.LIGHT)
        self._rebuild_ui()
        mode = "Dark" if self._is_dark else "Light"
        self.set_status(f"{'☽' if self._is_dark else '☀'} Switched to {mode} mode.")

    def _rebuild_ui(self):
        if self._status_job:
            self.root.after_cancel(self._status_job)
            self._status_job = None
        try:
            saved_tab = self.notebook.index(self.notebook.select())
        except Exception:
            saved_tab = 0
        for w in self.root.winfo_children():
            w.destroy()
        self._add_visible = {}
        self.root.configure(bg=self.C["bg"])
        self._configure_style()
        self._create_menu()
        self._create_widgets()
        for cat, _ in self._category_frames():
            self.update_description_options(cat)
        self._update_tab_titles()
        self._update_count_label()
        try:
            self.notebook.select(saved_tab)
        except Exception:
            pass

    def _show_about(self):
        C = self.C
        win = tk.Toplevel(self.root)
        win.title("About")
        win.geometry("340x190")
        win.resizable(False, False)
        win.configure(bg=C["surface"])
        win.grab_set()
        tk.Frame(win, bg=C["primary"], height=3).pack(fill=tk.X)
        tk.Label(win, text="GAM Command Bank",
                 font=("Segoe UI", 13, "bold"),
                 fg=C["text"], bg=C["surface"]).pack(pady=(18, 2))
        tk.Label(win, text="v3.1",
                 font=("Segoe UI", 9), fg=C["muted"], bg=C["surface"]).pack()
        tk.Label(win, text="Author:   Jeff Burns\nContact:  JeffBurns@JFLX.CLOUD",
                 font=("Segoe UI", 9), fg=C["accent"], bg=C["surface"],
                 justify=tk.LEFT).pack(pady=(10, 0))
        ttk.Button(win, text="Close", command=win.destroy,
                   style="Gh.TButton").pack(pady=16)


# ─────────────────────────────────────────────────────────────────────────────
def main():
    root = tk.Tk()
    app = CommandManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
