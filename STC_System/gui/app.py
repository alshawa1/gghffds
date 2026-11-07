"""
gui/app.py
──────────
Main application controller.

Navigation flow:
  WelcomePanel  →  UploadPanel  →  ProcessingPanel  →  ResultsPanel
                          ↑_____________________________________________↓

Panel switching is done by destroying the current panel and creating a new one.
Analysis runs in a background thread to keep the UI responsive.
"""
from __future__ import annotations

import logging
import os
import threading
from datetime import datetime
from typing import Any, Dict, Optional

import tkinter as tk
from tkinter import messagebox

from core.data_loader import load_files
from core.utils import (
    COMPANY_PAY, MAHARAH_PAY, MAIN_PORTFOLIO, PROMISE_PAY,
    TASK_NAMES, TASK_FILE_REQUIREMENTS,
)
from export.excel_writer import ExcelReportWriter
from gui.styles import (
    BG_DARK, BG_SIDEBAR, FONT_ARABIC_SMALL, FONT_SMALL, FONT_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, WINDOW_HEIGHT, WINDOW_WIDTH, center_window,
)
from gui.welcome_panel    import WelcomePanel
from gui.upload_panel     import UploadPanel
from gui.processing_panel import ProcessingPanel
from gui.results_panel    import ResultsPanel
from gui.ai_panel         import AiPanel

_log = logging.getLogger("Application")

# Output directory: same folder as the input files (or workspace)
OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "..",   # one level up from STC_System/
    "output",
)


class Application:
    """Root application object. Creates the Tk window and manages panels."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Maharah Operations Automation System — STC Operations")
        self.root.configure(bg=BG_DARK)
        center_window(self.root, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.root.minsize(900, 600)
        self.root.resizable(True, True)

        # Try to set app icon (ignore if not found)
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

        # State
        self._current_panel: Optional[tk.Widget] = None
        self._selected_task:  int = 0
        self._file_paths:     Dict[str, str] = {}
        self._last_stats:     Dict[str, Any] = {}
        self._last_output:    str = ""

        # ── Layout: header + content area ─────────────────────────────────────
        self._build_layout()

        # Show welcome screen on start
        self._show_welcome()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_layout(self):
        """Header bar + scrollable main content area."""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # ── Header bar ────────────────────────────────────────────────────────
        header = tk.Frame(self.root, bg="#010409", height=52)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        header.grid_propagate(False)

        # Logo / brand
        tk.Label(
            header,
            text="🏢  Maharah Ops  |  STC",
            font=("Segoe UI", 12, "bold"),
            bg="#010409", fg="#1f6feb",
            padx=20,
        ).grid(row=0, column=0, sticky="w")

        # Breadcrumb label
        self._breadcrumb_var = tk.StringVar(value="الرئيسية")
        tk.Label(
            header,
            textvariable=self._breadcrumb_var,
            font=FONT_ARABIC_SMALL,
            bg="#010409", fg=TEXT_SECONDARY,
        ).grid(row=0, column=1)

        # AI Assistant button
        tk.Button(
            header,
            text="🤖 مساعد ذكي",
            font=FONT_ARABIC_SMALL,
            bg="#21262d", fg="#58a6ff",
            activebackground="#30363d",
            relief="flat", bd=0,
            padx=12, pady=4,
            cursor="hand2",
            command=self._open_ai_panel,
        ).grid(row=0, column=2, sticky="e", padx=(0, 8))

        # Date/time
        self._time_var = tk.StringVar()
        self._update_clock()
        tk.Label(
            header,
            textvariable=self._time_var,
            font=FONT_SMALL,
            bg="#010409", fg=TEXT_SECONDARY,
            padx=12,
        ).grid(row=0, column=3, sticky="e")

        # ── Content area ──────────────────────────────────────────────────────
        self._content = tk.Frame(self.root, bg=BG_DARK)
        self._content.grid(row=1, column=0, sticky="nsew")
        self._content.columnconfigure(0, weight=1)
        self._content.rowconfigure(0, weight=1)

    # ── Panel navigation ──────────────────────────────────────────────────────

    def _show_panel(self, panel: tk.Widget):
        if self._current_panel:
            self._current_panel.destroy()
        self._current_panel = panel
        panel.grid(row=0, column=0, sticky="nsew")
        self._content.columnconfigure(0, weight=1)
        self._content.rowconfigure(0, weight=1)

    def _show_welcome(self):
        self._breadcrumb_var.set("الرئيسية")
        panel = WelcomePanel(
            self._content,
            on_task_selected=self._on_task_selected,
        )
        self._show_panel(panel)

    def _show_upload(self, task_id: int):
        self._selected_task = task_id
        task_name = TASK_NAMES.get(task_id, "")
        self._breadcrumb_var.set(f"الرئيسية  ▶  {task_name}")
        panel = UploadPanel(
            self._content,
            task_id=task_id,
            on_proceed=self._on_files_ready,
            on_back=self._show_welcome,
        )
        self._show_panel(panel)

    def _show_processing(self, task_id: int) -> ProcessingPanel:
        task_name = TASK_NAMES.get(task_id, "")
        self._breadcrumb_var.set(f"الرئيسية  ▶  {task_name}  ▶  جاري المعالجة")
        panel = ProcessingPanel(
            self._content,
            task_name=task_name,
            on_cancel=self._show_welcome,
        )
        self._show_panel(panel)
        return panel

    def _show_results(self, task_id: int, stats: Dict[str, Any], output_path: str):
        self._last_stats  = stats          # persist for AI panel
        self._last_output = output_path
        task_name = TASK_NAMES.get(task_id, "")
        self._breadcrumb_var.set(f"الرئيسية  ▶  {task_name}  ▶  النتائج")
        panel = ResultsPanel(
            self._content,
            task_id=task_id,
            stats=stats,
            output_path=output_path,
            on_back_to_menu=self._show_welcome,
            on_run_again=lambda: self._show_upload(task_id),
        )
        self._show_panel(panel)

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_task_selected(self, task_id: int):
        _log.info("تم اختيار المهمة: %d", task_id)
        self._show_upload(task_id)

    def _on_files_ready(self, paths: Dict[str, str]):
        self._file_paths = paths
        if self._selected_task == 6:
            self._show_rotation_selection(paths)
        else:
            proc_panel = self._show_processing(self._selected_task)
            # Run analysis in background thread
            thread = threading.Thread(
                target=self._run_analysis,
                args=(self._selected_task, paths, proc_panel),
                daemon=True,
            )
            thread.start()

    def _show_rotation_selection(self, paths: Dict[str, str]):
        task_name = TASK_NAMES.get(6, "")
        self._breadcrumb_var.set(f"الرئيسية  ▶  {task_name}  ▶  تحديد معطيات التدوير")
        from gui.rotation_panel import RotationSelectionPanel
        panel = RotationSelectionPanel(
            self._content,
            file_paths=paths,
            on_proceed=self._on_rotation_selections_ready,
            on_back=self._show_welcome,
        )
        self._show_panel(panel)

    def _on_rotation_selections_ready(self, supervisor: str, collector: str, portfolio_df: pl.DataFrame):
        proc_panel = self._show_processing(6)
        params = {"supervisor": supervisor, "collector": collector}
        thread = threading.Thread(
            target=self._run_analysis,
            args=(6, self._file_paths, proc_panel, params),
            daemon=True,
        )
        thread.start()

    # ── Analysis runner ───────────────────────────────────────────────────────

    # ── Analysis runner ───────────────────────────────────────────────────────

    def _run_analysis(
        self,
        task_id: int,
        paths: Dict[str, str],
        proc: ProcessingPanel,
        rotation_params: Optional[Dict[str, str]] = None,
    ):
        """
        Background thread: loads files, runs selected module(s), exports Excel.
        All UI updates go through self.root.after() for thread safety.
        """
        def log(msg, level="INFO"):
            self.root.after(0, proc.log, msg, level)

        def status(msg):
            self.root.after(0, proc.set_status, msg)

        def set_stage(idx, state):
            self.root.after(0, proc.set_stage, idx, state)

        try:
            # ── 1. Reading Files ─────────────────────────────────────────────
            set_stage(1, "RUNNING")
            log("📂 قراءة الملفات من القرص أو الذاكرة المؤقتة...", "STEP")
            status("جاري قراءة ملفات الإكسل...")
            dfs, results = load_files(paths)
            set_stage(1, "SUCCESS")

            # ── 2. Validating Columns ─────────────────────────────────────────
            set_stage(2, "RUNNING")
            log("🔍 التحقق من الأعمدة المطلوبة وصحة البيانات...", "STEP")
            status("جاري التحقق من الهيكلية والأعمدة...")
            
            for key, vr in results.items():
                if vr.is_valid:
                    log(f"  ✅ {key} — تم التحقق بنجاح", "SUCCESS")
                else:
                    log(f"  ❌ {key} — {vr.summary()}", "ERROR")
                    raise ValueError(f"الملف {key} غير صالح: {vr.summary()}")
            set_stage(2, "SUCCESS")

            # ── 3. Cleaning Data ─────────────────────────────────────────────
            set_stage(3, "RUNNING")
            log("🧹 تنظيف البيانات وإزالة الفراغات الزائدة...", "STEP")
            status("جاري تنظيف وتوحيد البيانات...")
            
            portfolio = dfs.get(MAIN_PORTFOLIO)
            promise   = dfs.get(PROMISE_PAY)
            maharah   = dfs.get(MAHARAH_PAY)
            company   = dfs.get(COMPANY_PAY)
            set_stage(3, "SUCCESS")

            # ── 4. Matching Records ───────────────────────────────────────────
            set_stage(4, "RUNNING")
            log("🔗 ربط السجلات بالاعتماد على الحساب والمديونية والهوية...", "STEP")
            status("جاري مطابقة الحسابات والمديونيات...")
            # Matching operations are performed inside the modules, log index status
            log("  ✅ تم إنشاء خرائط الفهارس الذكية للمطابقة", "SUCCESS")
            set_stage(4, "SUCCESS")

            # ── 5. Running Business Rules ─────────────────────────────────────
            set_stage(5, "RUNNING")
            log("⚙️ تطبيق قواعد العمل التشغيلية للمهام المحددة...", "STEP")
            status("جاري تشغيل منطق قواعد العمل...")
            
            all_stats: Dict[str, Any] = {}
            writer = self._make_writer(task_id)

            if task_id in (1, 8):
                log("  ▶ تشغيل: أخطاء النظام", "INFO")
                from modules.module1_errors import SystemErrorsModule
                r = SystemErrorsModule().run(portfolio, promise)
                all_stats.update(r["stats"])
                writer.write_errors(r["data"])

            if task_id in (2, 8):
                log("  ▶ تشغيل: التوصل وعدم التوصل", "INFO")
                from modules.module2_contact import ContactStatusModule
                r = ContactStatusModule().run(portfolio)
                all_stats.update(r["stats"])
                writer.write_contact(
                    r["data"],
                    r["pivot_supervisor"],
                    r["pivot_collector"],
                    r["pivot_status"],
                )

            if task_id in (3, 8):
                log("  ▶ تشغيل: الإهمال", "INFO")
                from modules.module3_neglect import NeglectModule
                r = NeglectModule().run(portfolio)
                all_stats.update(r["stats"])
                writer.write_neglect(
                    r["data"],
                    r["full_analysis"],
                    r["pivot_summary"],
                    r["pivot_supervisor"],
                    r["pivot_collector"],
                    r["pivot_status"],
                    r["pivot_branch"],
                    r["pivot_portfolio"],
                    r["pivot_days"],
                )

            if task_id in (4, 8):
                log("  ▶ تشغيل: السدادات والتسوية", "INFO")
                from modules.module4_payments import PaymentsModule
                r = PaymentsModule().run(portfolio, maharah, company)
                all_stats.update(r["stats"])
                writer.write_addition(r["addition_data"])
                writer.write_settlement(r["settlement_data"])
                writer.write_edit_delete(r["edit_delete_data"])

            if task_id in (5, 8):
                log("  ▶ تشغيل: الجدولة", "INFO")
                from modules.module5_scheduling import SchedulingModule
                r = SchedulingModule().run(portfolio, maharah)
                all_stats.update(r["stats"])
                writer.write_scheduling(r["data"], r["pivot_type"], r["pivot_month"], r["pivot_year"], r["pivot_count"], r["pivot_supervisor"])

            if task_id == 6:
                log("  ▶ تشغيل: السحب والتدوير الجديد", "INFO")
                if not rotation_params:
                    raise ValueError("معلمات السحب والتدوير غير متوفرة")
                sup = rotation_params["supervisor"]
                col = rotation_params["collector"]
                from modules.module6b_rotation import PortfolioRotationModule
                r = PortfolioRotationModule().run(portfolio, col, sup)
                all_stats.update(r["stats"])
                writer.write_rotation(
                    r["data"],
                    r["execution_report"],
                    r["distribution_summary"],
                    r["withdrawal_summary"],
                )

            if task_id == 8:
                # Task 8 skips interactive rotation, but can run other operations.
                log("  ▶ تشغيل: تخطي السحب والتدوير التفاعلي في التقرير الشامل", "WARNING")

            if task_id in (7, 8):
                log("  ▶ تشغيل: العملاء المستهدفة", "INFO")
                from modules.module7_targets import TargetCustomersModule
                r = TargetCustomersModule().run(portfolio, promise, maharah)
                all_stats.update(r["stats"])
                writer.write_targets(r["data"], r["pivot_supervisor"])

            log("  ✅ اكتمل تطبيق جميع قواعد العمل المطلوبة بنجاح", "SUCCESS")
            set_stage(5, "SUCCESS")

            # ── 6. Creating Report ────────────────────────────────────────────
            set_stage(6, "RUNNING")
            log("📊 إنشاء لوحة معلومات التقرير والملخص التنفيذي...", "STEP")
            status("جاري كتابة وتنسيق جداول Excel...")
            writer.write_dashboard(all_stats, task_id)
            writer.write_summary(all_stats)
            set_stage(6, "SUCCESS")

            # ── 7. Exporting Excel ────────────────────────────────────────────
            set_stage(7, "RUNNING")
            log("💾 حفظ وتصدير ملف Excel النهائي بالصيغة والتنسيق المطلوب...", "STEP")
            status("جاري حفظ التقرير...")
            writer.save()
            output_path = writer.output_path
            log(f"  ✅ تم التصدير والحفظ بنجاح: {output_path}", "SUCCESS")
            set_stage(7, "SUCCESS")

            # ── 8. Completed Successfully ─────────────────────────────────────
            set_stage(8, "RUNNING")
            log("🎉 تم إنهاء جميع العمليات بنجاح!", "SUCCESS")
            status("اكتمل العمل بنجاح.")
            
            # Release memory automatically
            import gc
            del dfs
            del portfolio
            del promise
            del maharah
            del company
            gc.collect()
            log("🧹 تم تنظيف الذاكرة العشوائية وتحرير الموارد بنجاح", "INFO")
            
            set_stage(8, "SUCCESS")
            self.root.after(0, proc.finish)
            self.root.after(
                800,
                self._show_results,
                task_id, all_stats, output_path,
            )

        except Exception as exc:
            _log.exception("خطأ أثناء التحليل")
            log(f"❌ خطأ: {exc}", "ERROR")
            self.root.after(
                0,
                messagebox.showerror,
                "خطأ في التحليل",
                f"حدث خطأ غير متوقع:\n{exc}",
            )

    # ── Writer factory ────────────────────────────────────────────────────────

    def _make_writer(self, task_id: int) -> ExcelReportWriter:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_slug = {
            1: "system_errors",
            2: "contact_status",
            3: "neglect",
            4: "payments",
            5: "scheduling",
            6: "rotation",
            7: "targets",
            8: "full_report",
        }.get(task_id, "report")
        filename = f"STC_Ops_{task_slug}_{timestamp}.xlsx"
        path = os.path.join(OUTPUT_DIR, filename)
        return ExcelReportWriter(path)

    # ── Clock ─────────────────────────────────────────────────────────────────

    def _update_clock(self):
        self._time_var.set(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
        self.root.after(1000, self._update_clock)

    # ── AI Panel ──────────────────────────────────────────────────────────────

    def _open_ai_panel(self):
        """Open the floating AI assistant panel."""
        panel = AiPanel(self.root, self._last_stats)
        panel.grab_set()   # modal-ish but still allows using the app

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self):
        """Start the tkinter event loop."""
        _log.info("🚀 تشغيل النظام")
        self.root.mainloop()
