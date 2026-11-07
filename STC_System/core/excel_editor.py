import os
import logging
from datetime import datetime
import polars as pl
from .knowledge_base import CopilotKnowledgeBase
from export.excel_writer_xl import ExcelReportWriter

_log = logging.getLogger(__name__)

class SafeExcelEditor:
    """
    مُحرك التعديل الآمن لملفات Excel.
    ينشئ دائماً نسخة معدلة معنونة باسم Portfolio_v2_[timestamp].xlsx
    دون المساس بالملف الأصلي نهائياً، مع توليد شيت سجل التعديلات (Audit Log Sheet).
    """
    def __init__(self, kb: CopilotKnowledgeBase | None = None):
        self.kb = kb or CopilotKnowledgeBase()

    def export_versioned_excel(
        self,
        df: pl.DataFrame,
        original_filepath: str,
        action_name: str,
        output_dir: str | None = None,
        rows_affected: int = 0,
        cols_affected: str = "",
        reason: str = "تعديل تنفيذي بواسطة AI Operations Copilot"
    ) -> str:
        """
        يصدر نسخة معدلة آمنة بدون لمس الملف الأصلي، مع شيت سجل التعديلات.
        """
        base_name = os.path.basename(original_filepath)
        name_part, ext = os.path.splitext(base_name)
        if not ext:
            ext = ".xlsx"
            
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = self.kb.get_rule("excel_version_suffix", "v2")
        out_name = f"{name_part}_{suffix}_{ts}{ext}"
        
        if not output_dir:
            output_dir = os.path.dirname(original_filepath) if os.path.dirname(original_filepath) else "."
            
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, out_name)

        # 1. Write Excel using ExcelReportWriter
        writer = ExcelReportWriter(out_path)
        
        NAVY = "#1f6592"
        RED = "#c0392b"
        
        # Sheet 1: Modified Portfolio Data
        ws_data = writer._add_sheet("بيانات المحفظة المعدلة", "1f6592")
        writer._write_section_header(ws_data, f"📁 {name_part} - النسخة المعدلة ({suffix})", 0, NAVY)
        writer._write_dataframe(ws_data, df, writer._fmts["hdr_navy"], start_row=2)
        
        # Sheet 2: Audit Log Sheet
        ws_audit = writer._add_sheet("📋 سجل التعديلات (Audit)", "e74c3c")
        writer._write_section_header(ws_audit, "📋 سجل التعديلات والعمليات المنفذة (Audit Log)", 0, RED)
        
        audit_data = pl.DataFrame({
            "العنصر": ["الملف الأصلي", "ملف الإخراج المعدل", "الإجراء المنفذ", "عدد الصفوف المترتبة", "الأعمدة التابعة", "سبب التعديل", "وقت التنفيذ"],
            "التفاصيل": [base_name, out_name, action_name, str(rows_affected if rows_affected else len(df)), cols_affected if cols_affected else ", ".join(list(df.columns)[:5]), reason, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        })
        writer._write_dataframe(ws_audit, audit_data, writer._fmts["hdr_red"], start_row=2)
        
        writer.save()

        # 2. Log in SQLite Knowledge Base
        self.kb.log_execution(
            original_filename=base_name,
            output_filename=out_name,
            action_taken=action_name,
            rows_affected=rows_affected if rows_affected else len(df),
            cols_affected=cols_affected,
            reason=reason
        )

        _log.info("🛡️ Safe Versioned Export Completed: %s -> %s", base_name, out_path)
        return out_path
