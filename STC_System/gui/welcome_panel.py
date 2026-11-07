"""
gui/welcome_panel.py
────────────────────
Professional welcome screen shown when the application starts.

Features:
  • Animated gradient title
  • 8 task selection cards in a responsive grid
  • Hover effects with colour highlights
  • Single-click task selection → triggers on_task_selected callback
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from gui.styles import (
    BG_CARD, BG_CARD_HOVER, BG_DARK, FONT_ARABIC_BODY, FONT_ARABIC_SMALL,
    FONT_ARABIC_TITLE, FONT_BODY, FONT_SUBTITLE, FONT_TITLE, FONT_TITLE_LARGE,
    TASK_COLORS, TEXT_PRIMARY, TEXT_SECONDARY,
)

# ─── Task definitions ─────────────────────────────────────────────────────────

TASKS = [
    {
        "id":    1,
        "icon":  "❌",
        "en":    "System Errors",
        "ar":    "اخطاء النظام",
        "desc":  "كشف أخطاء البيانات وتحقق من صحة الحالات والوعود",
    },
    {
        "id":    2,
        "icon":  "📞",
        "en":    "Contact Status",
        "ar":    "التوصل وعدم التوصل",
        "desc":  "تحليل حالة التواصل مع العملاء وإنشاء تقارير المشرفين",
    },
    {
        "id":    3,
        "icon":  "😴",
        "en":    "Neglect Analysis",
        "ar":    "الاهمال",
        "desc":  "حساب أيام الإهمال وتصنيف المحصلين حسب المتابعة",
    },
    {
        "id":    4,
        "icon":  "💰",
        "en":    "Payments & Reconciliation",
        "ar":    "السدادات والتسوية",
        "desc":  "مقارنة سداد مهارة بسداد الشركة وتصنيف التسويات",
    },
    {
        "id":    5,
        "icon":  "📅",
        "en":    "Scheduling",
        "ar":    "الجدولة",
        "desc":  "جدولة وعود السداد وتوزيع العملاء على المحصلين",
    },
    {
        "id":    6,
        "icon":  "🔄",
        "en":    "Withdrawal & Rotation",
        "ar":    "السحب والتدوير",
        "desc":  "سحب جميع عملاء محصل وإعادة توزيعهم على محصلي المشرف بالتساوي",
    },
    {
        "id":    7,
        "icon":  "🎯",
        "en":    "Target Customers",
        "ar":    "العملاء المستهدفة والايجابية",
        "desc":  "تصنيف العملاء الإيجابيين وترتيب أولويات التحصيل",
    },
    {
        "id":    8,
        "icon":  "🌟",
        "en":    "Full Operations Report",
        "ar":    "تشغيل جميع المهام",
        "desc":  "تشغيل كامل لجميع المهام وإنشاء تقرير شامل",
        "wide":  True,
    },
]


class WelcomePanel(tk.Frame):
    """
    Welcome screen with task selection cards.
    Calls *on_task_selected(task_id)* when a card is clicked.
    """

    def __init__(self, parent: tk.Widget, on_task_selected: Callable[[int], None]):
        super().__init__(parent, bg=BG_DARK)
        self._callback = on_task_selected
        self._card_frames: dict[int, tk.Frame] = {}
        self._build()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        self.columnconfigure(0, weight=1)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG_DARK, pady=20)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(0, weight=1)

        tk.Label(
            hdr,
            text="🏢  Maharah Operations Automation System",
            font=FONT_TITLE_LARGE,
            bg=BG_DARK, fg="#1f6feb",
        ).grid(row=0, column=0)

        tk.Label(
            hdr,
            text="STC Operations  —  نظام أتمتة العمليات",
            font=FONT_ARABIC_BODY,
            bg=BG_DARK, fg=TEXT_SECONDARY,
        ).grid(row=1, column=0, pady=(4, 0))

        # Divider
        tk.Frame(self, height=1, bg="#30363d").grid(
            row=1, column=0, sticky="ew", padx=40
        )

        # ── Subtitle ──────────────────────────────────────────────────────────
        tk.Label(
            self,
            text="ما المهمة التي تريد تنفيذها اليوم؟",
            font=FONT_ARABIC_TITLE,
            bg=BG_DARK, fg=TEXT_PRIMARY,
            pady=16,
        ).grid(row=2, column=0)

        # ── Task grid ─────────────────────────────────────────────────────────
        grid_frame = tk.Frame(self, bg=BG_DARK)
        grid_frame.grid(row=3, column=0, padx=40, pady=(0, 30), sticky="nsew")

        # 4 columns for the first 7 tasks, task 8 spans full row
        for col_i in range(4):
            grid_frame.columnconfigure(col_i, weight=1, uniform="col")

        row_i = 0
        col_i = 0
        for task in TASKS:
            is_wide = task.get("wide", False)
            columnspan = 4 if is_wide else 1

            card = self._make_card(grid_frame, task)
            card.grid(
                row=row_i, column=col_i,
                columnspan=columnspan,
                padx=10, pady=10,
                sticky="nsew",
            )
            self._card_frames[task["id"]] = card

            if is_wide:
                row_i += 1
                col_i = 0
            else:
                col_i += 1
                if col_i >= 4:
                    col_i = 0
                    row_i += 1

        # ── Footer ────────────────────────────────────────────────────────────
        tk.Label(
            self,
            text="انقر على أي مهمة لبدء التحليل",
            font=FONT_ARABIC_SMALL,
            bg=BG_DARK, fg=TEXT_SECONDARY,
            pady=10,
        ).grid(row=4, column=0)

    # ── Card factory ──────────────────────────────────────────────────────────

    def _make_card(self, parent: tk.Widget, task: dict) -> tk.Frame:
        tid    = task["id"]
        color  = TASK_COLORS[tid - 1]
        is_wide = task.get("wide", False)

        card = tk.Frame(
            parent,
            bg=BG_CARD,
            relief="flat",
            bd=0,
            cursor="hand2",
        )

        # Coloured top accent bar
        accent = tk.Frame(card, bg=color, height=4)
        accent.pack(fill="x", side="top")

        inner = tk.Frame(card, bg=BG_CARD, padx=16, pady=14)
        inner.pack(fill="both", expand=True)

        # Icon + task number
        top_row = tk.Frame(inner, bg=BG_CARD)
        top_row.pack(fill="x")

        tk.Label(
            top_row,
            text=task["icon"],
            font=("Segoe UI Emoji", 22),
            bg=BG_CARD, fg=color,
        ).pack(side="left")

        tk.Label(
            top_row,
            text=f"#{tid}",
            font=("Segoe UI", 9),
            bg=BG_CARD, fg=TEXT_SECONDARY,
        ).pack(side="right", anchor="n", pady=(4, 0))

        # Arabic name
        tk.Label(
            inner,
            text=task["ar"],
            font=FONT_ARABIC_BODY,
            bg=BG_CARD, fg=TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x", pady=(8, 2))

        # English name
        tk.Label(
            inner,
            text=task["en"],
            font=FONT_BODY,
            bg=BG_CARD, fg=color,
            anchor="w",
        ).pack(fill="x")

        # Description
        tk.Label(
            inner,
            text=task["desc"],
            font=FONT_ARABIC_SMALL,
            bg=BG_CARD, fg=TEXT_SECONDARY,
            wraplength=260 if is_wide else 200,
            justify="right",
            anchor="w",
        ).pack(fill="x", pady=(6, 0))

        # Click button
        btn = tk.Button(
            inner,
            text="ابدأ ◀",
            font=FONT_ARABIC_SMALL,
            bg=color, fg="white",
            activebackground=BG_CARD_HOVER,
            relief="flat", bd=0, padx=14, pady=6,
            cursor="hand2",
            command=lambda t=tid: self._callback(t),
        )
        btn.pack(anchor="e", pady=(12, 0))

        # Hover effects
        def _enter(e, f=card, a=accent, c=color):
            f.configure(bg=BG_CARD_HOVER)
            a.configure(bg=c)
            for w in f.winfo_children():
                _set_bg_recursive(w, BG_CARD_HOVER, c)

        def _leave(e, f=card, a=accent, c=color):
            f.configure(bg=BG_CARD)
            a.configure(bg=c)
            for w in f.winfo_children():
                _set_bg_recursive(w, BG_CARD, c)

        card.bind("<Enter>", _enter)
        card.bind("<Leave>", _leave)
        card.bind("<Button-1>", lambda e, t=tid: self._callback(t))

        return card


def _set_bg_recursive(widget, bg_color, accent_color):
    """Recursively set background on widget tree, preserving button color."""
    try:
        if isinstance(widget, tk.Button):
            return  # Preserve button color
        widget.configure(bg=bg_color)
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        _set_bg_recursive(child, bg_color, accent_color)
