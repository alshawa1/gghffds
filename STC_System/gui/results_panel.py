"""
gui/results_panel.py
────────────────────
Results panel shown after analysis completes.

Features:
  • KPI summary cards with colour-coded values
  • Export to Excel button
  • Open output file button
  • Run again / back to menu buttons
  • Scrollable KPI table
"""
from __future__ import annotations

import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Any, Callable, Dict, Optional

from gui.styles import (
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_RED, ACCENT_ORANGE,
    BG_CARD, BG_DARK, FONT_ARABIC_BODY, FONT_ARABIC_SMALL,
    FONT_ARABIC_TITLE, FONT_BODY, FONT_SMALL, TASK_COLORS,
    TEXT_PRIMARY, TEXT_SECONDARY,
)


class ResultsPanel(tk.Frame):
    """
    Displayed after analysis completes. Shows KPIs and export controls.
    """

    def __init__(
        self,
        parent: tk.Widget,
        task_id: int,
        stats: Dict[str, Any],
        output_path: str,
        on_back_to_menu: Callable[[], None],
        on_run_again: Callable[[], None],
    ):
        super().__init__(parent, bg=BG_DARK)
        self.task_id     = task_id
        self.stats       = stats
        self.output_path = output_path
        self._back_cb    = on_back_to_menu
        self._again_cb   = on_run_again
        self._build()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        color = TASK_COLORS[self.task_id - 1]

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG_DARK, pady=20)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(0, weight=1)

        tk.Label(
            hdr,
            text="✅  اكتمل التحليل بنجاح",
            font=FONT_ARABIC_TITLE,
            bg=BG_DARK, fg=ACCENT_GREEN,
        ).grid(row=0, column=0)

        tk.Label(
            hdr,
            text="النتائج جاهزة — يمكنك الآن تصدير التقرير",
            font=FONT_ARABIC_BODY,
            bg=BG_DARK, fg=TEXT_SECONDARY,
        ).grid(row=1, column=0, pady=(4, 0))

        tk.Frame(self, height=1, bg="#30363d").grid(row=1, column=0, sticky="ew", padx=40)

        # ── KPI cards row ─────────────────────────────────────────────────────
        kpi_frame = tk.Frame(self, bg=BG_DARK, padx=40, pady=18)
        kpi_frame.grid(row=2, column=0, sticky="ew")

        kpi_items = list(self.stats.items())[:8]  # Show top 8 KPIs as cards
        cols = min(len(kpi_items), 4)

        for col_i in range(cols):
            kpi_frame.columnconfigure(col_i, weight=1, uniform="kpi")

        for i, (label, value) in enumerate(kpi_items):
            col_i = i % cols
            row_i = i // cols
            card_color = TASK_COLORS[i % len(TASK_COLORS)]
            self._make_kpi_card(kpi_frame, label, value, card_color, row_i, col_i)

        # ── Full stats table (scrollable) ─────────────────────────────────────
        table_frame = tk.Frame(self, bg=BG_DARK, padx=40)
        table_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(1, weight=1)

        tk.Label(
            table_frame,
            text="📊  جميع المؤشرات",
            font=FONT_ARABIC_SMALL,
            bg=BG_DARK, fg=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        # Canvas + scrollbar for the stats table
        canvas = tk.Canvas(table_frame, bg=BG_CARD, highlightthickness=0, height=150)
        scrollbar = tk.Scrollbar(table_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")

        inner = tk.Frame(canvas, bg=BG_CARD)
        canvas.create_window((0, 0), window=inner, anchor="nw")

        for i, (label, value) in enumerate(self.stats.items()):
            bg = BG_CARD if i % 2 == 0 else "#1c2333"
            row_frame = tk.Frame(inner, bg=bg, padx=16, pady=6)
            row_frame.pack(fill="x")

            tk.Label(row_frame, text=label, font=FONT_ARABIC_SMALL,
                     bg=bg, fg=TEXT_PRIMARY, anchor="w").pack(side="right")
            tk.Label(row_frame, text=str(value), font=("Tahoma", 10, "bold"),
                     bg=bg, fg=ACCENT_BLUE).pack(side="left")

        inner.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

        # ── Action buttons ────────────────────────────────────────────────────
        btn_row = tk.Frame(self, bg=BG_DARK, pady=16)
        btn_row.grid(row=4, column=0, sticky="ew", padx=40)

        tk.Button(
            btn_row,
            text="◀  القائمة الرئيسية",
            font=FONT_ARABIC_BODY,
            bg=BG_CARD, fg=TEXT_SECONDARY,
            activebackground="#21262d",
            relief="flat", bd=0, padx=18, pady=10,
            cursor="hand2",
            command=self._back_cb,
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            btn_row,
            text="🔄  تشغيل مجدداً",
            font=FONT_ARABIC_BODY,
            bg=BG_CARD, fg=TEXT_SECONDARY,
            activebackground="#21262d",
            relief="flat", bd=0, padx=18, pady=10,
            cursor="hand2",
            command=self._again_cb,
        ).pack(side="left")

        # Open file button
        tk.Button(
            btn_row,
            text="📂  فتح ملف الإخراج",
            font=FONT_ARABIC_BODY,
            bg=ACCENT_ORANGE, fg="white",
            activebackground="#b7770d",
            relief="flat", bd=0, padx=18, pady=10,
            cursor="hand2",
            command=self._open_output,
        ).pack(side="right", padx=(10, 0))

        # Export button
        tk.Button(
            btn_row,
            text="💾  حفظ بمسار آخر",
            font=FONT_ARABIC_BODY,
            bg=color, fg="white",
            activebackground="#155ea8",
            relief="flat", bd=0, padx=24, pady=10,
            cursor="hand2",
            command=self._save_as,
        ).pack(side="right")

    # ── Card factory ──────────────────────────────────────────────────────────

    def _make_kpi_card(
        self, parent, label: str, value, color: str, row_i: int, col_i: int
    ):
        card = tk.Frame(parent, bg=BG_CARD, padx=14, pady=12, relief="flat")
        card.grid(row=row_i, column=col_i, padx=8, pady=8, sticky="nsew")

        # Accent stripe
        tk.Frame(card, bg=color, height=3).pack(fill="x", side="top")
        tk.Label(
            card, text=str(value),
            font=("Tahoma", 20, "bold"),
            bg=BG_CARD, fg=color,
        ).pack()
        tk.Label(
            card, text=label,
            font=FONT_ARABIC_SMALL,
            bg=BG_CARD, fg=TEXT_SECONDARY,
            wraplength=150,
        ).pack()

    # ── File actions ──────────────────────────────────────────────────────────

    def _open_output(self):
        if not os.path.exists(self.output_path):
            messagebox.showerror("خطأ", "ملف الإخراج غير موجود")
            return
        try:
            os.startfile(self.output_path)
        except Exception as e:
            messagebox.showerror("خطأ في فتح الملف", str(e))

    def _save_as(self):
        import shutil
        dest = filedialog.asksaveasfilename(
            title="حفظ التقرير",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=os.path.basename(self.output_path),
        )
        if not dest:
            return
        try:
            shutil.copy2(self.output_path, dest)
            messagebox.showinfo("تم الحفظ", f"تم حفظ التقرير في:\n{dest}")
        except Exception as e:
            messagebox.showerror("خطأ في الحفظ", str(e))
