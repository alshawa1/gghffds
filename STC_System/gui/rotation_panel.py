"""
gui/rotation_panel.py
──────────────────────
Dedicated UI Panel for Portfolio Rotation (السحب والتدوير).
Allows user to:
1. Select Supervisor.
2. Select Collector to withdraw from.
3. Preview target customer counts.
4. Run round-robin reassignment.
"""
from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict, List, Optional

import polars as pl

from core.data_loader import load_files
from core.utils import MAIN_PORTFOLIO
from gui.styles import (
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_RED, BORDER, BG_CARD, BG_DARK, BG_INPUT,
    FONT_ARABIC_BODY, FONT_ARABIC_SMALL, FONT_ARABIC_TITLE, FONT_BODY,
    FONT_SMALL, FONT_TITLE, TASK_COLORS, TEXT_PRIMARY, TEXT_SECONDARY,
)
from modules.module6b_rotation import PortfolioRotationModule

_log = logging.getLogger("RotationPanel")


class RotationSelectionPanel(tk.Frame):
    """
    Panel to select Supervisor and Collector for portfolio rotation.
    Shown after uploading the main portfolio file.
    """

    def __init__(
        self,
        parent: tk.Widget,
        file_paths: Dict[str, str],
        on_proceed: Callable[[str, str, pl.DataFrame], None],
        on_back: Callable[[], None],
    ):
        super().__init__(parent, bg=BG_DARK)
        self.file_paths = file_paths
        self.on_proceed = on_proceed
        self.on_back    = on_back

        self.portfolio_df: Optional[pl.DataFrame] = None
        self.supervisors: List[str] = []

        # Form variables
        self.sup_var = tk.StringVar()
        self.col_var = tk.StringVar()

        self._build()
        self._load_portfolio_async()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG_DARK, pady=16)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(0, weight=1)

        tk.Label(
            hdr,
            text="🔄  برنامج السحب والتدوير (Portfolio Rotation)",
            font=FONT_ARABIC_TITLE,
            bg=BG_DARK, fg="#e67e22",
        ).grid(row=0, column=0, sticky="w", padx=40)

        tk.Label(
            hdr,
            text="سحب محفظة محصل معين وإعادة توزيعها بالعميل على محصلي نفس المشرف بالتساوي",
            font=FONT_ARABIC_BODY,
            bg=BG_DARK, fg=TEXT_SECONDARY,
        ).grid(row=1, column=0, sticky="w", padx=40, pady=(4, 0))

        tk.Frame(self, height=1, bg=BORDER).grid(row=1, column=0, sticky="ew", padx=40)

        # ── Loading Overlay/Label ─────────────────────────────────────────────
        self.loading_frame = tk.Frame(self, bg=BG_DARK)
        self.loading_frame.grid(row=2, column=0, sticky="nsew", padx=40, pady=20)
        self.loading_frame.columnconfigure(0, weight=1)
        self.loading_frame.rowconfigure(0, weight=1)

        self.loading_lbl = tk.Label(
            self.loading_frame,
            text="⏳  جاري قراءة وتحليل بيانات المحفظة... يرجى الانتظار",
            font=FONT_ARABIC_BODY,
            bg=BG_DARK, fg=ACCENT_BLUE,
        )
        self.loading_lbl.grid(row=0, column=0)

        # ── Main Selection Card (Hidden initially during load) ────────────────
        self.card = tk.Frame(self, bg=BG_CARD, padx=30, pady=30, relief="flat")
        # card will be gridded after loading succeeds

    def _load_portfolio_async(self):
        def task():
            try:
                _log.info("Loading portfolio file for rotation selection dropdowns...")
                dfs, results = load_files(self.file_paths)
                df = dfs.get(MAIN_PORTFOLIO)
                if df is None or df.is_empty():
                    raise ValueError("ملف المحفظة فارغ أو لم يقرأ بشكل صحيح")

                # Get supervisors
                sups = PortfolioRotationModule.get_supervisors(df)
                if not sups:
                    raise ValueError("لم نجد مشرفين في ملف المحفظة. تأكد من وجود عمود 'المشرف'.")

                self.portfolio_df = df
                self.supervisors = sups

                self.after(0, self._on_load_success)
            except Exception as exc:
                _log.exception("Error loading portfolio for rotation")
                self.after(0, lambda e=exc: self._on_load_error(str(e)))

        threading.Thread(target=task, daemon=True).start()

    def _on_load_success(self):
        self.loading_frame.grid_forget()
        self.card.grid(row=2, column=0, sticky="nsew", padx=40, pady=20)
        self.card.columnconfigure(1, weight=1)

        # Build dropdown fields inside card
        style = ttk.Style()
        style.theme_use('combobox')
        style.configure('TCombobox',
                        fieldbackground=BG_INPUT,
                        background=BG_CARD,
                        foreground=TEXT_PRIMARY,
                        font=FONT_ARABIC_SMALL)

        # 1. Supervisor select
        tk.Label(
            self.card, text="1. اختر اسم المشرف :",
            font=FONT_ARABIC_BODY, bg=BG_CARD, fg=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.sup_combo = ttk.Combobox(
            self.card,
            textvariable=self.sup_var,
            values=self.supervisors,
            state="readonly",
            font=FONT_ARABIC_BODY,
            width=40,
        )
        self.sup_combo.grid(row=0, column=1, sticky="w", pady=(0, 10), padx=20)
        self.sup_combo.bind("<<ComboboxSelected>>", self._on_supervisor_selected)

        # 2. Collector select
        tk.Label(
            self.card, text="2. اسم المحصل المسحوب :",
            font=FONT_ARABIC_BODY, bg=BG_CARD, fg=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(10, 10))

        self.col_combo = ttk.Combobox(
            self.card,
            textvariable=self.col_var,
            state="disabled",
            font=FONT_ARABIC_BODY,
            width=40,
        )
        self.col_combo.grid(row=1, column=1, sticky="w", pady=(10, 10), padx=20)
        self.col_combo.bind("<<ComboboxSelected>>", self._on_collector_selected)

        # 3. Preview Area
        self.preview_lbl = tk.Label(
            self.card,
            text="💡 يرجى اختيار المشرف والمحصل للبدء.",
            font=FONT_ARABIC_SMALL,
            bg=BG_CARD, fg=TEXT_SECONDARY,
            justify="right", anchor="e",
        )
        self.preview_lbl.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(20, 10))

        # ── Controls row inside card ──
        ctrls = tk.Frame(self.card, bg=BG_CARD, pady=20)
        ctrls.grid(row=3, column=0, columnspan=2, sticky="ew")

        tk.Button(
            ctrls,
            text="◀ العودة للخلف",
            font=FONT_ARABIC_BODY,
            bg=BG_DARK, fg=TEXT_SECONDARY,
            relief="flat", bd=0, padx=20, pady=8,
            cursor="hand2",
            command=self.on_back,
        ).pack(side="left")

        self.proceed_btn = tk.Button(
            ctrls,
            text="تأكيد وبدء السحب والتدوير 🔄",
            font=FONT_ARABIC_BODY,
            bg="#e67e22", fg="white",
            relief="flat", bd=0, padx=24, pady=8,
            cursor="hand2",
            state="disabled",
            command=self._on_submit,
        )
        self.proceed_btn.pack(side="right")

    def _on_load_error(self, err_msg: str):
        self.loading_lbl.configure(text=f"❌ فشل قراءة الملف:\n{err_msg}", fg=ACCENT_RED)
        messagebox.showerror("خطأ في قراءة الملف", f"تعذر فتح المحفظة:\n{err_msg}")

    def _on_supervisor_selected(self, event=None):
        sup = self.sup_var.get()
        if not sup or self.portfolio_df is None:
            return

        cols = PortfolioRotationModule.get_collectors_for_supervisor(self.portfolio_df, sup)
        self.col_combo.configure(state="readonly", values=cols)
        self.col_var.set("")
        self.proceed_btn.configure(state="disabled")
        self.preview_lbl.configure(
            text="💡 الآن اختر المحصل الذي ترغب في سحب عملاءه وتوزيعهم.",
            fg=TEXT_SECONDARY
        )

    def _on_collector_selected(self, event=None):
        sup = self.sup_var.get()
        col = self.col_var.get()
        if not sup or not col or self.portfolio_df is None:
            return

        # Count debts & customers for preview
        # First detect column names
        from modules.module6b_rotation import _detect, _SUPERVISOR_COLS, _COLLECTOR_COLS, _ID_COLS
        id_col = _detect(self.portfolio_df, _ID_COLS)
        col_col = _detect(self.portfolio_df, _COLLECTOR_COLS)
        sup_col = _detect(self.portfolio_df, _SUPERVISOR_COLS)

        # Get counts
        col_df = self.portfolio_df.filter(
            (pl.col(col_col).cast(pl.String).str.strip_chars() == col.strip()) &
            (pl.col(sup_col).cast(pl.String).str.strip_chars() == sup.strip())
        )
        total_debts = len(col_df)
        total_custs = col_df.select(id_col).n_unique() if id_col else 0

        # Available collectors pool count
        all_cols = PortfolioRotationModule.get_collectors_for_supervisor(self.portfolio_df, sup)
        pool_size = len([c for c in all_cols if c.strip() != col.strip()])

        if total_custs == 0:
            self.preview_lbl.configure(
                text=f"⚠️ هذا المحصل ليس لديه أي عملاء مسجلين تحت المشرف '{sup}'.",
                fg=ACCENT_RED
            )
            self.proceed_btn.configure(state="disabled")
            return

        if pool_size == 0:
            self.preview_lbl.configure(
                text=f"⚠️ لا يوجد أي محصلين آخرين تابعين للمشرف '{sup}' للتوزيع عليهم!",
                fg=ACCENT_RED
            )
            self.proceed_btn.configure(state="disabled")
            return

        msg = (
            f"✅ محفظة المحصل تحتوي على {total_custs} عميل فريد (بإجمالي {total_debts} مديونية).\n"
            f"سيتم سحبهم بالكامل وتوزيعهم بالتساوي على {pool_size} محصلين تابعين للمشرف '{sup}'."
        )
        self.preview_lbl.configure(text=msg, fg=ACCENT_GREEN)
        self.proceed_btn.configure(state="normal")

    def _on_submit(self):
        sup = self.sup_var.get()
        col = self.col_var.get()
        if not sup or not col or self.portfolio_df is None:
            return

        self.on_proceed(sup, col, self.portfolio_df)
