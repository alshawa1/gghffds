"""
gui/processing_panel.py
───────────────────────
Processing panel with a visual 8-stage progress tracker and scrollable logs.

Stages:
  1. 📂 قراءة الملفات (Reading Files)
  2. 🔍 التحقق من الأعمدة (Validating Columns)
  3. 🧹 تنظيف البيانات (Cleaning Data)
  4. 🔗 ربط السجلات (Matching Records)
  5. ⚙️ تطبيق قواعد العمل (Running Business Rules)
  6. 📊 إنشاء التقرير (Creating Report)
  7. 💾 تصدير ملف Excel (Exporting Excel)
  8. 🎉 اكتمل بنجاح (Completed Successfully)
"""
from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext
from typing import Callable, Optional

from gui.styles import (
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_RED, ACCENT_ORANGE,
    BG_CARD, BG_DARK, FONT_ARABIC_BODY, FONT_ARABIC_SMALL,
    FONT_ARABIC_TITLE, FONT_MONO, TEXT_PRIMARY, TEXT_SECONDARY,
)

STAGES = [
    "قراءة الملفات (Reading Files)",
    "التحقق من الأعمدة (Validating Columns)",
    "تنظيف البيانات (Cleaning Data)",
    "ربط السجلات (Matching Records)",
    "تطبيق قواعد العمل (Running Business Rules)",
    "إنشاء التقرير (Creating Report)",
    "تصدير ملف Excel (Exporting Excel)",
    "اكتمل بنجاح (Completed Successfully)",
]


class ProcessingPanel(tk.Frame):

    def __init__(
        self,
        parent: tk.Widget,
        task_name: str,
        on_cancel: Optional[Callable] = None,
    ):
        super().__init__(parent, bg=BG_DARK)
        self.task_name  = task_name
        self._cancel_cb = on_cancel
        self._stage_labels: dict[int, tk.Label] = {}
        self._stage_icons: dict[int, tk.Label] = {}
        self._build()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        self.columnconfigure(0, weight=4)  # Left column (Stages)
        self.columnconfigure(1, weight=6)  # Right column (Logs)
        self.rowconfigure(1, weight=1)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG_DARK, pady=16)
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew")
        hdr.columnconfigure(0, weight=1)

        tk.Label(
            hdr,
            text="⚙️  جاري تشغيل التحليل العملياتي",
            font=FONT_ARABIC_TITLE,
            bg=BG_DARK, fg=ACCENT_BLUE,
        ).grid(row=0, column=0)

        tk.Label(
            hdr,
            text=self.task_name,
            font=FONT_ARABIC_BODY,
            bg=BG_DARK, fg=TEXT_SECONDARY,
        ).grid(row=1, column=0, pady=(4, 0))

        # ── Left Pane: Stages Checklist ──────────────────────────────────────
        left_pane = tk.Frame(self, bg=BG_CARD, padx=20, pady=20, relief="flat")
        left_pane.grid(row=1, column=0, sticky="nsew", padx=(40, 10), pady=10)
        left_pane.columnconfigure(1, weight=1)

        tk.Label(
            left_pane,
            text="📋  خطوات المعالجة",
            font=FONT_ARABIC_BODY,
            bg=BG_CARD, fg=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 16))

        for idx, stage in enumerate(STAGES, start=1):
            # Status icon
            icon_lbl = tk.Label(
                left_pane,
                text="⏳",
                font=("Segoe UI Emoji", 14),
                bg=BG_CARD, fg=TEXT_SECONDARY,
                width=3,
            )
            icon_lbl.grid(row=idx, column=0, sticky="w", pady=8)
            self._stage_icons[idx] = icon_lbl

            # Stage text
            text_lbl = tk.Label(
                left_pane,
                text=f"{idx}. {stage}",
                font=FONT_ARABIC_SMALL,
                bg=BG_CARD, fg=TEXT_SECONDARY,
                anchor="w",
            )
            text_lbl.grid(row=idx, column=1, sticky="w", pady=8, padx=(10, 0))
            self._stage_labels[idx] = text_lbl

        # Status Label
        self._status_lbl = tk.Label(
            left_pane,
            text="جاري البدء...",
            font=FONT_ARABIC_SMALL,
            bg=BG_CARD, fg=TEXT_SECONDARY,
            anchor="w",
        )
        self._status_lbl.grid(row=len(STAGES) + 1, column=0, columnspan=2, sticky="w", pady=(15, 0))

        # ── Right Pane: Logs Console ─────────────────────────────────────────
        right_pane = tk.Frame(self, bg=BG_DARK, padx=10, pady=10)
        right_pane.grid(row=1, column=1, sticky="nsew", padx=(10, 40), pady=10)
        right_pane.columnconfigure(0, weight=1)
        right_pane.rowconfigure(1, weight=1)

        tk.Label(
            right_pane,
            text="💻  سجل التشغيل",
            font=FONT_ARABIC_SMALL,
            bg=BG_DARK, fg=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        self._log_text = scrolledtext.ScrolledText(
            right_pane,
            font=FONT_MONO,
            bg="#0d1117",
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            padx=12, pady=8,
            state="disabled",
        )
        self._log_text.grid(row=1, column=0, sticky="nsew")

        # Log color tags
        self._log_text.tag_configure("INFO",    foreground=TEXT_SECONDARY)
        self._log_text.tag_configure("SUCCESS", foreground=ACCENT_GREEN)
        self._log_text.tag_configure("WARNING", foreground=ACCENT_ORANGE)
        self._log_text.tag_configure("ERROR",   foreground=ACCENT_RED)
        self._log_text.tag_configure("STEP",    foreground=ACCENT_BLUE)

        # ── Cancel Button ─────────────────────────────────────────────────────
        if self._cancel_cb:
            tk.Button(
                self,
                text="إلغاء",
                font=FONT_ARABIC_SMALL,
                bg="#21262d", fg=TEXT_SECONDARY,
                activebackground=BG_CARD,
                relief="flat", bd=0, padx=20, pady=8,
                cursor="hand2",
                command=self._cancel_cb,
            ).grid(row=2, column=0, columnspan=2, pady=16)

    # ── Stage controller ──────────────────────────────────────────────────────

    def set_stage(self, stage_idx: int, status: str):
        """
        Set status of a specific stage.
        status: "RUNNING" (🔄) | "SUCCESS" (✅) | "ERROR" (❌) | "PENDING" (⏳)
        """
        if stage_idx not in self._stage_labels:
            return

        icon_lbl = self._stage_icons[stage_idx]
        text_lbl = self._stage_labels[stage_idx]

        if status == "RUNNING":
            icon_lbl.configure(text="🔄", fg=ACCENT_BLUE)
            text_lbl.configure(fg=TEXT_PRIMARY, font=("Tahoma", 10, "bold"))
        elif status == "SUCCESS":
            icon_lbl.configure(text="✅", fg=ACCENT_GREEN)
            text_lbl.configure(fg=ACCENT_GREEN, font=("Tahoma", 10))
        elif status == "ERROR":
            icon_lbl.configure(text="❌", fg=ACCENT_RED)
            text_lbl.configure(fg=ACCENT_RED, font=("Tahoma", 10, "bold"))
        else:
            icon_lbl.configure(text="⏳", fg=TEXT_SECONDARY)
            text_lbl.configure(fg=TEXT_SECONDARY, font=("Tahoma", 10))

    def log(self, msg: str, level: str = "INFO"):
        self._log_text.configure(state="normal")
        self._log_text.insert("end", msg + "\n", level)
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def set_status(self, msg: str):
        """Update the status label at the bottom of the checklist."""
        self._status_lbl.configure(text=msg, fg=TEXT_SECONDARY)

    def finish(self):
        """Finalize the processing UI."""
        self._status_lbl.configure(text="✅  اكتمل التحليل بنجاح", fg=ACCENT_GREEN)
