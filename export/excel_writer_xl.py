"""
export/excel_writer_xl.py
─────────────────────────
ExcelReportWriter v2 — استخدام xlsxwriter بدل openpyxl
أسرع 5-10x للملفات الكبيرة (54k+ صف)

xlsxwriter مزايا:
  • يكتب مباشرة للـ XML stream (constant_memory mode)
  • لا يحتاج تحميل كامل الملف في الذاكرة
  • 5-10x أسرع من openpyxl للـ save
  • يدعم كل مميزات openpyxl: RTL, freeze, autofilter, charts, conditional_format
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import polars as pl
import xlsxwriter
from xlsxwriter import Workbook
from xlsxwriter.worksheet import Worksheet
from xlsxwriter.utility import xl_range

_log = logging.getLogger("ExcelWriterXL")

# ── لوحة الألوان ─────────────────────────────────────────────────────────────
NAVY   = "#1f2d5a"
WHITE  = "#FFFFFF"
RED    = "#da3633"
GREEN  = "#238636"
AMBER  = "#d29922"
PURPLE = "#8957e5"
TEAL   = "#1abc9c"
BLUE   = "#1f6feb"
LT_BLUE = "#dce6f1"
LT_GREY = "#f5f5f5"
DARK_BG = "#0d1117"
CARD_BG = "#161b22"

# Tab colours per sheet
TAB_COLORS = {
    "Dashboard":              "1f6feb",
    "Summary":                "238636",
    "اخطاء النظام":          "da3633",
    "التوصل":                 "28a745",
    "الإهمال":                "d29922",
    "تحليل الإهمال":          "f39c12",
    "العملاء المستهدفة":     "9b59b6",
    "ملف التنفيذ":            "e67e22",
    "ملخص التوزيع":           "2ecc71",
    "ملخص السحب":            "e74c3c",
    "بيانات السحب والتدوير": "3498db",
    # Balancing sheets
    "قبل التوزيع":            "1f6feb",
    "بعد التوزيع":            "27ae60",
    "تفاصيل النقل":           "8e44ad",
    "ملخص العملية":           "e67e22",
    "بيانات التوزيع":         "2980b9",
    "خطة التوازن":             "e74c3c",
    "بيانات المحفظة":         "1f6feb",
}

TASK_KPIS = {
    1: [
        ("👥 إجمالي العملاء",      "إجمالي العملاء",          "1f6feb"),
        ("❌ بأخطاء",              "عملاء بأخطاء",             "da3633"),
        ("✅ بدون أخطاء",          "عملاء بدون أخطاء",        "238636"),
        ("📊 نسبة الأخطاء",        "نسبة الأخطاء %",           "f0883e"),
    ],
    2: [
        ("👥 إجمالي العملاء",      "إجمالي العملاء",          "1f6feb"),
        ("✅ تم التوصل",           "تم التوصل",                "238636"),
        ("📵 عدم التوصل",          "عدم التوصل",              "da3633"),
        ("🔒 لا يرد ومغلق",        "لا يرد ومغلق",            "f0883e"),
        ("📊 نسبة التوصل %",       "نسبة التوصل %",            "1abc9c"),
    ],
    3: [
        ("👥 إجمالي العملاء",      "إجمالي العملاء",          "1f6feb"),
        ("😴 مهمل",               "مهمل",                     "da3633"),
        ("✅ غير مهمل",           "غير مهمل",                 "238636"),
        ("📊 نسبة الإهمال %",      "نسبة الإهمال %",           "d29922"),
    ],
    6: [
        ("👥 عملاء مسحوبين",      "عدد العملاء المسحوبين",    "1f6feb"),
        ("📋 عدد المديونيات",      "عدد المديونيات",          "d29922"),
        ("👥 محصلين مستقبِلين",   "عدد المحصلين المستقبِلين", "1abc9c"),
        ("💰 إجمالي المتبقي",       "إجمالي متبقي السداد",     "238636"),
    ],
    7: [
        ("👥 إجمالي العملاء",      "إجمالي العملاء",          "1f6feb"),
        ("🎯 مستهدف",              "مستهدف",                   "238636"),
        ("🔴 غير مستهدف",          "غير مستهدف",               "da3633"),
    ],
    8: [
        ("👥 عملاء منقولون",       "عدد العملاء المنقولين",    "1f6feb"),
        ("👥 محصلون مشاركون",      "عدد المحصلين المستهدفين",  "1abc9c"),
        ("💰 إجمالي السداد المنقول", "إجمالي متبقي السداد المنقول", "238636"),
    ],
}

TASK_ARABIC_NAMES = {
    1: "أخطاء النظام",
    2: "التوصل وعدم التوصل",
    3: "الإهمال",
    6: "السحب والتدوير",
    7: "العملاء المستهدفة",
    8: "سحب وتوزيع المحافظ",
}

# ────────────────────────────────────────────────────────────────────────────
_TABLE_COUNTER = 0

def _next_table_name(prefix: str = "Tbl") -> str:
    global _TABLE_COUNTER
    _TABLE_COUNTER += 1
    safe = "".join(c if c.isalnum() else "_" for c in prefix)[:12]
    return f"{safe}_{_TABLE_COUNTER}"


class ExcelReportWriter:
    """
    يُنشئ ملف Excel واحد ويكشف دوال للكتابة في كل شيت.
    اتصل بـ save() في النهاية.
    """

    def __init__(self, output_path: str):
        global _TABLE_COUNTER
        _TABLE_COUNTER = 0
        self.output_path = output_path
        # constant_memory False: allows conditional_format + set_column
        # Still 5-8x faster than openpyxl because xlsxwriter writes XML streams
        self.wb: Workbook = xlsxwriter.Workbook(
            output_path,
            {
                "strings_to_numbers": True,
                "nan_inf_to_errors": True
            }
        )
        self._sheets_written: list[str] = []
        self._fmts: dict[str, Any] = {}
        self._init_formats()
        _log.info("🗂  تهيئة ملف الإخراج (xlsxwriter): %s", output_path)

    # ── Format factory ────────────────────────────────────────────────────────

    def _init_formats(self):
        """تعريف كل formats مرة واحدة بره اللوبات."""
        wb = self.wb

        def hdr(bg: str) -> Any:
            return wb.add_format({
                "bold": True, "font_name": "Tahoma", "font_size": 11,
                "bg_color": bg, "font_color": "#FFFFFF",
                "border": 1, "border_color": "#b0b8c1",
                "align": "right", "valign": "vcenter", "reading_order": 2,
            })

        self._fmts = {
            "hdr_navy":   hdr(NAVY),
            "hdr_red":    hdr(RED),
            "hdr_green":  hdr(GREEN),
            "hdr_amber":  hdr(AMBER),
            "hdr_purple": hdr(PURPLE),
            "hdr_teal":   hdr(TEAL),
            "hdr_blue":   hdr(BLUE),

            "data": wb.add_format({
                "font_name": "Tahoma", "font_size": 10, "font_color": "#1a1a2e",
                "align": "right", "valign": "vcenter", "reading_order": 2,
            }),
            "data_a": wb.add_format({  # alternating row A
                "font_name": "Tahoma", "font_size": 10, "font_color": "#1a1a2e",
                "bg_color": LT_BLUE,
                "align": "right", "valign": "vcenter", "reading_order": 2,
            }),
            "data_b": wb.add_format({  # alternating row B
                "font_name": "Tahoma", "font_size": 10, "font_color": "#1a1a2e",
                "bg_color": LT_GREY,
                "align": "right", "valign": "vcenter", "reading_order": 2,
            }),
            "num_a": wb.add_format({
                "font_name": "Tahoma", "font_size": 10, "font_color": "#1a1a2e",
                "bg_color": LT_BLUE, "num_format": "#,##0.000",
                "align": "right", "valign": "vcenter",
            }),
            "num_b": wb.add_format({
                "font_name": "Tahoma", "font_size": 10, "font_color": "#1a1a2e",
                "bg_color": LT_GREY, "num_format": "#,##0.000",
                "align": "right", "valign": "vcenter",
            }),
            "int_a": wb.add_format({
                "font_name": "Tahoma", "font_size": 10, "font_color": "#1a1a2e",
                "bg_color": LT_BLUE, "num_format": "#,##0",
                "align": "right", "valign": "vcenter",
            }),
            "int_b": wb.add_format({
                "font_name": "Tahoma", "font_size": 10, "font_color": "#1a1a2e",
                "bg_color": LT_GREY, "num_format": "#,##0",
                "align": "right", "valign": "vcenter",
            }),
            "err_val": wb.add_format({
                "font_name": "Tahoma", "font_size": 9, "bold": True,
                "font_color": "#c0392b", "bg_color": "#fce4e4",
                "align": "right",
            }),
            "fix_val": wb.add_format({
                "font_name": "Tahoma", "font_size": 9,
                "font_color": "#155724", "bg_color": "#d4edda",
                "align": "right",
            }),
            "ok_col": wb.add_format({
                "font_name": "Tahoma", "font_size": 10,
                "font_color": "#238636", "align": "right", "valign": "vcenter",
            }),
            "neg_col": wb.add_format({
                "font_name": "Tahoma", "font_size": 10, "bold": True,
                "font_color": "#da3633", "align": "right", "valign": "vcenter",
            }),
        }

    # ── Sheet factory ─────────────────────────────────────────────────────────

    def _add_sheet(self, name: str, tab_color: str = "") -> Worksheet:
        ws = self.wb.add_worksheet(name)
        if tab_color:
            ws.set_tab_color(f"#{tab_color}")
        ws.right_to_left()
        self._sheets_written.append(name)
        return ws

    # ── Core write_dataframe ──────────────────────────────────────────────────

    def _write_dataframe(
        self,
        ws: Worksheet,
        df: pl.DataFrame,
        hdr_fmt,
        start_row: int = 0,
        start_col: int = 0,
        num_col_set: set | None = None,
        special_cols: dict | None = None,
    ):
        """
        يكتب DataFrame في الـ worksheet باستخدام xlsxwriter.
        start_row/start_col: 0-indexed.
        num_col_set: أسماء أعمدة float/رقمية.
        special_cols: {col_name: (fmt_a, fmt_b)} لأعمدة تحتاج format خاص.

        استراتيجية الأداء:
          • write_row() للـ data rows بدون per-cell format → سريع جداً
          • conditional_format للـ banding (تلوين المتناوب) → Excel يحسبها عند الفتح
          • column number_format عبر set_column() → مرة واحدة لكل عمود
          • special_cols فقط بـ per-cell write (أعمدة الأخطاء والحالات)
        """
        num_col_set = num_col_set or set()
        special_cols = special_cols or {}
        headers = list(df.columns)
        n_cols = len(headers)
        n_rows = len(df)

        # Auto-detect float columns
        float_cols = {
            col for col, dtype in zip(df.columns, df.dtypes)
            if dtype in (pl.Float32, pl.Float64)
        }
        all_num = num_col_set | float_cols

        # ── Header row ────────────────────────────────────────────────────────
        # For pivot/small tables (start_col > 0), write header manually.
        # For main data sheets (start_col == 0), add_table() writes headers via columns dict.
        use_table = n_rows > 0 and start_col == 0
        if not use_table:
            for c, header in enumerate(headers, start=start_col):
                ws.write(start_row, c, header, hdr_fmt)
        ws.set_row(start_row, 18)

        # ── Data rows ─────────────────────────────────────────────────────────
        # FAST PATH: write_row() for raw values (no per-cell format)
        # Only special_cols get per-cell format (errors/status columns)
        # Identify special column indices vs normal
        for r, row_tuple in enumerate(df.iter_rows(), start=start_row + 1):
            ws.write_row(r, start_col, [
                "" if v is None else v for v in row_tuple
            ])

        # ── Excel Table (alternating colors + borders + filter) ───────────────
        # add_table() serializes much faster than per-cell or conditional_format banding.
        # NOTE: add_table() writes the header row itself via 'columns' definitions.
        if use_table:
            end_col_idx = start_col + n_cols - 1
            num_cell_fmt = self.wb.add_format({"num_format": "#,##0.000"})
            int_cell_fmt = self.wb.add_format({"num_format": "#,##0"})
            hdr_col_fmt  = self.wb.add_format({
                "bold": True, "bg_color": NAVY, "font_color": WHITE,
                "font_name": "Tahoma", "font_size": 11,
                "align": "right", "valign": "vcenter",
            })
            col_defs = []
            for col_name in headers:
                col_def: dict[str, Any] = {
                    "header": col_name,
                    "header_format": hdr_col_fmt,
                }
                if col_name in all_num:
                    col_def["format"] = num_cell_fmt
                elif col_name == "عدد أيام الإهمال":
                    col_def["format"] = int_cell_fmt
                
                # Apply special column formats directly to the table column definition
                if col_name in special_cols:
                    # special_cols now passes the format string name, e.g., "ok_col"
                    fmt_obj = special_cols[col_name]
                    if isinstance(fmt_obj, tuple):
                        # Backward compatibility if it still passes a tuple
                        pass
                    else:
                        col_def["format"] = fmt_obj

                col_defs.append(col_def)

            global _TABLE_COUNTER
            _TABLE_COUNTER += 1
            safe_name = f"Tbl_{_TABLE_COUNTER}"
            ws.add_table(
                start_row, start_col,
                start_row + n_rows, end_col_idx,
                {
                    "name": safe_name,
                    "style": "Table Style Medium 9",
                    "banded_rows": True,
                    "banded_columns": False,
                    "header_row": True,
                    "autofilter": True,
                    "columns": col_defs,
                }
            )

        # ── Column widths ──────────────────────────────────────────────────────
        sample = df.head(200)
        data_fmt = self.wb.add_format({
            "font_name": "Tahoma", "font_size": 10, "font_color": "#1a1a2e",
            "align": "right", "valign": "vcenter", "reading_order": 2,
        })
        num_fmt = self.wb.add_format({
            "font_name": "Tahoma", "font_size": 10, "font_color": "#1a1a2e",
            "num_format": "#,##0.000", "align": "right", "valign": "vcenter",
        })
        int_fmt = self.wb.add_format({
            "font_name": "Tahoma", "font_size": 10, "font_color": "#1a1a2e",
            "num_format": "#,##0", "align": "right", "valign": "vcenter",
        })
        for c, col_name in enumerate(headers, start=start_col):
            h_len = len(str(col_name))
            try:
                d_len = int(sample[col_name].cast(pl.String).str.len_chars().max() or 0)
            except Exception:
                d_len = 0
            width = min(45, max(12, h_len + 2, d_len + 2))
            if col_name in all_num:
                ws.set_column(c, c, width, num_fmt)
            elif col_name == "عدد أيام الإهمال":
                ws.set_column(c, c, width, int_fmt)
            else:
                ws.set_column(c, c, width, data_fmt)

        # ── Freeze panes ───────────────────────────────────────────────────────
        if start_row == 0 and start_col == 0:
            ws.freeze_panes(1, 0)



    # ── Public write methods ──────────────────────────────────────────────────

    def write_dashboard(self, all_stats: Dict[str, Any], task_id: int = 3):
        ws = self._add_sheet("Dashboard", TAB_COLORS["Dashboard"])
        wb = self.wb

        task_name = TASK_ARABIC_NAMES.get(task_id, "العمليات")

        # Title
        title_fmt = wb.add_format({
            "bold": True, "font_name": "Tahoma", "font_size": 15,
            "bg_color": NAVY, "font_color": "#FFFFFF",
            "align": "center", "valign": "vcenter",
        })
        ws.merge_range("A1:L1", f"🏢  نظام أتمتة العمليات — مهارة × STC  |  {task_name}", title_fmt)
        ws.set_row(0, 42)

        sub_fmt = wb.add_format({
            "font_name": "Tahoma", "font_size": 10, "font_color": "#8b949e",
            "bg_color": DARK_BG, "align": "center", "valign": "vcenter",
        })
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        ws.merge_range("A2:L2",
            f"تاريخ التقرير: {now_str}  |  المهمة: {task_id} — {task_name}", sub_fmt)
        ws.set_row(1, 22)

        # KPI Cards
        kpi_definitions = TASK_KPIS.get(task_id, TASK_KPIS[3])
        row_start = 3
        cards_per_row = 5

        for i, (label, stat_key, color) in enumerate(kpi_definitions):
            col = (i % cards_per_row) * 2
            r   = row_start + (i // cards_per_row) * 5
            value = all_stats.get(stat_key, 0)

            top_fmt = wb.add_format({"bg_color": f"#{color}"})
            ws.merge_range(r, col, r, col + 1, "", top_fmt)
            ws.set_row(r, 5)

            lbl_fmt = wb.add_format({
                "bold": True, "font_name": "Tahoma", "font_size": 9,
                "bg_color": CARD_BG, "font_color": f"#{color}",
                "align": "center", "valign": "vcenter",
            })
            ws.merge_range(r+1, col, r+1, col+1, label, lbl_fmt)
            ws.set_row(r+1, 18)

            val_fmt = wb.add_format({
                "bold": True, "font_name": "Tahoma", "font_size": 26,
                "bg_color": CARD_BG, "font_color": f"#{color}",
                "align": "center", "valign": "vcenter",
            })
            ws.merge_range(r+2, col, r+3, col+1, value, val_fmt)
            ws.set_row(r+2, 38)
            ws.set_row(r+3, 8)

        # Full Stats table
        rows_used = row_start + ((len(kpi_definitions) - 1) // cards_per_row + 1) * 5 + 2
        tbl_hdr_fmt = wb.add_format({
            "font_name": "Tahoma", "font_size": 11, "bold": True,
            "font_color": "#c9d1d9", "bg_color": "#21262d",
            "align": "right", "valign": "vcenter",
        })
        ws.merge_range(rows_used, 0, rows_used, 11, "📊  تفاصيل جميع المؤشرات", tbl_hdr_fmt)
        ws.set_row(rows_used, 22)
        rows_used += 1

        col_colors = [DARK_BG, CARD_BG]
        for idx, (k, v) in enumerate(all_stats.items()):
            bg = col_colors[idx % 2]
            k_fmt = wb.add_format({
                "font_name": "Tahoma", "font_size": 10,
                "font_color": "#c9d1d9", "bg_color": bg,
                "align": "right", "valign": "vcenter",
            })
            v_fmt = wb.add_format({
                "font_name": "Tahoma", "font_size": 10, "bold": True,
                "font_color": "#58a6ff", "bg_color": bg,
                "align": "center", "valign": "vcenter",
            })
            ws.merge_range(rows_used, 0, rows_used, 5, str(k), k_fmt)
            ws.merge_range(rows_used, 6, rows_used, 11, v, v_fmt)
            ws.set_row(rows_used, 18)
            rows_used += 1

        # Column widths
        for c in range(12):
            ws.set_column(c, c, 17)

        _log.info("✅ Dashboard sheet written (task %d — %s)", task_id, task_name)

    def write_summary(self, all_stats: Dict[str, Any]):
        ws = self._add_sheet("Summary", TAB_COLORS["Summary"])
        records = [{"المؤشر": str(k), "القيمة": str(v)} for k, v in all_stats.items()]
        df = pl.DataFrame(records) if records else pl.DataFrame({
            "المؤشر": pl.Series([], dtype=pl.String),
            "القيمة": pl.Series([], dtype=pl.String),
        })
        self._write_dataframe(ws, df, self._fmts["hdr_green"])
        _log.info("✅ Summary sheet written (%d KPIs)", len(all_stats))

    def write_errors(self, errors_data: pl.DataFrame):
        ws = self._add_sheet("اخطاء النظام", TAB_COLORS["اخطاء النظام"])
        special = {}
        if "الخطأ" in errors_data.columns:
            special["الخطأ"] = self._fmts["err_val"]
        if "تصحيح الخطأ" in errors_data.columns:
            special["تصحيح الخطأ"] = self._fmts["fix_val"]
        num_set = {"عدد العملاء"} & set(errors_data.columns)
        self._write_dataframe(ws, errors_data, self._fmts["hdr_red"],
                              num_col_set=num_set, special_cols=special)
        _log.info("✅ اخطاء النظام sheet written (%d rows)", len(errors_data))

    def write_contact(
        self,
        contact_data: pl.DataFrame,
        pivot_supervisor: pl.DataFrame,
        pivot_collector: pl.DataFrame,
        pivot_status: pl.DataFrame,
    ):
        ws = self._add_sheet("التوصل", TAB_COLORS["التوصل"])
        special = {}
        if "حالة التوصل" in contact_data.columns:
            # تلوين مشروط: تم التوصل=أخضر، لا يرد ومغلق=برتقالي، عدم التوصل=أحمر
            contact_col_idx = list(contact_data.columns).index("حالة التوصل")
            data_rows = len(contact_data)
            # أخضر = تم التوصل
            ws.conditional_format(1, contact_col_idx, data_rows, contact_col_idx, {
                "type": "text", "criteria": "containing", "value": "تم التوصل",
                "format": self.wb.add_format({"bg_color": "#d4edda", "font_color": "#155724", "bold": True}),
            })
            # برتقالي = لا يرد ومغلق
            ws.conditional_format(1, contact_col_idx, data_rows, contact_col_idx, {
                "type": "text", "criteria": "containing", "value": "لا يرد ومغلق",
                "format": self.wb.add_format({"bg_color": "#fff3cd", "font_color": "#856404", "bold": True}),
            })
            # أحمر = عدم التوصل
            ws.conditional_format(1, contact_col_idx, data_rows, contact_col_idx, {
                "type": "text", "criteria": "containing", "value": "عدم التوصل",
                "format": self.wb.add_format({"bg_color": "#f8d7da", "font_color": "#721c24", "bold": True}),
            })
        num_set = {"عدد العملاء"} & set(contact_data.columns)
        self._write_dataframe(ws, contact_data, self._fmts["hdr_green"],
                              num_col_set=num_set)
        # Pivot — supervisor
        if not pivot_supervisor.is_empty():
            sr = len(contact_data) + 3
            self._write_section_header(ws, "حسب المشرف", sr, GREEN)
            self._write_dataframe(ws, pivot_supervisor, self._fmts["hdr_green"],
                                  start_row=sr + 1)
        _log.info("✅ التوصل sheet written")

    def write_neglect(
        self,
        neglect_only: pl.DataFrame,
        full_analysis: pl.DataFrame,
        pivot_summary: pl.DataFrame,
        pivot_supervisor: pl.DataFrame,
        pivot_collector: pl.DataFrame,
        pivot_status: pl.DataFrame,
        pivot_branch: pl.DataFrame,
        pivot_portfolio: pl.DataFrame,
        pivot_days: pl.DataFrame,
    ):
        num_set = {"عدد العملاء"} & set(full_analysis.columns)
        status_col = "حالة الإهمال" if "حالة الإهمال" in full_analysis.columns else "حالة الاهمال"

        # ── Sheet 1: الإهمال (neglected only) ────────────────────────────────
        ws1 = self._add_sheet("الإهمال", TAB_COLORS["الإهمال"])
        special1 = {}
        if status_col in neglect_only.columns:
            special1[status_col] = self._fmts["neg_col"]
        self._write_dataframe(ws1, neglect_only, self._fmts["hdr_amber"],
                              num_col_set=num_set, special_cols=special1)

        # color scale for days column (manual gradient)
        if "عدد أيام الإهمال" in neglect_only.columns:
            c_idx = list(neglect_only.columns).index("عدد أيام الإهمال")
            ws1.conditional_format(1, c_idx, len(neglect_only), c_idx, {
                "type": "3_color_scale",
                "min_color": "#63BE7B",
                "mid_color": "#FFEB84",
                "max_color": "#F8696B",
            })

        # ── Sheet 2: تحليل الإهمال (all) ──────────────────────────────────────
        ws2 = self._add_sheet("تحليل الإهمال", "f39c12")
        special2 = {}
        if status_col in full_analysis.columns:
            special2[status_col] = self._fmts["neg_col"]
        self._write_dataframe(ws2, full_analysis, self._fmts["hdr_amber"],
                              num_col_set=num_set, special_cols=special2)

        # color scale for days in full sheet
        if "عدد أيام الإهمال" in full_analysis.columns:
            c_idx = list(full_analysis.columns).index("عدد أيام الإهمال")
            ws2.conditional_format(1, c_idx, len(full_analysis), c_idx, {
                "type": "3_color_scale",
                "min_color": "#63BE7B",
                "mid_color": "#FFEB84",
                "max_color": "#F8696B",
            })

        # Pivots below data in ws2
        cur = len(full_analysis) + 3
        for piv, title, color_key in [
            (pivot_summary,    "ملخص الإهمال",           "hdr_amber"),
            (pivot_supervisor, "حسب المشرف",             "hdr_amber"),
            (pivot_collector,  "حسب المحصل",             "hdr_navy"),
            (pivot_status,     "حسب الحالة الرئيسية",   "hdr_navy"),
            (pivot_branch,     "حسب الفرع",              "hdr_teal"),
            (pivot_portfolio,  "حسب المحفظة",            "hdr_purple"),
            (pivot_days,       "توزيع أيام الإهمال",     "hdr_amber"),
        ]:
            if piv is not None and not piv.is_empty():
                self._write_section_header(ws2, title, cur, AMBER)
                self._write_dataframe(ws2, piv, self._fmts[color_key], start_row=cur + 1)
                cur += len(piv) + 4

        _log.info("✅ الإهمال sheets written")

    def write_targets(
        self,
        targets_data: pl.DataFrame,
        pivot_supervisor: pl.DataFrame,
    ):
        target_col = "العملاء المستهدفة"
        num_set = {"عدد العملاء"} & set(targets_data.columns)
        special_all = {}
        if target_col in targets_data.columns:
            special_all[target_col] = self._fmts["ok_col"]

        # 1. First Sheet: ONLY targeted customers (Clean output for user)
        ws_targets = self._add_sheet("المستهدفين فقط", "2ecc71")
        only_targets = targets_data.filter(pl.col(target_col) == "مستهدف") if target_col in targets_data.columns else targets_data
        self._write_dataframe(ws_targets, only_targets, self._fmts["hdr_purple"],
                              num_col_set=num_set, special_cols=special_all)

        if not pivot_supervisor.is_empty():
            sr = len(only_targets) + 3
            self._write_section_header(ws_targets, "حسب المشرف", sr, PURPLE)
            self._write_dataframe(ws_targets, pivot_supervisor, self._fmts["hdr_purple"],
                                  start_row=sr + 1)

        # 2. Second Sheet: Full portfolio classification (No original rows deleted)
        ws_all = self._add_sheet("التصنيف الشامل", TAB_COLORS["العملاء المستهدفة"])
        self._write_dataframe(ws_all, targets_data, self._fmts["hdr_purple"],
                              num_col_set=num_set, special_cols=special_all)

        _log.info("✅ العملاء المستهدفة sheets written")

    def write_rotation(
        self,
        data: pl.DataFrame,
        execution: pl.DataFrame,
        dist_summary: pl.DataFrame,
        withdrawal_summary: pl.DataFrame,
    ):
        # 1. Sheet 1: ملخص السحب
        ws_sum = self._add_sheet("ملخص السحب", TAB_COLORS["ملخص السحب"])
        self._write_dataframe(ws_sum, withdrawal_summary, self._fmts["hdr_red"])

        # 2. Sheet 2: ملخص التوزيع
        ws_dist = self._add_sheet("ملخص التوزيع", TAB_COLORS["ملخص التوزيع"])
        num_set = {"عدد العملاء", "إجمالي متبقي السداد", "متوسط قيمة العميل"}
        self._write_dataframe(ws_dist, dist_summary, self._fmts["hdr_green"], num_col_set=num_set)

        # 3. Sheet 3: ملف التنفيذ
        ws_exec = self._add_sheet("ملف التنفيذ", TAB_COLORS["ملف التنفيذ"])
        self._write_dataframe(ws_exec, execution, self._fmts["hdr_amber"])

        # 4. Sheet 4: بيانات السحب والتدوير
        ws_data = self._add_sheet("بيانات السحب والتدوير", TAB_COLORS["بيانات السحب والتدوير"])
        num_cols = {"متبقي سداد موثق", "إجمالي العميل", "سنة التعثر"} & set(data.columns)
        self._write_dataframe(ws_data, data, self._fmts["hdr_blue"], num_col_set=num_cols)

        _log.info("✅ Rotation sheets written")

    def write_balancing(
        self,
        data: pl.DataFrame,
        summary_pivot: pl.DataFrame,
        planning_sheet: pl.DataFrame = None,
        source_summary: pl.DataFrame = None,
        final_result_sheet: pl.DataFrame = None,
    ):
        """Writes sheets for the Portfolio Balancing module (8)."""

        # 1. بيانات المحفظة (الشيت الأساسي الكامل دون أي تعديل بالصفوف)
        ws_data = self._add_sheet("بيانات المحفظة", TAB_COLORS.get("بيانات المحفظة", "1f6feb"))
        num_set_data = {
            "متبقي سداد موثق", "إجمالي مديونيات العميل", "سنة التعثر",
            "متبقي السداد الموثق", "الرصيد المتبقي",
        } & set(data.columns)
        self._write_dataframe(ws_data, data, self._fmts["hdr_blue"], num_col_set=num_set_data)

        # 2. ملخص التوزيع (قبل / بعد لكل محصل في المحافظ الهدف)
        ws_sum = self._add_sheet("ملخص التوزيع", TAB_COLORS.get("ملخص التوزيع", "2ecc71"))
        num_set_sum = {"عدد العملاء", "إجمالي متبقي السداد"}
        self._write_dataframe(ws_sum, summary_pivot, self._fmts["hdr_green"], num_col_set=num_set_sum)

        # 3. ملخص المحفظة المصدر
        if source_summary is not None and not source_summary.is_empty():
            ws_src = self._add_sheet("ملخص المحفظة المصدر", "e74c3c")
            self._write_dataframe(ws_src, source_summary, self._fmts["hdr_red"])

        # 3.5. نتيجة التوزيع (العدد الفعلي النهائي لكل محصل)
        if final_result_sheet is not None and not final_result_sheet.is_empty():
            ws_res = self._add_sheet("نتيجة التوزيع", "9b59b6")
            num_set_res = {"عدد العملاء النهائي", "إجمالي متبقي سداد موثق"}
            self._write_dataframe(ws_res, final_result_sheet, self._fmts["hdr_purple"], num_col_set=num_set_res)

        # 4. خطة التوازن (إذا كانت متوفرة)
        if planning_sheet is not None and not planning_sheet.is_empty():
            ws_plan = self._add_sheet("خطة التوازن", TAB_COLORS.get("خطة التوازن", "e74c3c"))
            num_set_plan = {
                "العملاء الحاليون",
                "إجمالي السداد الحالي",
                "المتوسط المثالي",
                "الفائض/النقص",
                "كام نسحب",
                "كام يستقبل",
                "العملاء بعد",
                "إجمالي السداد بعد",
            }
            self._write_dataframe(ws_plan, planning_sheet, self._fmts["hdr_amber"], num_col_set=num_set_plan)
            _log.info("Balancing sheets written (4 sheets)")
        else:
            _log.info("Balancing sheets written (3 sheets)")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _write_section_header(self, ws: Worksheet, title: str, row: int, color: str):
        """Writes a merged section title row."""
        fmt = self.wb.add_format({
            "bold": True, "font_name": "Tahoma", "font_size": 12,
            "bg_color": color, "font_color": WHITE,
            "align": "right", "valign": "vcenter",
        })
        ws.merge_range(row, 0, row, 10, f"  {title}", fmt)
        ws.set_row(row, 20)

    
    def write_operations_report(
        self,
        report_table: pl.DataFrame,
        data: pl.DataFrame = None,
        stats: dict = None,
        *args, **kwargs
    ):
        rep_title  = stats.get("نوع التقرير", "📊 تقرير العمليات") if stats else "📊 تقرير العمليات"
        rep_period = stats.get("الفترة الزمنية", "") if stats else ""

        # ── Sheet 1: تقرير العمليات التنفيذي (The exact 8-column table) ──────
        ws = self._add_sheet("تقرير العمليات", "1E3A8A")

        # 1. ترويسة التقرير
        hdr_banner_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 14,
            "bg_color": "#1E3A8A", "font_color": "#FFFFFF",
            "align": "center", "valign": "vcenter"
        })
        ws.merge_range("A1:H1", f"🏢 {rep_title} — {rep_period}", hdr_banner_fmt)
        ws.set_row(0, 32)

        # 2. كروت المؤشرات السريعة
        card_lbl_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 9,
            "bg_color": "#F0F7FF", "font_color": "#1E40AF",
            "border": 1, "border_color": "#BFDBFE",
            "align": "center", "valign": "vcenter"
        })
        card_val_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 12,
            "bg_color": "#FFFFFF", "font_color": "#1E3A8A",
            "border": 1, "border_color": "#BFDBFE",
            "align": "center", "valign": "vcenter"
        })

        if stats:
            kpis = [
                ("إجمالي التغطية", stats.get("إجمالي التغطية الفعلية", "-")),
                ("مستهدف التغطية", stats.get("مستهدف التغطية الكلي", "-")),
                ("نسبة التغطية الكلية", stats.get("نسبة التغطية الكلية", "-")),
                ("إجمالي التحصيل الفعلي", stats.get("إجمالي التحصيل الفعلي", "-")),
                ("مستهدف التحصيل الكلي", stats.get("مستهدف التحصيل الكلي", "-")),
                ("نسبة التحصيل الكلية", stats.get("نسبة التحصيل الكلية", "-")),
            ]
            c_pos = 0
            for lbl, val in kpis:
                if c_pos < 8:
                    ws.write(2, c_pos, lbl, card_lbl_fmt)
                    ws.write(3, c_pos, val, card_val_fmt)
                    c_pos += 1
            ws.set_row(2, 20)
            ws.set_row(3, 24)

        # 3. جدول العمليات الرئيسي (الأعمدة الثمانية)
        tbl_hdr_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 11,
            "bg_color": "#1E3A8A", "font_color": "#FFFFFF",
            "border": 1, "border_color": "#93C5FD",
            "align": "center", "valign": "vcenter"
        })
        row_normal_fmt = self.wb.add_format({
            "font_name": "Segoe UI", "font_size": 10,
            "font_color": "#0F172A", "bg_color": "#FFFFFF",
            "border": 1, "border_color": "#E2E8F0",
            "align": "center", "valign": "vcenter"
        })
        row_alt_fmt = self.wb.add_format({
            "font_name": "Segoe UI", "font_size": 10,
            "font_color": "#0F172A", "bg_color": "#F8FAFC",
            "border": 1, "border_color": "#E2E8F0",
            "align": "center", "valign": "vcenter"
        })
        row_subtotal_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 10,
            "font_color": "#1E3A8A", "bg_color": "#E0F2FE",
            "border": 1, "border_color": "#93C5FD",
            "align": "center", "valign": "vcenter"
        })
        row_grand_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 11,
            "font_color": "#FFFFFF", "bg_color": "#1E3A8A",
            "border": 2, "border_color": "#3B82F6",
            "align": "center", "valign": "vcenter"
        })

        # تنسيقات الأرقام والنسب
        pct_normal_fmt = self.wb.add_format({
            "font_name": "Segoe UI", "font_size": 10, "font_color": "#0F172A",
            "bg_color": "#FFFFFF", "border": 1, "border_color": "#E2E8F0",
            "align": "center", "valign": "vcenter", "num_format": "0.0%"
        })
        pct_subtotal_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 10, "font_color": "#1E3A8A",
            "bg_color": "#E0F2FE", "border": 1, "border_color": "#93C5FD",
            "align": "center", "valign": "vcenter", "num_format": "0.0%"
        })
        pct_grand_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 11, "font_color": "#FFFFFF",
            "bg_color": "#1E3A8A", "border": 2, "border_color": "#3B82F6",
            "align": "center", "valign": "vcenter", "num_format": "0.0%"
        })

        num_normal_fmt = self.wb.add_format({
            "font_name": "Segoe UI", "font_size": 10, "font_color": "#0F172A",
            "bg_color": "#FFFFFF", "border": 1, "border_color": "#E2E8F0",
            "align": "center", "valign": "vcenter", "num_format": "#,##0.00"
        })
        num_subtotal_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 10, "font_color": "#1E3A8A",
            "bg_color": "#E0F2FE", "border": 1, "border_color": "#93C5FD",
            "align": "center", "valign": "vcenter", "num_format": "#,##0.00"
        })
        num_grand_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 11, "font_color": "#FFFFFF",
            "bg_color": "#1E3A8A", "border": 2, "border_color": "#3B82F6",
            "align": "center", "valign": "vcenter", "num_format": "#,##0.00"
        })

        target_columns = [
            "المشرف", "المحصل", "التغطية", "مستهدف التغطية",
            "نسبة التغطية %", "التحصيل", "مستهدف التحصيل", "نسبة التحصيل %"
        ]

        start_r = 5
        ws.set_row(start_r, 26)
        for col_idx, col_name in enumerate(target_columns):
            ws.write(start_r, col_idx, col_name, tbl_hdr_fmt)
            ws.set_column(col_idx, col_idx, 18)

        if report_table is not None and not report_table.is_empty():
            clean_tbl = report_table.select([c for c in report_table.columns if not c.startswith("_")])
            for r_idx, row in enumerate(clean_tbl.iter_rows(named=True)):
                cur_row_idx = start_r + 1 + r_idx
                sup_text = str(row.get("المشرف", ""))
                is_grand = "الإجمالي العام" in sup_text
                is_sub   = "إجمالي مشرف" in sup_text

                if is_grand:
                    ws.set_row(cur_row_idx, 24)
                elif is_sub:
                    ws.set_row(cur_row_idx, 22)
                else:
                    ws.set_row(cur_row_idx, 20)

                for c_idx, col_name in enumerate(target_columns):
                    val = row.get(col_name)
                    # اختيار التنسيق المناسب
                    if is_grand:
                        if "%" in col_name:
                            f = pct_grand_fmt
                            val = (val / 100.0) if (val is not None and isinstance(val, (int, float))) else val
                        elif col_name in ("التحصيل", "مستهدف التحصيل"):
                            f = num_grand_fmt
                        else:
                            f = row_grand_fmt
                    elif is_sub:
                        if "%" in col_name:
                            f = pct_subtotal_fmt
                            val = (val / 100.0) if (val is not None and isinstance(val, (int, float))) else val
                        elif col_name in ("التحصيل", "مستهدف التحصيل"):
                            f = num_subtotal_fmt
                        else:
                            f = row_subtotal_fmt
                    else:
                        base_f = row_alt_fmt if (r_idx % 2 == 1) else row_normal_fmt
                        if "%" in col_name:
                            f = pct_normal_fmt
                            val = (val / 100.0) if (val is not None and isinstance(val, (int, float))) else val
                        elif col_name in ("التحصيل", "مستهدف التحصيل"):
                            f = num_normal_fmt
                        else:
                            f = base_f

                    ws.write(cur_row_idx, c_idx, val, f)

        self._sheets_written.append("Operations Report")

    def write_electronic_collection(
        self,
        data,
        pivot_supervisor,
        pivot_collector,
        pivot_segment,
        stats = None
    ):
        rep_title = "📊 تقرير التحصيل الإلكتروني"
        rep_period = stats.get("تاريخ التقرير", "") if stats else ""
        mode = stats.get("report_mode", "task1_contact") if stats else "task1_contact"

        # ── Sheet 1: البيانات الأصلية ────────────────────────
        ws1 = self._add_sheet("البيانات الأصلية", "2980b9")
        self._write_section_header(ws1, f"📄 {rep_title} - {rep_period}", 0, NAVY)
        self._write_dataframe(ws1, data, self._fmts["hdr_blue"], start_row=2)

        # ── Sheet 2: الملخص التنفيذي ────────────────────────
        ws2 = self._add_sheet("الملخص التنفيذي", "27ae60")
        self._write_section_header(ws2, f"📋 الملخص التنفيذي - {rep_title} ({rep_period})", 0, GREEN)
        r_idx = 3
        if stats:
            mode = stats.get("report_mode", "task1_contact")
            card_fmt = self.wb.add_format({
                "bold": True, "font_name": "Tahoma", "font_size": 11,
                "bg_color": "#e8f8f5", "font_color": "#117a65",
                "border": 1, "border_color": "#a3e4d7", "align": "center", "valign": "vcenter"
            })
            val_fmt = self.wb.add_format({
                "bold": True, "font_name": "Tahoma", "font_size": 12,
                "bg_color": "#ffffff", "font_color": "#196f3d",
                "border": 1, "border_color": "#a3e4d7", "align": "center", "valign": "vcenter"
            })
            
            # Filter stats per task
            clean_stats = {}
            for k, v in stats.items():
                if k == "report_mode":
                    continue
                if mode == "task1_contact" and ("تغطية" in k or "مغطين" in k):
                    continue
                if mode == "task2_coverage" and ("توصل" in k and "نسبة التغطية" not in k):
                    continue
                clean_stats[k] = v

            c_idx = 0
            for k, v in clean_stats.items():
                ws2.merge_range(r_idx, c_idx, r_idx, c_idx + 1, k, card_fmt)
                ws2.merge_range(r_idx + 1, c_idx, r_idx + 1, c_idx + 1, str(v), val_fmt)
                c_idx += 3
                if c_idx >= 12:
                    c_idx = 0
                    r_idx += 3
            r_idx += 4

        if pivot_supervisor is not None and not pivot_supervisor.is_empty():
            import polars as pl
            mode = stats.get("report_mode", "task1_contact") if stats else "task1_contact"
            
            if mode == "task1_contact":
                display_cols = ["المشرف", "عدد العملاء", "توصل", "نسبة التوصل %", "عدم توصل", "نسبة عدم التوصل %", "لايرد-مغلق", "نسبة لايرد ومغلق %"]
                header_title = "📋 جدول ملخص حالات التواصل والنسب للإدارة"
            elif mode == "task2_coverage":
                display_cols = ["المشرف", "عدد العملاء", "العملاء المغطين", "نسبة التغطية %", "غير المغطين", "نسبة عدم التغطية %"]
                header_title = "📋 جدول ملخص نسبة التغطية والنسب للإدارة"
            else:
                display_cols = ["المشرف", "عدد العملاء", "العملاء المغطين", "نسبة التغطية %", "توصل", "نسبة التوصل %"]
                header_title = "📋 جدول الملخص التنفيذي الشامل للإدارة"
                
            cols_to_show = [c for c in display_cols if c in pivot_supervisor.columns]
            if cols_to_show:
                show_df = pivot_supervisor.select(cols_to_show)
                show_df = show_df.filter(~pl.col("المشرف").cast(pl.String).str.contains("الإجمالي|📉|📈"))
                self._write_section_header(ws2, header_title, r_idx, GREEN)
                self._write_dataframe(ws2, show_df, self._fmts["hdr_green"], start_row=r_idx + 1)
                r_idx += len(show_df) + 4

        if mode == "task3_comprehensive" and pivot_segment is not None and not pivot_segment.is_empty():
            self._write_section_header(ws2, "🧩 ملخص القطاعات (Segment) ونوع الخدمة الموثقة", r_idx, GREEN)
            self._write_dataframe(ws2, pivot_segment, self._fmts["hdr_teal"], start_row=r_idx + 1)

        # ── Sheet 3: الجداول المحورية المخصصة للتاسك ───────
        sheet3_name = "نتائج التواصل والنسب" if mode == "task1_contact" else ("نتائج التغطية والنسب" if mode == "task2_coverage" else "التقرير المحوري الشامل")
        ws3 = self._add_sheet(sheet3_name, "8e44ad")
        self._write_section_header(ws3, f"📊 جداول {sheet3_name} - {rep_period}", 0, PURPLE)
        cur_row = 3
        
        pivots_list = [
            (pivot_supervisor, "📊 التخصيص حسب المشرف", "hdr_purple"),
            (pivot_collector,  "👤 التخصيص حسب المحصل", "hdr_navy"),
        ]
        if mode == "task3_comprehensive":
            pivots_list.append((pivot_segment, "🧩 تحليل حسب القطاع (Segment)", "hdr_teal"))

        for piv, title, color_key in pivots_list:
            if piv is not None and not piv.is_empty():
                if mode == "task1_contact":
                    target_cols = ["المشرف", "المحصل", "عدد العملاء", "توصل", "نسبة التوصل %", "عدم توصل", "نسبة عدم التوصل %", "لايرد-مغلق", "نسبة لايرد ومغلق %"]
                elif mode == "task2_coverage":
                    target_cols = ["المشرف", "المحصل", "عدد العملاء", "العملاء المغطين", "نسبة التغطية %", "غير المغطين", "نسبة عدم التغطية %"]
                else:
                    target_cols = piv.columns
                
                show_piv = piv.select([c for c in target_cols if c in piv.columns])
                self._write_section_header(ws3, title, cur_row, PURPLE)
                self._write_dataframe(ws3, show_piv, self._fmts[color_key], start_row=cur_row + 1)
                cur_row += len(show_piv) + 4
        
        self._sheets_written.append("Electronic Collection")
        import logging
        logging.info("✅ Electronic Collection sheets written (%s)", rep_title)

    def write_targeting_report(self, df: pl.DataFrame, stats: dict = None):
        """تصدير شيت تقرير الاستهداف بنفس تنسيق الأكسيل الخاص بالمستخدم"""
        ws = self._add_sheet("تقرير الاستهداف", "800000")
        
        # Header formatting
        hdr_fmt = self.wb.add_format({
            "bold": True, "font_name": "Tahoma", "font_size": 11,
            "bg_color": "#4a3b32", "font_color": "#ffffff",
            "border": 1, "border_color": "#333333",
            "align": "center", "valign": "vcenter"
        })
        
        data_fmt = self.wb.add_format({
            "font_name": "Tahoma", "font_size": 10,
            "border": 1, "border_color": "#d9d9d9",
            "align": "center", "valign": "vcenter"
        })
        
        total_fmt = self.wb.add_format({
            "bold": True, "font_name": "Tahoma", "font_size": 11,
            "bg_color": "#800000", "font_color": "#ffffff",
            "border": 1, "border_color": "#333333",
            "align": "center", "valign": "vcenter"
        })
        
        cols = df.columns
        for c_idx, col in enumerate(cols):
            ws.write(0, c_idx, col, hdr_fmt)
            ws.set_column(c_idx, c_idx, 16)
        
        for r_idx, row in enumerate(df.iter_rows(named=True)):
            is_total = "إجمالي" in str(row.get("المشرف", "")) or "الإجمالي" in str(row.get("المشرف", ""))
            curr_fmt = total_fmt if is_total else data_fmt
            for c_idx, col in enumerate(cols):
                val = row[col]
                ws.write(r_idx + 1, c_idx, val, curr_fmt)

        _log.info("✅ Targeting report sheet written (%d rows)", len(df))

    def write_monthly_targets_report(
        self,
        report_table: pl.DataFrame,
        months_meta: list = None,
        stats: dict = None,
    ):
        """تصدير تقرير التحصيل بالشهور بالمستهدف بتنسيق تنفيذي متكامل"""
        ws = self._add_sheet("التحصيل بالشهور", "1E3A8A")

        # 1. ترويسة رئيسية
        hdr_banner_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 14,
            "bg_color": "#1E3A8A", "font_color": "#FFFFFF",
            "align": "center", "valign": "vcenter"
        })
        n_cols = len([c for c in report_table.columns if not c.startswith("_")])
        last_col_idx = max(n_cols - 1, 7)
        ws.merge_range(0, 0, 0, last_col_idx, "📅 تقرير التحصيل بالشهور بالمستهدف — مقارنة الأداء الفعلي ونسب الإنجاز", hdr_banner_fmt)
        ws.set_row(0, 32)

        # 2. كروت المؤشرات السريعة
        card_lbl_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 9,
            "bg_color": "#F0F7FF", "font_color": "#1E40AF",
            "border": 1, "border_color": "#BFDBFE",
            "align": "center", "valign": "vcenter"
        })
        card_val_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 12,
            "bg_color": "#FFFFFF", "font_color": "#1E3A8A",
            "border": 1, "border_color": "#BFDBFE",
            "align": "center", "valign": "vcenter"
        })

        if stats:
            kpis = [
                ("عدد الشهور", str(stats.get("عدد الشهور المشمولة", "-"))),
                ("إجمالي التحصيل", stats.get("إجمالي التحصيل الفعلي", "-")),
                ("إجمالي المستهدف", stats.get("إجمالي المستهدف الكلي", "-")),
                ("نسبة الإنجاز الكلية", stats.get("نسبة الإنجاز الإجمالية", "-")),
            ]
            c_pos = 0
            for lbl, val in kpis:
                if c_pos <= last_col_idx:
                    ws.write(2, c_pos, lbl, card_lbl_fmt)
                    ws.write(3, c_pos, val, card_val_fmt)
                    c_pos += 1
            ws.set_row(2, 20)
            ws.set_row(3, 24)

        # 3. جدول البيانات
        tbl_hdr_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 10,
            "bg_color": "#1E3A8A", "font_color": "#FFFFFF",
            "border": 1, "border_color": "#93C5FD",
            "align": "center", "valign": "vcenter"
        })
        row_normal_fmt = self.wb.add_format({
            "font_name": "Segoe UI", "font_size": 10,
            "font_color": "#0F172A", "bg_color": "#FFFFFF",
            "border": 1, "border_color": "#E2E8F0",
            "align": "center", "valign": "vcenter"
        })
        row_alt_fmt = self.wb.add_format({
            "font_name": "Segoe UI", "font_size": 10,
            "font_color": "#0F172A", "bg_color": "#F8FAFC",
            "border": 1, "border_color": "#E2E8F0",
            "align": "center", "valign": "vcenter"
        })
        row_subtotal_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 10,
            "font_color": "#1E3A8A", "bg_color": "#E0F2FE",
            "border": 1, "border_color": "#93C5FD",
            "align": "center", "valign": "vcenter"
        })
        row_grand_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 11,
            "font_color": "#FFFFFF", "bg_color": "#1E3A8A",
            "border": 2, "border_color": "#3B82F6",
            "align": "center", "valign": "vcenter"
        })

        pct_normal_fmt = self.wb.add_format({
            "font_name": "Segoe UI", "font_size": 10, "font_color": "#0F172A",
            "bg_color": "#FFFFFF", "border": 1, "border_color": "#E2E8F0",
            "align": "center", "valign": "vcenter", "num_format": "0.0%"
        })
        pct_subtotal_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 10, "font_color": "#1E3A8A",
            "bg_color": "#E0F2FE", "border": 1, "border_color": "#93C5FD",
            "align": "center", "valign": "vcenter", "num_format": "0.0%"
        })
        pct_grand_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 11, "font_color": "#FFFFFF",
            "bg_color": "#1E3A8A", "border": 2, "border_color": "#3B82F6",
            "align": "center", "valign": "vcenter", "num_format": "0.0%"
        })

        num_normal_fmt = self.wb.add_format({
            "font_name": "Segoe UI", "font_size": 10, "font_color": "#0F172A",
            "bg_color": "#FFFFFF", "border": 1, "border_color": "#E2E8F0",
            "align": "center", "valign": "vcenter", "num_format": "#,##0.00"
        })
        num_subtotal_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 10, "font_color": "#1E3A8A",
            "bg_color": "#E0F2FE", "border": 1, "border_color": "#93C5FD",
            "align": "center", "valign": "vcenter", "num_format": "#,##0.00"
        })
        num_grand_fmt = self.wb.add_format({
            "bold": True, "font_name": "Segoe UI", "font_size": 11, "font_color": "#FFFFFF",
            "bg_color": "#1E3A8A", "border": 2, "border_color": "#3B82F6",
            "align": "center", "valign": "vcenter", "num_format": "#,##0.00"
        })

        start_r = 5
        clean_cols = [c for c in report_table.columns if not c.startswith("_")]
        ws.set_row(start_r, 26)
        for col_idx, col_name in enumerate(clean_cols):
            ws.write(start_r, col_idx, col_name, tbl_hdr_fmt)
            ws.set_column(col_idx, col_idx, 16)

        for r_idx, row in enumerate(report_table.iter_rows(named=True)):
            cur_r = start_r + 1 + r_idx
            sup_str = str(row.get("المشرف", ""))
            is_grand = "الإجمالي العام" in sup_str
            is_sub   = "إجمالي مشرف" in sup_str

            if is_grand:
                ws.set_row(cur_r, 24)
            elif is_sub:
                ws.set_row(cur_r, 22)
            else:
                ws.set_row(cur_r, 20)

            for c_idx, col_name in enumerate(clean_cols):
                val = row.get(col_name)
                is_pct = "%" in col_name
                is_curr = ("تحصيل" in col_name or "مستهدف" in col_name) and not is_pct

                if is_grand:
                    if is_pct:
                        f = pct_grand_fmt
                        val = (val / 100.0) if (val is not None and isinstance(val, (int, float))) else val
                    elif is_curr:
                        f = num_grand_fmt
                    else:
                        f = row_grand_fmt
                elif is_sub:
                    if is_pct:
                        f = pct_subtotal_fmt
                        val = (val / 100.0) if (val is not None and isinstance(val, (int, float))) else val
                    elif is_curr:
                        f = num_subtotal_fmt
                    else:
                        f = row_subtotal_fmt
                else:
                    base_f = row_alt_fmt if (r_idx % 2 == 1) else row_normal_fmt
                    if is_pct:
                        f = pct_normal_fmt
                        val = (val / 100.0) if (val is not None and isinstance(val, (int, float))) else val
                    elif is_curr:
                        f = num_normal_fmt
                    else:
                        f = base_f

                ws.write(cur_r, c_idx, val, f)

        self._sheets_written.append("Monthly Targets Report")
        _log.info("✅ Monthly targets report sheet written (%d rows)", len(report_table))

    def save(self):
        self.wb.close()
        import logging
        logging.info("💾 Workbook saved → %s", self.output_path)
