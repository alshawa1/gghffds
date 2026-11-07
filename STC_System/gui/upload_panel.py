"""
gui/upload_panel.py
───────────────────
High-performance File Upload panel with:
  1. Smart File Loading: Automatic file type detection via column names.
  2. Single-click multiple import.
  3. Visual indicators for cached or modified files.
"""
from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Callable, Dict, List, Optional

from core.data_loader import DataLoader, FileClassifier, SmartCache, ValidationResult, load_files, all_valid
from core.utils import (
    COMPANY_PAY, FILE_LABELS, MAHARAH_PAY, MAIN_PORTFOLIO,
    PROMISE_PAY, TASK_FILE_REQUIREMENTS, TASK_NAMES,
)
from gui.styles import (
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_RED, BG_CARD, BG_DARK, BG_INPUT,
    BORDER, FONT_ARABIC_BODY, FONT_ARABIC_SMALL, FONT_ARABIC_TITLE,
    FONT_BODY, FONT_SMALL, FONT_SUBTITLE, TASK_COLORS, TEXT_PRIMARY,
    TEXT_SECONDARY,
)

_LAST_DIR = os.path.expanduser("~")


class UploadPanel(tk.Frame):

    def __init__(
        self,
        parent: tk.Widget,
        task_id: int,
        on_proceed: Callable[[Dict[str, str]], None],
        on_back: Callable[[], None],
    ):
        super().__init__(parent, bg=BG_DARK)
        self.task_id    = task_id
        self._proceed_cb = on_proceed
        self._back_cb    = on_back

        self._required_keys: List[str] = TASK_FILE_REQUIREMENTS.get(task_id, [])
        self._paths: Dict[str, tk.StringVar] = {}
        self._status_labels: Dict[str, tk.Label] = {}
        self._msg_labels: Dict[str, tk.Label] = {}
        self._proceed_btn: Optional[tk.Button] = None

        self._build()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        self.columnconfigure(0, weight=1)

        color = TASK_COLORS[self.task_id - 1]
        task_name = TASK_NAMES.get(self.task_id, "")

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG_DARK, pady=14)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(0, weight=1)

        tk.Label(
            hdr, text=f"  #{self.task_id}  {task_name}",
            font=FONT_ARABIC_TITLE, bg=BG_DARK, fg=color,
        ).grid(row=0, column=0, sticky="w", padx=40)

        tk.Label(
            hdr, text="تحميل وتصنيف الملفات تلقائياً (Smart File Detection)",
            font=FONT_ARABIC_BODY, bg=BG_DARK, fg=TEXT_SECONDARY,
        ).grid(row=1, column=0, sticky="w", padx=40, pady=(4, 0))

        tk.Frame(self, height=1, bg=BORDER).grid(row=1, column=0, sticky="ew", padx=40)

        # ── Smart multi-upload section ────────────────────────────────────────
        smart_frame = tk.Frame(self, bg=BG_CARD, padx=16, pady=12)
        smart_frame.grid(row=2, column=0, sticky="ew", padx=40, pady=10)
        smart_frame.columnconfigure(0, weight=1)

        tk.Label(
            smart_frame,
            text="💡 اختر ملفاً واحداً أو عدة ملفات معاً، وسيقوم النظام بتصنيفها تلقائياً بالاعتماد على الأعمدة:",
            font=FONT_ARABIC_SMALL,
            bg=BG_CARD, fg=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        tk.Button(
            smart_frame,
            text="📂  رفع وتصنيف ذكي للملفات (Smart Upload)",
            font=FONT_ARABIC_BODY,
            bg=ACCENT_BLUE, fg="white",
            relief="flat", bd=0, padx=20, pady=8,
            cursor="hand2",
            command=self._smart_upload,
        ).grid(row=0, column=1, padx=(20, 0))

        # ── Required slots list ───────────────────────────────────────────────
        upload_frame = tk.Frame(self, bg=BG_DARK, padx=40, pady=10)
        upload_frame.grid(row=3, column=0, sticky="nsew")
        upload_frame.columnconfigure(0, weight=1)

        for idx, file_key in enumerate(self._required_keys):
            self._make_file_card(upload_frame, file_key, idx)

        # ── Bottom controls ───────────────────────────────────────────────────
        btn_row = tk.Frame(self, bg=BG_DARK, pady=16)
        btn_row.grid(row=4, column=0, sticky="ew", padx=40)

        tk.Button(
            btn_row,
            text="◀  العودة للرئيسية",
            font=FONT_ARABIC_BODY,
            bg=BG_CARD, fg=TEXT_SECONDARY,
            relief="flat", bd=0, padx=20, pady=10,
            cursor="hand2",
            command=self._back_cb,
        ).pack(side="left")

        self._proceed_btn = tk.Button(
            btn_row,
            text="بدء التحليل العملياتي  ▶",
            font=FONT_ARABIC_BODY,
            bg=color, fg="white",
            relief="flat", bd=0, padx=24, pady=10,
            cursor="hand2",
            command=self._on_validate_and_proceed,
        )
        self._proceed_btn.pack(side="right")

    # ── File Slot Card ────────────────────────────────────────────────────────

    def _make_file_card(self, parent: tk.Frame, file_key: str, idx: int):
        label = FILE_LABELS.get(file_key, file_key)
        color = TASK_COLORS[idx % len(TASK_COLORS)]

        card = tk.Frame(parent, bg=BG_CARD, relief="flat", bd=0, pady=2)
        card.grid(row=idx, column=0, sticky="ew", pady=4)
        card.columnconfigure(1, weight=1)

        # Accent bar
        tk.Frame(card, bg=color, width=4).grid(row=0, column=0, rowspan=4, sticky="ns", padx=(0, 12))

        # Title
        tk.Label(
            card, text=label,
            font=FONT_ARABIC_BODY,
            bg=BG_CARD, fg=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=(6, 2))

        # Browse row
        entry_row = tk.Frame(card, bg=BG_CARD)
        entry_row.grid(row=1, column=1, sticky="ew")
        entry_row.columnconfigure(0, weight=1)

        path_var = tk.StringVar()
        self._paths[file_key] = path_var

        path_entry = tk.Entry(
            entry_row,
            textvariable=path_var,
            font=FONT_SMALL,
            bg=BG_INPUT, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat", bd=0,
            state="readonly",
        )
        path_entry.grid(row=0, column=0, sticky="ew", ipady=6, padx=(0, 8))

        # Override browse
        tk.Button(
            entry_row,
            text="📂 استعراض",
            font=FONT_ARABIC_SMALL,
            bg="#21262d", fg=TEXT_PRIMARY,
            relief="flat", bd=0, padx=14, pady=6,
            cursor="hand2",
            command=lambda k=file_key, pv=path_var: self._manual_browse(k, pv),
        ).grid(row=0, column=1)

        # Status
        status_lbl = tk.Label(
            card, text="⏳  في انتظار الملف",
            font=FONT_ARABIC_SMALL,
            bg=BG_CARD, fg=TEXT_SECONDARY,
            anchor="w",
        )
        status_lbl.grid(row=2, column=1, sticky="w", pady=(2, 4))
        self._status_labels[file_key] = status_lbl

        # Message
        msg_lbl = tk.Label(
            card, text="",
            font=FONT_SMALL,
            bg=BG_CARD, fg=ACCENT_RED,
            anchor="w", justify="left",
        )
        msg_lbl.grid(row=3, column=1, sticky="w")
        self._msg_labels[file_key] = msg_lbl

    # ── Smart upload handler ──────────────────────────────────────────────────

    def _smart_upload(self):
        global _LAST_DIR
        paths = filedialog.askopenfilenames(
            title="اختر ملفات العمل للتحليل التلقائي",
            initialdir=_LAST_DIR,
            filetypes=[("Excel", "*.xlsx *.xls")],
        )
        if not paths:
            return

        _LAST_DIR = os.path.dirname(paths[0])
        
        # Classify each file in a background thread to keep UI fast
        threading.Thread(target=self._classify_and_map, args=(paths,), daemon=True).start()

    def _classify_and_map(self, paths: tuple[str]):
        classified = {}
        for path in paths:
            detected = FileClassifier.detect_type(path)
            if detected:
                classified[detected] = path
            else:
                self.after(0, lambda p=path: messagebox.showwarning(
                    "ملف غير معروف",
                    f"تعذر التعرف التلقائي على نوع الملف:\n{os.path.basename(p)}\nيرجى ربطه يدوياً."
                ))

        # Update UI vars
        for key, path in classified.items():
            if key in self._required_keys:
                self._paths[key].set(path)
                self.after(0, self._run_validation_bg, key, path)

    # ── Manual browse handler ─────────────────────────────────────────────────

    def _manual_browse(self, file_key: str, path_var: tk.StringVar):
        global _LAST_DIR
        path = filedialog.askopenfilename(
            title=f"اختر ملف: {FILE_LABELS.get(file_key, file_key)}",
            initialdir=_LAST_DIR,
            filetypes=[("Excel", "*.xlsx *.xls")],
        )
        if not path:
            return
        _LAST_DIR = os.path.dirname(path)
        path_var.set(path)
        self._run_validation_bg(file_key, path)

    # ── Validation runner ─────────────────────────────────────────────────────

    def _run_validation_bg(self, file_key: str, path: str):
        self._status_labels[file_key].configure(text="🔄  جاري التحقق...", fg=TEXT_SECONDARY)
        self._msg_labels[file_key].configure(text="")
        
        def run():
            loader = DataLoader(file_key)
            _, vr = loader.load(path)
            self.after(0, self._update_status, file_key, path, vr)

        threading.Thread(target=run, daemon=True).start()

    def _update_status(self, file_key: str, path: str, vr: ValidationResult):
        # Check if loaded from cache
        is_cached = SmartCache.get(path) is not None
        cache_status = " (⚡ مسترد من الذاكرة)" if is_cached else ""

        if vr.is_valid:
            self._status_labels[file_key].configure(
                text=f"✅  الملف جاهز وصحيح{cache_status}",
                fg=ACCENT_GREEN,
            )
            self._msg_labels[file_key].configure(text="")
        else:
            self._status_labels[file_key].configure(
                text="❌  خطأ في التحقق من هيكلية الملف",
                fg=ACCENT_RED,
            )
            self._msg_labels[file_key].configure(
                text="\n".join(vr.errors + vr.warnings)
            )

    # ── Proceed check ─────────────────────────────────────────────────────────

    def _on_validate_and_proceed(self):
        missing = [FILE_LABELS[k] for k in self._required_keys if not self._paths[k].get().strip()]
        if missing:
            messagebox.showwarning(
                "ملفات مفقودة",
                "الرجاء اختيار أو إسقاط الملفات التالية للمهمة:\n\n" + "\n".join(missing)
            )
            return

        paths = {k: self._paths[k].get() for k in self._required_keys}
        self._proceed_cb(paths)
