import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import pyautogui, time, random, json, threading, os, sys, winsound
from datetime import datetime
from collections import defaultdict

try:
    import keyboard, pygetwindow as gw
except ImportError:
    print("pip install keyboard pygetwindow pyautogui")
    input("Enter...")
    sys.exit(1)

TRAY = False
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY = True
except Exception:
    pass

CFG = "config.json"
VER = "1.0.0"

try:
    from updater import CURRENT_VERSION, check_for_update, download_update, apply_update_and_restart
    VER = CURRENT_VERSION
except ImportError:
    def check_for_update(*a, **k):
        return None
    def download_update(*a, **k):
        pass
    def apply_update_and_restart(*a, **k):
        return False, "brak updatera"

# Colors
BG     = "#0d0d14"
BG2    = "#14141f"
CARD   = "#1c1c2e"
SURF   = "#2b2b40"
SURF2  = "#3a3a55"
TEXT   = "#e8e8f0"
TEXT2  = "#9a9ab8"
MUTED  = "#6a6a88"
BLUE   = "#7aa2f7"
GREEN  = "#9ece6a"
RED    = "#f7768e"
TEAL   = "#7dcfff"
MAUVE  = "#bb9af7"
ORANGE = "#ff9e64"


class Btn(tk.Canvas):
    def __init__(self, parent, text, command=None, width=120, height=32,
                 bg=BLUE, fg="#0d0d14", font=("Segoe UI", 9, "bold"), radius=8):
        super().__init__(parent, width=width, height=height,
                         bg=parent.cget("bg"), highlightthickness=0)
        self.command = command
        self.bg_color = bg
        self.fg_color = fg
        self.hover_color = self._lighten(bg)
        self.press_color = self._darken(bg)
        self.radius = radius
        self.font = font
        self.text = text
        self.w = width
        self.h = height
        self.enabled = True
        self.hovered = False
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", self._click)
        self._paint(self.bg_color)

    def _lighten(self, hex_color):
        hex_color = hex_color.lstrip("#")
        r, g, b = [min(255, int(int(hex_color[i:i+2], 16) * 1.18)) for i in (0, 2, 4)]
        return f"#{r:02x}{g:02x}{b:02x}"

    def _darken(self, hex_color):
        hex_color = hex_color.lstrip("#")
        r, g, b = [int(int(hex_color[i:i+2], 16) * 0.7) for i in (0, 2, 4)]
        return f"#{r:02x}{g:02x}{b:02x}"

    def _paint(self, color):
        self.delete("all")
        r, w, h = self.radius, self.w, self.h
        self.create_oval(0, 0, r*2, r*2, fill=color, outline="")
        self.create_oval(w - r*2, 0, w, r*2, fill=color, outline="")
        self.create_oval(0, h - r*2, r*2, h, fill=color, outline="")
        self.create_oval(w - r*2, h - r*2, w, h, fill=color, outline="")
        self.create_rectangle(r, 0, w - r, h, fill=color, outline="")
        self.create_rectangle(0, r, w, h - r, fill=color, outline="")
        self.create_text(w // 2, h // 2, text=self.text, fill=self.fg_color, font=self.font)

    def _enter(self, _):
        if self.enabled:
            self.hovered = True
            self._paint(self.hover_color)
            self.config(cursor="hand2")

    def _leave(self, _):
        self.hovered = False
        if self.enabled:
            self._paint(self.bg_color)

    def _click(self, _):
        if self.enabled and self.command:
            self._paint(self.press_color)
            self.after(80, lambda: self._paint(self.hover_color if self.hovered else self.bg_color))
            self.command()

    def set_enabled(self, state):
        self.enabled = state
        self._paint(self.bg_color if state else self._darken(self.bg_color))


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Discord AFK Panel  •  v{VER}")
        self.root.geometry("1000x860")
        self.root.minsize(900, 700)
        self.root.resizable(True, True)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.running = False
        self.thread = None
        self.commands = {}
        self.next_due = {}
        self.stats = defaultdict(int)
        self.session_start = None
        self.total_sent = 0
        self.last_activity = time.time()
        self.tray_icon = None
        self.pulse = 0
        self.profiles = {"Domyślny": {}}
        self.current_profile = "Domyślny"

        self.var_focus = tk.BooleanVar(value=False)
        self.var_sound = tk.BooleanVar(value=True)
        self.var_random = tk.BooleanVar(value=False)
        self.var_log = tk.BooleanVar(value=False)
        self.var_schedule = tk.BooleanVar(value=False)

        self._build()
        self.load_config()
        self._setup_hotkey()
        self._track_activity()
        self._tick()
        if TRAY:
            self._setup_tray()
        self.root.after(1500, self._auto_check_update)

    def _build(self):
        # ===== TOP BAR =====
        top = tk.Frame(self.root, bg=BG2, height=48)
        top.pack(fill="x")
        top.pack_propagate(False)

        # gradient strip
        grad = tk.Canvas(top, height=3, bg=BG2, highlightthickness=0)
        grad.pack(fill="x", side="top")
        colors = [BLUE, TEAL, MAUVE, ORANGE, GREEN]
        for i, col in enumerate(colors):
            grad.create_rectangle(i * 196, 0, (i + 1) * 196 + 2, 3, fill=col, outline="")

        inner_top = tk.Frame(top, bg=BG2)
        inner_top.pack(fill="both", expand=True)

        tk.Label(inner_top, text="⚡  Discord AFK Panel", bg=BG2, fg=BLUE,
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=16, pady=6)
        tk.Label(inner_top, text=f"v{VER}", bg=BG2, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="left")

        self.status_label = tk.Label(inner_top, text="●  ZATRZYMANY", bg=BG2, fg=RED,
                                     font=("Segoe UI", 10, "bold"))
        self.status_label.pack(side="right", padx=16)

        # ===== MAIN 3 COLUMNS =====
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=12, pady=10)

        # ---------- LEFT ----------
        left = tk.Frame(main, bg=CARD, width=350)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(left, text="KOMENDY", bg=CARD, fg=TEXT2,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(12, 6))

        # Profile row
        prof_row = tk.Frame(left, bg=CARD)
        prof_row.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(prof_row, text="Profil:", bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(side="left")
        self.profile_var = tk.StringVar(value="Domyślny")
        self.profile_combo = ttk.Combobox(prof_row, textvariable=self.profile_var,
                                          width=14, state="readonly")
        self.profile_combo["values"] = ["Domyślny"]
        self.profile_combo.pack(side="left", padx=6)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_change)
        Btn(prof_row, "+", command=self._new_profile, width=28, height=24,
            bg=SURF2, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(side="left")

        # Tree
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.Treeview",
                        background=SURF, foreground=TEXT, fieldbackground=SURF,
                        rowheight=26, borderwidth=0, font=("Segoe UI", 9))
        style.configure("Dark.Treeview.Heading",
                        background=SURF2, foreground=TEXT,
                        font=("Segoe UI", 8, "bold"), borderwidth=0)
        style.map("Dark.Treeview",
                  background=[("selected", BLUE)],
                  foreground=[("selected", BG)])

        tree_frame = tk.Frame(left, bg=CARD)
        tree_frame.pack(fill="both", expand=True, padx=10)
        self.tree = ttk.Treeview(tree_frame, columns=("cmd", "int", "next", "act"),
                                 show="headings", height=6, style="Dark.Treeview")
        self.tree.heading("cmd", text="Komenda")
        self.tree.heading("int", text="Interwał")
        self.tree.heading("next", text="Następna")
        self.tree.heading("act", text="Akcje")
        self.tree.column("cmd", width=110)
        self.tree.column("int", width=70, anchor="center")
        self.tree.column("next", width=70, anchor="center")
        self.tree.column("act", width=55, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self._edit_actions())

        # Separator
        tk.Frame(left, bg=SURF2, height=1).pack(fill="x", padx=12, pady=10)

        # Form
        form = tk.Frame(left, bg=CARD)
        form.pack(fill="x", padx=12)

        tk.Label(form, text="Komenda", bg=CARD, fg=MUTED, font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w", columnspan=3)
        self.cmd_entry = self._entry(form, 28)
        self.cmd_entry.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(2, 8))

        tk.Label(form, text="Minuty", bg=CARD, fg=MUTED, font=("Segoe UI", 8)).grid(row=2, column=0, sticky="w")
        tk.Label(form, text="Sekundy", bg=CARD, fg=MUTED, font=("Segoe UI", 8)).grid(row=2, column=1, sticky="w", padx=(8, 0))
        tk.Label(form, text="Jitter ±s", bg=CARD, fg=MUTED, font=("Segoe UI", 8)).grid(row=2, column=2, sticky="w", padx=(8, 0))

        self.min_entry = self._entry(form, 6)
        self.min_entry.grid(row=3, column=0, sticky="w", pady=(2, 0))
        self.min_entry.insert(0, "1")

        self.sec_entry = self._entry(form, 6)
        self.sec_entry.grid(row=3, column=1, sticky="w", padx=(8, 0), pady=(2, 0))
        self.sec_entry.insert(0, "5")

        self.jit_entry = self._entry(form, 6)
        self.jit_entry.grid(row=3, column=2, sticky="w", padx=(8, 0), pady=(2, 0))
        self.jit_entry.insert(0, "3")

        # Buttons under form — clearly separated
        btn_row = tk.Frame(left, bg=CARD)
        btn_row.pack(fill="x", padx=12, pady=(14, 8))

        Btn(btn_row, "＋  Dodaj", command=self.add_command, width=100, height=34, bg=BLUE).pack(side="left", padx=(0, 6))
        Btn(btn_row, "✕  Usuń", command=self.remove_command, width=90, height=34, bg=RED).pack(side="left", padx=(0, 6))
        Btn(btn_row, "⚡ Akcje", command=self._edit_actions, width=90, height=34, bg=MAUVE).pack(side="left")

        # ---------- MIDDLE ----------
        mid = tk.Frame(main, bg=CARD, width=300)
        mid.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(mid, text="USTAWIENIA", bg=CARD, fg=TEXT2,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(12, 8))

        opts = tk.Frame(mid, bg=CARD)
        opts.pack(fill="x", padx=14)
        self._check(opts, "Auto-fokusuj Discord", self.var_focus)
        self._check(opts, "Dźwięki", self.var_sound)
        self._check(opts, "Losowa kolejność komend", self.var_random)
        self._check(opts, "Zapisuj log do pliku", self.var_log)

        tk.Frame(mid, bg=SURF2, height=1).pack(fill="x", padx=14, pady=10)

        self._check(mid, "Harmonogram (tylko w godzinach)", self.var_schedule)

        sched = tk.Frame(mid, bg=CARD)
        sched.pack(fill="x", padx=14, pady=(4, 0))
        tk.Label(sched, text="Od:", bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(side="left")
        self.sched_from = self._entry(sched, 6)
        self.sched_from.pack(side="left", padx=4)
        self.sched_from.insert(0, "08:00")
        tk.Label(sched, text="Do:", bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(side="left", padx=(10, 0))
        self.sched_to = self._entry(sched, 6)
        self.sched_to.pack(side="left", padx=4)
        self.sched_to.insert(0, "23:00")

        tk.Frame(mid, bg=SURF2, height=1).pack(fill="x", padx=14, pady=10)

        fields = tk.Frame(mid, bg=CARD)
        fields.pack(fill="x", padx=14)
        self.start_delay = self._labeled_entry(fields, "Czas na przełączenie (s)", "5")
        self.global_jitter = self._labeled_entry(fields, "Globalne losowe ± s", "2")

        # Spacer to push buttons down a bit but keep them visible
        tk.Frame(mid, bg=CARD, height=20).pack()

        # START / STOP — big and clear
        ctrl = tk.Frame(mid, bg=CARD)
        ctrl.pack(fill="x", padx=14, pady=(0, 12))

        self.btn_start = Btn(ctrl, "▶    START    (F6)", command=self.toggle,
                             width=270, height=42, bg=GREEN, font=("Segoe UI", 11, "bold"))
        self.btn_start.pack(pady=(0, 8))

        self.btn_stop = Btn(ctrl, "⏹    STOP", command=self.stop,
                            width=270, height=36, bg=RED)
        self.btn_stop.pack()
        self.btn_stop.set_enabled(False)

        # ---------- RIGHT ----------
        right = tk.Frame(main, bg=CARD, width=270)
        right.pack(side="left", fill="both", expand=True)

        tk.Label(right, text="STATYSTYKI", bg=CARD, fg=TEXT2,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(12, 10))

        self.lbl_time = tk.Label(right, text="00:00:00", bg=CARD, fg=BLUE,
                                 font=("Consolas", 26, "bold"))
        self.lbl_time.pack()
        tk.Label(right, text="czas sesji", bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack()

        self.lbl_total = tk.Label(right, text="0", bg=CARD, fg=GREEN,
                                  font=("Consolas", 24, "bold"))
        self.lbl_total.pack(pady=(16, 0))
        tk.Label(right, text="wysłanych komend", bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack()

        tk.Frame(right, bg=SURF2, height=1).pack(fill="x", padx=14, pady=14)

        self.lbl_detail = tk.Label(right, text="Brak danych", bg=CARD, fg=TEXT2,
                                   font=("Consolas", 9), justify="left", anchor="nw")
        self.lbl_detail.pack(fill="both", expand=True, padx=16)

        # Save / Load
        save_row = tk.Frame(right, bg=CARD)
        save_row.pack(fill="x", padx=12, pady=(8, 6))
        Btn(save_row, "💾  Zapisz", command=self.save_config, width=115, height=32,
            bg=SURF2, fg=TEXT).pack(side="left", padx=(0, 6))
        Btn(save_row, "📂  Wczytaj", command=self.load_config, width=115, height=32,
            bg=SURF2, fg=TEXT).pack(side="left")

        upd_row = tk.Frame(right, bg=CARD)
        upd_row.pack(fill="x", padx=12, pady=(0, 6))
        Btn(upd_row, "🔄  Sprawdź aktualizacje", command=self._manual_check_update,
            width=240, height=30, bg=SURF2, fg=TEXT).pack()

        if TRAY:
            tray_row = tk.Frame(right, bg=CARD)
            tray_row.pack(fill="x", padx=12, pady=(0, 12))
            Btn(tray_row, "⬇  Minimalizuj do tray", command=self.hide_to_tray,
                width=240, height=30, bg=SURF2, fg=TEXT).pack()

        # ===== LOG =====
        log_card = tk.Frame(self.root, bg=CARD)
        log_card.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        tk.Label(log_card, text="LOG", bg=CARD, fg=TEXT2,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(8, 4))

        self.log = scrolledtext.ScrolledText(
            log_card, height=8, state="disabled",
            bg=SURF, fg=TEXT, font=("Consolas", 9),
            relief="flat", borderwidth=0, padx=8, pady=6
        )
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.log_msg(f"Discord AFK Panel v{VER} gotowy.")
        self.log_msg("F6 = Start/Stop  |  Dwuklik na komendę = edycja akcji")

    # ---------- helpers ----------
    def _entry(self, parent, width=10):
        return tk.Entry(parent, width=width, bg=SURF, fg=TEXT, insertbackground=BLUE,
                        relief="flat", font=("Segoe UI", 10), highlightthickness=1,
                        highlightbackground=SURF2, highlightcolor=BLUE)

    def _labeled_entry(self, parent, label, default):
        tk.Label(parent, text=label, bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(2, 0))
        e = self._entry(parent, 10)
        e.pack(anchor="w", pady=(2, 6))
        e.insert(0, default)
        return e

    def _check(self, parent, text, variable):
        tk.Checkbutton(parent, text=text, variable=variable, bg=CARD, fg=TEXT,
                       activebackground=CARD, activeforeground=TEXT,
                       selectcolor=SURF, font=("Segoe UI", 9),
                       highlightthickness=0, bd=0).pack(anchor="w", pady=2)

    # ---------- actions editor ----------
    def _edit_actions(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Akcje", "Zaznacz komendę na liście.")
            return
        cmd = self.tree.item(sel[0])["values"][0]
        if cmd not in self.commands:
            return
        data = self.commands[cmd]
        actions = list(data.get("actions", []))

        win = tk.Toplevel(self.root)
        win.title(f"Akcje → {cmd}")
        win.geometry("460x420")
        win.configure(bg=BG2)
        win.minsize(400, 350)
        win.resizable(True, True)
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text=f"Akcje po komendzie:  {cmd}", bg=BG2, fg=BLUE,
                 font=("Segoe UI", 12, "bold")).pack(pady=(14, 4))
        tk.Label(win, text="Po wysłaniu bot wykona te kroki po kolei:",
                 bg=BG2, fg=MUTED, font=("Segoe UI", 8)).pack()

        lb = tk.Listbox(win, bg=SURF, fg=TEXT, font=("Consolas", 10),
                        selectbackground=BLUE, relief="flat", height=9)
        lb.pack(fill="both", expand=True, padx=16, pady=10)
        for a in actions:
            lb.insert("end", f"czekaj {a['wait']}s   →   naciśnij [{a['key']}]")

        row = tk.Frame(win, bg=BG2)
        row.pack(fill="x", padx=16)
        tk.Label(row, text="Czekaj (s):", bg=BG2, fg=MUTED, font=("Segoe UI", 8)).pack(side="left")
        wait_e = self._entry(row, 6)
        wait_e.pack(side="left", padx=4)
        wait_e.insert(0, "1.5")
        tk.Label(row, text="Klawisz:", bg=BG2, fg=MUTED, font=("Segoe UI", 8)).pack(side="left", padx=(12, 0))
        key_e = self._entry(row, 6)
        key_e.pack(side="left", padx=4)
        key_e.insert(0, "1")

        def add_step():
            try:
                w = float(wait_e.get())
            except ValueError:
                messagebox.showwarning("Błąd", "Czas musi być liczbą!", parent=win)
                return
            k = key_e.get().strip()
            if not k:
                return
            actions.append({"wait": w, "key": k})
            lb.insert("end", f"czekaj {w}s   →   naciśnij [{k}]")

        def del_step():
            s = lb.curselection()
            if s:
                idx = s[0]
                lb.delete(idx)
                actions.pop(idx)

        def save_steps():
            data["actions"] = actions
            self.commands[cmd] = data
            self.refresh_tree()
            self.log_msg(f"Akcje dla {cmd}: {len(actions)} kroków")
            win.destroy()

        btns = tk.Frame(win, bg=BG2)
        btns.pack(fill="x", padx=16, pady=14)
        Btn(btns, "＋ Dodaj krok", command=add_step, width=120, height=32, bg=BLUE).pack(side="left", padx=(0, 6))
        Btn(btns, "✕ Usuń krok", command=del_step, width=110, height=32, bg=RED).pack(side="left", padx=(0, 6))
        Btn(btns, "✓ Zapisz", command=save_steps, width=100, height=32, bg=GREEN).pack(side="right")

    # ---------- profiles ----------
    def _new_profile(self):
        name = simpledialog.askstring("Nowy profil", "Nazwa profilu:", parent=self.root)
        if name and name not in self.profiles:
            self.profiles[name] = {}
            self.profile_combo["values"] = list(self.profiles.keys())
            self.profile_var.set(name)
            self.current_profile = name
            self.commands = {}
            self.refresh_tree()
            self.log_msg(f"Nowy profil: {name}")

    def _on_profile_change(self, _=None):
        self.profiles[self.current_profile] = dict(self.commands)
        self.current_profile = self.profile_var.get()
        self.commands = dict(self.profiles.get(self.current_profile, {}))
        self.refresh_tree()
        self.log_msg(f"Profil: {self.current_profile}")

    # ---------- tick ----------
    def _tick(self):
        if self.running:
            cols = [GREEN, TEAL, BLUE, MAUVE]
            self.status_label.config(fg=cols[self.pulse % 4])
            self.pulse += 1
            now = time.time()
            for item in self.tree.get_children():
                vals = list(self.tree.item(item)["values"])
                cmd = vals[0]
                if cmd in self.next_due:
                    rem = max(0, int(self.next_due[cmd] - now))
                    m, s = divmod(rem, 60)
                    vals[2] = f"{m:02d}:{s:02d}"
                else:
                    vals[2] = "—"
                self.tree.item(item, values=vals)

        if self.session_start and self.running:
            elapsed = int(time.time() - self.session_start)
            h, rem = divmod(elapsed, 3600)
            m, s = divmod(rem, 60)
            self.lbl_time.config(text=f"{h:02d}:{m:02d}:{s:02d}")
        else:
            self.lbl_time.config(text="00:00:00")

        self.lbl_total.config(text=str(self.total_sent))
        if self.stats:
            lines = [f"{c}: {n}x" for c, n in sorted(self.stats.items(), key=lambda x: -x[1])]
            self.lbl_detail.config(text="\n".join(lines))
        else:
            self.lbl_detail.config(text="Brak danych")

        self.root.after(500, self._tick)

    def log_msg(self, msg):
        def _log():
            line = f"[{datetime.now().strftime('%H:%M:%S')}]  {msg}"
            self.log.config(state="normal")
            self.log.insert("end", line + "\n")
            self.log.see("end")
            self.log.config(state="disabled")
            if self.var_log.get():
                try:
                    with open("afk_log.txt", "a", encoding="utf-8") as f:
                        f.write(line + "\n")
                except Exception:
                    pass
        self.root.after(0, _log)

    # ---------- core ----------
    def is_in_schedule(self):
        if not self.var_schedule.get():
            return True
        try:
            now = datetime.now().time()
            start = datetime.strptime(self.sched_from.get().strip(), "%H:%M").time()
            end = datetime.strptime(self.sched_to.get().strip(), "%H:%M").time()
            if start <= end:
                return start <= now <= end
            return now >= start or now <= end
        except Exception:
            return True

    def is_discord_active(self):
        try:
            win = gw.getActiveWindow()
            return win and win.title and "discord" in win.title.lower()
        except Exception:
            return False

    def focus_discord(self):
        try:
            windows = gw.getWindowsWithTitle("Discord")
            if not windows:
                windows = [w for w in gw.getAllWindows() if w.title and "discord" in w.title.lower()]
            if windows:
                w = windows[0]
                if w.isMinimized:
                    w.restore()
                w.activate()
                time.sleep(0.2)
                return True
        except Exception as e:
            self.log_msg(f"Fokus: {e}")
        return False

    def play_sound(self, start=True):
        if not self.var_sound.get():
            return
        try:
            if start:
                winsound.Beep(880, 90)
                winsound.Beep(1200, 120)
            else:
                winsound.Beep(700, 100)
                winsound.Beep(400, 140)
        except Exception:
            pass

    def add_command(self):
        cmd = self.cmd_entry.get().strip()
        if not cmd:
            messagebox.showwarning("Błąd", "Wpisz komendę!")
            return
        try:
            minutes = int(self.min_entry.get() or 0)
            seconds = int(self.sec_entry.get() or 0)
            jitter = float(self.jit_entry.get() or 0)
            total = minutes * 60 + seconds
            if total < 5:
                messagebox.showwarning("Błąd", "Minimalny interwał to 5 sekund!")
                return
        except ValueError:
            messagebox.showwarning("Błąd", "Minuty / sekundy / jitter muszą być liczbami!")
            return

        old = self.commands.get(cmd, {})
        self.commands[cmd] = {
            "interval": total,
            "jitter": jitter,
            "actions": old.get("actions", [])
        }
        self.refresh_tree()
        self.cmd_entry.delete(0, "end")
        self.log_msg(f"Dodano: {cmd} → {minutes}m {seconds}s (±{jitter}s)")

    def remove_command(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Zaznacz komendę do usunięcia.")
            return
        cmd = self.tree.item(sel[0])["values"][0]
        if cmd in self.commands:
            del self.commands[cmd]
            self.refresh_tree()
            self.log_msg(f"Usunięto: {cmd}")

    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for cmd, data in self.commands.items():
            m, s = divmod(data["interval"], 60)
            n_act = len(data.get("actions", []))
            self.tree.insert("", "end", values=(
                cmd, f"{m}m {s}s", "—", f"{n_act}k" if n_act else "—"
            ))

    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        if not self.commands:
            messagebox.showwarning("Błąd", "Dodaj przynajmniej jedną komendę!")
            return
        try:
            delay = int(self.start_delay.get())
        except ValueError:
            messagebox.showwarning("Błąd", "Czas na przełączenie musi być liczbą!")
            return

        self.running = True
        self.session_start = time.time()
        self.stats.clear()
        self.total_sent = 0
        self.btn_start.set_enabled(False)
        self.btn_stop.set_enabled(True)
        self.status_label.config(text="●  DZIAŁA", fg=GREEN)
        self.play_sound(True)
        self.log_msg(f"Start za {delay}s — kliknij w pole wiadomości Discord!")

        if self.tray_icon:
            try:
                self.tray_icon.icon = self._tray_image()
            except Exception:
                pass

        self.thread = threading.Thread(target=self._run_loop, args=(delay,), daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.btn_start.set_enabled(True)
        self.btn_stop.set_enabled(False)
        self.status_label.config(text="●  ZATRZYMANY", fg=RED)
        self.play_sound(False)
        self.log_msg("Zatrzymano.")
        if self.tray_icon:
            try:
                self.tray_icon.icon = self._tray_image()
            except Exception:
                pass

    def _type_cmd(self, cmd):
        """Pisanie literka po literce co 0.5 s."""
        for ch in cmd:
            pyautogui.write(ch)
            time.sleep(0.5)

    def _run_loop(self, delay):
        time.sleep(delay)
        self.log_msg("Bot uruchomiony! Pierwsze komendy zaraz polecą.")
        now = time.time()
        # Pierwsza runda: komendy startują od razu (lekko rozłożone)
        self.next_due = {}
        for i, (cmd, data) in enumerate(self.commands.items()):
            self.next_due[cmd] = now + 0.5 + i * 1.2

        while self.running:
            if not self.is_in_schedule():
                self.log_msg("Poza harmonogramem – czekam...")
                time.sleep(3)
                continue

            now = time.time()
            items = list(self.commands.items())
            if self.var_random.get():
                random.shuffle(items)

            for cmd, data in items:
                if not self.running:
                    break
                if now >= self.next_due.get(cmd, 0):
                    if self.var_focus.get():
                        if not self.is_discord_active():
                            self.log_msg("Próbuję fokus Discord...")
                            self.focus_discord()
                            time.sleep(0.3)
                    try:
                        self.log_msg(f"Piszę → {cmd}")
                        self._type_cmd(cmd)
                        time.sleep(0.1)
                        pyautogui.press("enter")
                        self.log_msg(f"Wysłano → {cmd}")

                        for act in data.get("actions", []):
                            time.sleep(float(act["wait"]))
                            key = str(act["key"]).lower()
                            pyautogui.press("enter" if key in ("enter", "return") else key)
                            self.log_msg(f"  ↳ naciśnięto [{act['key']}]")

                        jitter = float(data.get("jitter", 0)) + float(self.global_jitter.get() or 0)
                        self.next_due[cmd] = time.time() + data["interval"] + random.uniform(-jitter, jitter)
                        self.stats[cmd] += 1
                        self.total_sent += 1
                        time.sleep(random.uniform(0.4, 1.0))
                    except Exception as e:
                        self.log_msg(f"Błąd przy {cmd}: {e}")

            time.sleep(0.4)

    # ---------- tray / hotkey / activity ----------
    def _tray_image(self):
        img = Image.new("RGB", (64, 64), (13, 13, 20))
        draw = ImageDraw.Draw(img)
        color = (158, 206, 106) if self.running else (247, 118, 142)
        draw.ellipse([10, 10, 54, 54], fill=color)
        return img

    def _setup_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("Pokaż", self.show_from_tray),
            pystray.MenuItem("Start / Stop", lambda: self.root.after(0, self.toggle)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Zamknij", self.quit_app)
        )
        self.tray_icon = pystray.Icon("DiscordAFK", self._tray_image(), "Discord AFK Panel", menu)

    def hide_to_tray(self):
        self.root.withdraw()
        if self.tray_icon and not getattr(self.tray_icon, "_running", False):
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_from_tray(self, *_):
        self.root.after(0, lambda: (self.root.deiconify(), self.root.lift(), self.root.focus_force()))

    def quit_app(self, *_):
        self.running = False
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.root.after(0, self.root.destroy)

    def on_close(self):
        if self.running:
            if messagebox.askyesno("Bot działa", "Bot jest uruchomiony.\nNa pewno zamknąć?"):
                self.quit_app()
        else:
            self.quit_app()

    def _setup_hotkey(self):
        try:
            keyboard.add_hotkey("f6", lambda: self.root.after(0, self.toggle))
        except Exception as e:
            self.log_msg(f"Hotkey F6: {e}")

    def _track_activity(self):
        def on_activity(_):
            self.last_activity = time.time()
        try:
            keyboard.hook(on_activity)
        except Exception:
            pass
        self.root.after(400, self._check_mouse)

    def _check_mouse(self):
        try:
            pos = pyautogui.position()
            if not hasattr(self, "_last_pos") or pos != self._last_pos:
                self.last_activity = time.time()
                self._last_pos = pos
        except Exception:
            pass
        self.root.after(400, self._check_mouse)


    # ---------- updates ----------
    def _auto_check_update(self):
        def worker():
            info = check_for_update()
            if info:
                self.root.after(0, lambda: self._prompt_update(info))
        threading.Thread(target=worker, daemon=True).start()

    def _manual_check_update(self):
        self.log_msg("Sprawdzam aktualizacje...")
        def worker():
            info = check_for_update()
            def done():
                if info:
                    self._prompt_update(info)
                else:
                    messagebox.showinfo("Aktualizacje", f"Masz najnowszą wersję ({VER}).")
                    self.log_msg("Brak nowszej wersji.")
            self.root.after(0, done)
        threading.Thread(target=worker, daemon=True).start()

    def _prompt_update(self, info):
        ver = info.get("version", "?")
        log = info.get("changelog", "")
        msg = f"Dostępna nowa wersja: {ver}\nTwoja: {VER}\n\n{log}\n\nZaktualizować teraz?"
        if messagebox.askyesno("Aktualizacja", msg):
            self._do_update(info)

    def _do_update(self, info):
        url = info.get("url")
        if not url:
            messagebox.showerror("Błąd", "Brak linku do aktualizacji w version.json")
            return
        self.log_msg("Pobieram aktualizację...")
        def worker():
            try:
                import tempfile
                dest = os.path.join(tempfile.gettempdir(), "DiscordAFKPanel_new.exe")
                download_update(url, dest)
                ok, msg = apply_update_and_restart(dest)
                def done():
                    self.log_msg(msg)
                    if ok:
                        self.quit_app()
                    else:
                        messagebox.showinfo("Aktualizacja", msg)
                self.root.after(0, done)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Błąd aktualizacji", str(e)))
        threading.Thread(target=worker, daemon=True).start()

    # ---------- config ----------
    def save_config(self):
        self.profiles[self.current_profile] = dict(self.commands)
        data = {
            "profiles": self.profiles,
            "current_profile": self.current_profile,
            "start_delay": self.start_delay.get(),
            "global_jitter": self.global_jitter.get(),
            "var_focus": self.var_focus.get(),
            "var_sound": self.var_sound.get(),
            "var_random": self.var_random.get(),
            "var_log": self.var_log.get(),
            "var_schedule": self.var_schedule.get(),
            "sched_from": self.sched_from.get(),
            "sched_to": self.sched_to.get()
        }
        try:
            with open(CFG, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.log_msg("Konfiguracja zapisana.")
        except Exception as e:
            self.log_msg(f"Błąd zapisu: {e}")

    def load_config(self):
        if not os.path.exists(CFG):
            self.commands = {
                ".low": {"interval": 65, "jitter": 3, "actions": []},
                ".zarabiaj": {"interval": 120, "jitter": 4, "actions": []},
                ".lemoniada": {"interval": 180, "jitter": 5, "actions": []},
                ".zlecenie": {"interval": 300, "jitter": 5, "actions": [{"wait": 1.5, "key": "1"}]}
            }
            self.profiles = {"Domyślny": dict(self.commands)}
            self.refresh_tree()
            return
        try:
            with open(CFG, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.profiles = data.get("profiles", {"Domyślny": {}})
            self.current_profile = data.get("current_profile", "Domyślny")
            self.profile_combo["values"] = list(self.profiles.keys())
            self.profile_var.set(self.current_profile)
            self.commands = dict(self.profiles.get(self.current_profile, {}))

            for cmd, val in list(self.commands.items()):
                if isinstance(val, (int, float)):
                    self.commands[cmd] = {"interval": int(val), "jitter": 3, "actions": []}

            for entry, key, default in [
                (self.start_delay, "start_delay", "5"),
                (self.global_jitter, "global_jitter", "2"),
                (self.sched_from, "sched_from", "08:00"),
                (self.sched_to, "sched_to", "23:00")
            ]:
                entry.delete(0, "end")
                entry.insert(0, str(data.get(key, default)))

            self.var_focus.set(data.get("var_focus", False))
            self.var_sound.set(data.get("var_sound", True))
            self.var_random.set(data.get("var_random", False))
            self.var_log.set(data.get("var_log", False))
            self.var_schedule.set(data.get("var_schedule", False))
            self.refresh_tree()
            self.log_msg("Konfiguracja wczytana.")
        except Exception as e:
            self.log_msg(f"Błąd wczytywania: {e}")


if __name__ == "__main__":
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.025
    root = tk.Tk()
    App(root)
    root.mainloop()
