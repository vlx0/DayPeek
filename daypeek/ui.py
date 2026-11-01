"""Окно DayPeek."""

from __future__ import annotations

import ctypes
import queue
import threading
import tkinter as tk
from datetime import datetime

from . import __version__
from .instance import WINDOW_TITLE
from .log import LogError, fetch_events
from .today import Day, build_day, format_day, from_rows

BG = "#111111"
FG = "#ffffff"
MUTED = "#999999"
CARD = "#1c1c1c"
ACCENT = "#93c5fd"
OK = "#86efac"


class DayPeekApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry("645x520")
        self.minsize(480, 420)
        self.configure(bg=BG)
        self._q: queue.Queue = queue.Queue()
        self._gen = 0
        self._day: Day | None = None

        pad = tk.Frame(self, bg=BG)
        pad.pack(fill="both", expand=True, padx=16, pady=14)

        foot = tk.Frame(pad, bg=BG)
        foot.pack(fill="x", side="bottom", pady=(8, 0))
        tk.Label(foot, text="неделя 10 · день 70", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        tk.Label(foot, text=f"v{__version__} · darkshade", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="right")

        head = tk.Frame(pad, bg=BG)
        head.pack(fill="x")
        tk.Label(head, text="DayPeek", bg=BG, fg=FG, font=("Segoe UI Semibold", 20)).pack(side="left")
        self._reload = tk.Button(
            head,
            text="Обновить",
            command=self._load,
            bg=ACCENT,
            fg=BG,
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Segoe UI Semibold", 9),
            activebackground=ACCENT,
            activeforeground=BG,
            padx=6,
            pady=1,
        )
        self._reload.pack(side="right", pady=6)
        self._note = tk.Label(
            pad, text="Следы за сегодня",
            bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w",
        )
        self._note.pack(fill="x", pady=(3, 12))

        self._card = tk.Frame(pad, bg=CARD)
        self._card.pack(fill="both", expand=True)
        stripe = tk.Frame(self._card, bg=OK, width=6)
        stripe.pack(side="left", fill="y")
        stripe.pack_propagate(False)
        inner = tk.Frame(self._card, bg=CARD)
        inner.pack(side="left", fill="both", expand=True, padx=16, pady=14)
        self._title = tk.Label(
            inner, text="сегодня", bg=CARD, fg=FG,
            font=("Segoe UI Semibold", 18),
        )
        self._title.pack(anchor="w")
        self._facts = tk.Frame(inner, bg=CARD)
        self._facts.pack(fill="both", expand=True, pady=(12, 0))

        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(20, self._place)
        self.after(80, self._poll)
        self.after(60, self._load)

    def _place(self) -> None:
        width, height = 645, 520
        sw = ctypes.windll.user32.GetSystemMetrics(0)
        sh = ctypes.windll.user32.GetSystemMetrics(1)
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 8)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _alive(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except tk.TclError:
            return False

    def _close(self) -> None:
        self.destroy()

    def _load(self) -> None:
        self._gen += 1
        gen = self._gen
        self._reload.configure(text="Читаю…", state="disabled")
        self._note.configure(text="читаю журналы…", fg=MUTED)
        threading.Thread(target=self._work, args=(gen,), daemon=True).start()

    def _work(self, gen: int) -> None:
        try:
            rows = fetch_events()
            now = datetime.now().astimezone()
            day = build_day(from_rows(rows, now), now)
            self._q.put(("ok", gen, day))
        except LogError as exc:
            self._q.put(("err", gen, str(exc)))
        except Exception as exc:
            self._q.put(("err", gen, str(exc)))

    def _fact_rows(self, item: Day) -> list[tuple[str, str]]:
        return [
            ("Запусков Windows", str(item.boots)),
            ("Пробуждений", str(item.wakes)),
            ("Падений", str(item.crashes)),
            ("USB", str(item.plugs)),
            ("MSI", str(item.softs)),
        ]

    def _show(self, item: Day | None) -> None:
        for child in self._facts.winfo_children():
            child.destroy()
        if item is None:
            self._title.configure(text="сегодня")
            return
        self._title.configure(text=format_day(item.when))
        rows = self._fact_rows(item)
        width = max(240, self.winfo_width() - 80)
        col_w = max(180, width // 2 - 12)
        for index, (caption, value) in enumerate(rows):
            cell = tk.Frame(self._facts, bg=CARD)
            cell.grid(row=index // 2, column=index % 2, sticky="nsew", padx=(0, 12), pady=(0, 10))
            tk.Label(cell, text=caption, bg=CARD, fg=MUTED, font=("Segoe UI", 9), anchor="w").pack(fill="x")
            tk.Label(
                cell, text=value, bg=CARD, fg=FG, font=("Segoe UI Semibold", 22),
                wraplength=col_w, justify="left", anchor="w",
            ).pack(fill="x")

    def _on_msg(self, msg) -> None:
        kind = msg[0]
        gen = msg[1]
        if gen != self._gen:
            return
        self._reload.configure(text="Обновить", state="normal")
        if kind == "ok":
            self._day = msg[2]
            self._note.configure(text="Следы за сегодня. Другие программы серии не нужны.", fg=MUTED)
            self._show(self._day)
            return
        self._day = None
        self._note.configure(text=str(msg[2]), fg="#fca5a5")
        self._show(None)

    def _poll(self) -> None:
        if not self._alive():
            return
        try:
            while True:
                self._on_msg(self._q.get_nowait())
        except queue.Empty:
            pass
        except tk.TclError:
            return
        if self._alive():
            self.after(80, self._poll)


def run() -> None:
    DayPeekApp().mainloop()
