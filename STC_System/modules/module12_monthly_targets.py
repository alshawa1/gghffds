# -*- coding: utf-8 -*-
"""
modules/module12_monthly_targets.py
───────────────────────────────────
تقرير التحصيل بالشهور بالمستهدف (Monthly Collections vs Targets Report):
- الربط بين ملف المحفظة وملف السدادات برقم المديونية [رقم المديونية]
- استخراج الشهور من عمود [تاريخ السداد] في شيت السدادات
- حساب التحصيل الفعلي لكل محصل ومشرف لكل شهر على حدة
- مقارنة التحصيل الفعلي بمستهدف كل شهر واحتساب نسبة الإنجاز %
- تجميع إجماليات لكل مشرف والإجمالي العام
- الأعمدة الناتجة ديناميكياً حسب الشهور المختارة:
  المشرف | المحصل | تحصيل شهر X | مستهدف شهر X | نسبة شهر X % | تحصيل شهر Y | مستهدف شهر Y | نسبة شهر Y % | ... | إجمالي التحصيل | إجمالي المستهدف | نسبة الإنجاز الكلية %
"""

from __future__ import annotations
import logging
import re
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
import polars as pl

_log = logging.getLogger("STC_MONTHLY_TARGETS")

_DEBT_COLS          = ["رقم المديونية", "رقم المديونيه", "رقم العقد", "رقم الحساب", "المديونية", "debt_id", "Debt ID"]
_ID_COLS            = ["رقم الهوية", "الهوية", "هوية العميل", "السجل المدني", "ID", "customer_id"]
_SUPERVISOR_COLS     = ["المشرف", "اسم المشرف", "supervisor", "Supervisor"]
_COLLECTOR_COLS      = ["المحصل", "اسم المحصل", "الموظف", "محصل", "collector", "Collector"]
_PAYMENT_AMOUNT_COLS = ["مبلغ السداد", "قيمة السداد", "المبلغ", "amount", "Amount", "paid_amount", "السدادات الموثقة"]
_PAYMENT_DATE_COLS   = ["تاريخ السداد", "تاريخ الدفع", "تاريخ الحركة", "تاريخ العملية", "التاريخ", "date", "Date", "payment_date"]

MONTH_NAMES_AR = {
    1: "يناير (شهر 1)",
    2: "فبراير (شهر 2)",
    3: "مارس (شهر 3)",
    4: "أبريل (شهر 4)",
    5: "مايو (شهر 5)",
    6: "يونيو (شهر 6)",
    7: "يوليو (شهر 7)",
    8: "أغسطس (شهر 8)",
    9: "سبتمبر (شهر 9)",
    10: "أكتوبر (شهر 10)",
    11: "نوفمبر (شهر 11)",
    12: "ديسمبر (شهر 12)",
}


def _detect(df: pl.DataFrame, candidates: List[str]) -> Optional[str]:
    if df is None or len(df.columns) == 0:
        return None
    for c in candidates:
        if c in df.columns:
            return c
    for c in df.columns:
        for cand in candidates:
            if cand.strip().lower() in c.strip().lower() or c.strip().lower() in cand.strip().lower():
                return c
    return None


_RE_US_DATE  = re.compile(r"^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})")
_RE_ISO_DATE = re.compile(r"^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})")


def _extract_year_month(val: Any) -> Optional[Tuple[int, int]]:
    """يستخرج (السنة, الشهر) من أي صيغة تاريخ."""
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return (val.year, val.month)
    v = str(val).strip()
    if not v or v in ("-", "None", "null", "nan"):
        return None

    m2 = _RE_ISO_DATE.match(v)
    if m2:
        return (int(m2.group(1)), int(m2.group(2)))

    m = _RE_US_DATE.match(v)
    if m:
        p1, p2, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if p1 > 12:
            return (y, p2)
        elif p2 > 12:
            return (y, p1)
        else:
            return (y, p2)  # DD/MM/YYYY

    return None


class MonthlyTargetsModule:
    """
    محرك تقرير التحصيل بالشهور بالمستهدف:
    يربط المحفظة بالسدادات برقم المديونية، ويوزع المبالغ على الشهور ويقارنها بالمستهدفات.
    """

    @staticmethod
    def detect_available_months(payments: pl.DataFrame) -> List[Dict[str, Any]]:
        """
        فحص ملف السدادات لاكتشاف جميع الشهور المتاحة في عمود تاريخ السداد.
        يُرجع قائمة بالشهور المكتشفة مرتبة: [{'key': '2026-07', 'year': 2026, 'month': 7, 'label': 'شهر 7 (يوليو 2026)', 'count': 1500}, ...]
        """
        if payments is None or len(payments) == 0:
            return []

        dt_col = _detect(payments, _PAYMENT_DATE_COLS)
        if not dt_col:
            # افتراض الشهر الحالي إذا لم يوجد عمود تاريخ
            curr = date.today()
            return [{
                "key": f"{curr.year:04d}-{curr.month:02d}",
                "year": curr.year,
                "month": curr.month,
                "label": f"شهر {curr.month} ({MONTH_NAMES_AR.get(curr.month, '')})",
                "count": len(payments)
            }]

        month_counts: Dict[Tuple[int, int], int] = {}
        for val in payments[dt_col].to_list():
            ym = _extract_year_month(val)
            if ym:
                month_counts[ym] = month_counts.get(ym, 0) + 1

        results = []
        for (y, m) in sorted(month_counts.keys()):
            key_str = f"{y:04d}-{m:02d}"
            label_str = f"شهر {m} ({MONTH_NAMES_AR.get(m, f'شهر {m}')} {y})"
            results.append({
                "key": key_str,
                "year": y,
                "month": m,
                "label": label_str,
                "count": month_counts[(y, m)]
            })

        return results

    def run(
        self,
        portfolio: pl.DataFrame,
        payments: pl.DataFrame,
        selected_months: List[str],  # قائمة المفاتيح المختارة مثلاً: ["2026-07", "2026-08"] أو أرقام الشهور
        monthly_targets: Dict[str, float],  # {key: target_amount}
        supervisors: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:

        if portfolio is None or len(portfolio) == 0:
            raise ValueError("ملف المحفظة فارغ أو لم يتم رفعه!")
        if payments is None or len(payments) == 0:
            raise ValueError("ملف التحصيل / السدادات فارغ أو لم يتم رفعه!")
        if not selected_months:
            raise ValueError("يرجى اختيار شهر واحد على الأقل لإنشاء التقرير!")

        # 1. كشف الأعمدة الحيوية في المحفظة
        port_debt_col = _detect(portfolio, _DEBT_COLS) or _detect(portfolio, _ID_COLS) or portfolio.columns[0]
        sup_col       = _detect(portfolio, _SUPERVISOR_COLS)
        col_col       = _detect(portfolio, _COLLECTOR_COLS)

        if not col_col:
            raise ValueError("لم يتم العثور على عمود المحصل في ملف المحفظة!")

        # 2. كشف الأعمدة في السدادات
        pmt_debt_col = _detect(payments, _DEBT_COLS) or _detect(payments, _ID_COLS)
        pmt_amt_col  = _detect(payments, _PAYMENT_AMOUNT_COLS)
        pmt_dt_col   = _detect(payments, _PAYMENT_DATE_COLS)

        if not pmt_debt_col:
            raise ValueError("لم يتم العثور على عمود رقم المديونية في ملف السدادات!")
        if not pmt_amt_col:
            raise ValueError("لم يتم العثور على عمود مبلغ السداد في ملف السدادات!")

        df_p = portfolio.clone()

        # تصفية المحفظة حسب المشرفين إن تم تحديدهم
        if supervisors and sup_col and sup_col in df_p.columns:
            df_p = df_p.filter(pl.col(sup_col).cast(pl.String).str.strip_chars().is_in(supervisors))

        if len(df_p) == 0:
            raise ValueError("لا توجد سجلات مطابقة للمشرفين المحددين في المحفظة!")

        # تنظيف رقم المديونية في المحفظة
        df_p = df_p.with_columns(
            pl.col(port_debt_col).cast(pl.String).str.replace(r"\.0$", "", literal=False).str.strip_chars().alias("_clean_debt_id")
        )

        # 3. معالجة وتصنيف السدادات حسب الشهور المختارة برقم المديونية
        pmt_clean = payments.with_columns([
            pl.col(pmt_debt_col).cast(pl.String).str.replace(r"\.0$", "", literal=False).str.strip_chars().alias("_pmt_debt_clean"),
            pl.col(pmt_amt_col).cast(pl.String).str.replace_all(",", "", literal=True).str.replace_all(r"[^\d\.-]", "", literal=False).cast(pl.Float64, strict=False).fill_null(0.0).alias("_pmt_amt_clean")
        ])

        # استخراج الشهر لكل حركة سداد
        if pmt_dt_col and pmt_dt_col in pmt_clean.columns:
            raw_dates = pmt_clean[pmt_dt_col].to_list()
            month_keys = []
            for d in raw_dates:
                ym = _extract_year_month(d)
                if ym:
                    month_keys.append(f"{ym[0]:04d}-{ym[1]:02d}")
                else:
                    month_keys.append("unknown")
            pmt_clean = pmt_clean.with_columns(pl.Series("_pmt_month_key", month_keys))
        else:
            # إذا لم يوجد تاريخ، نعتبر كل السدادات تابعة للشهر الأول المختار
            first_m = selected_months[0]
            pmt_clean = pmt_clean.with_columns(pl.lit(first_m).alias("_pmt_month_key"))

        # تجميع مبالغ السداد لكل (مديونية, شهر)
        debt_month_map: Dict[Tuple[str, str], float] = {}
        for r in pmt_clean.iter_rows(named=True):
            did = str(r["_pmt_debt_clean"]).strip()
            mkey = str(r["_pmt_month_key"]).strip()
            amt = float(r["_pmt_amt_clean"] or 0.0)
            if did and amt > 0:
                debt_month_map[(did, mkey)] = debt_month_map.get((did, mkey), 0.0) + amt

        # 4. تجميع السدادات لكل محصل ومشرف حسب كل شهر مختار
        # بناء قائمة المحصلين الفريدين تحت كل مشرف
        grp_cols = [sup_col, col_col] if sup_col and sup_col in df_p.columns else [col_col]
        unique_collectors_df = df_p.select(grp_cols).unique().sort(sup_col if sup_col and sup_col in df_p.columns else col_col)

        # استخراج مديونيات كل محصل
        col_debts_map: Dict[Tuple[str, str], List[str]] = {}
        for r in df_p.iter_rows(named=True):
            s_name = str(r.get(sup_col) or "-").strip() if sup_col else "-"
            c_name = str(r.get(col_col) or "").strip()
            did    = str(r["_clean_debt_id"]).strip()
            if c_name and did:
                col_debts_map.setdefault((s_name, c_name), []).append(did)

        # تجهيز مسميات الأعمدة ومعلومات الشهور
        # إذا كان المفتاح "2026-07" نحصل على اسم "شهر 7"
        def _get_m_display(k: str) -> str:
            if "-" in k:
                try:
                    parts = k.split("-")
                    m_int = int(parts[1])
                    return f"شهر {m_int}"
                except:
                    return f"شهر {k}"
            return f"شهر {k}"

        months_meta = []
        for m_key in selected_months:
            disp_name = _get_m_display(m_key)
            tgt_val = float(monthly_targets.get(m_key, 50000.0))
            months_meta.append({
                "key": m_key,
                "name": disp_name,
                "target": tgt_val,
                "col_paid": f"تحصيل {disp_name}",
                "col_tgt": f"مستهدف {disp_name}",
                "col_pct": f"نسبة {disp_name} %",
            })

        # 5. بناء أسطر التقرير
        rows: List[Dict[str, Any]] = []

        # تجميع حسب المشرفين
        sup_groups: Dict[str, List[str]] = {}
        for (s_name, c_name) in col_debts_map.keys():
            sup_groups.setdefault(s_name, []).append(c_name)

        grand_totals = {m["key"]: {"paid": 0.0, "target": 0.0} for m in months_meta}
        grand_all_paid = 0.0
        grand_all_tgt = 0.0

        for s_name, collectors_list in sup_groups.items():
            sup_totals = {m["key"]: {"paid": 0.0, "target": 0.0} for m in months_meta}
            sup_all_paid = 0.0
            sup_all_tgt = 0.0

            # أسطر المحصلين التابعين للمشرف
            for c_name in collectors_list:
                debts = col_debts_map.get((s_name, c_name), [])
                row_dict: Dict[str, Any] = {
                    "المشرف": s_name,
                    "المحصل": c_name,
                }

                col_tot_paid = 0.0
                col_tot_tgt = 0.0

                for m in months_meta:
                    m_key = m["key"]
                    tgt_val = m["target"]
                    # جمع السدادات لهذه المديونيات في هذا الشهر
                    month_paid = sum(debt_month_map.get((did, m_key), 0.0) for did in debts)
                    pct_val = round((month_paid / tgt_val * 100.0), 2) if tgt_val > 0 else 0.0

                    row_dict[m["col_paid"]] = round(month_paid, 2)
                    row_dict[m["col_tgt"]]  = round(tgt_val, 2)
                    row_dict[m["col_pct"]]  = pct_val

                    sup_totals[m_key]["paid"] += month_paid
                    sup_totals[m_key]["target"] += tgt_val

                    grand_totals[m_key]["paid"] += month_paid
                    grand_totals[m_key]["target"] += tgt_val

                    col_tot_paid += month_paid
                    col_tot_tgt += tgt_val

                # إجماليات المحصل عبر كل الشهور
                col_tot_pct = round((col_tot_paid / col_tot_tgt * 100.0), 2) if col_tot_tgt > 0 else 0.0
                row_dict["إجمالي التحصيل"] = round(col_tot_paid, 2)
                row_dict["إجمالي المستهدف"] = round(col_tot_tgt, 2)
                row_dict["نسبة الإنجاز الكلية %"] = col_tot_pct
                row_dict["_row_type"] = "collector"

                sup_all_paid += col_tot_paid
                sup_all_tgt  += col_tot_tgt
                grand_all_paid += col_tot_paid
                grand_all_tgt  += col_tot_tgt

                rows.append(row_dict)

            # صف إجمالي المشرف الفرعي
            sup_subtotal_row: Dict[str, Any] = {
                "المشرف": f"إجمالي مشرف: {s_name}",
                "المحصل": f"({len(collectors_list)} محصلين)",
            }
            for m in months_meta:
                m_key = m["key"]
                s_paid = sup_totals[m_key]["paid"]
                s_tgt  = sup_totals[m_key]["target"]
                s_pct  = round((s_paid / s_tgt * 100.0), 2) if s_tgt > 0 else 0.0
                sup_subtotal_row[m["col_paid"]] = round(s_paid, 2)
                sup_subtotal_row[m["col_tgt"]]  = round(s_tgt, 2)
                sup_subtotal_row[m["col_pct"]]  = s_pct

            sup_all_pct = round((sup_all_paid / sup_all_tgt * 100.0), 2) if sup_all_tgt > 0 else 0.0
            sup_subtotal_row["إجمالي التحصيل"] = round(sup_all_paid, 2)
            sup_subtotal_row["إجمالي المستهدف"] = round(sup_all_tgt, 2)
            sup_subtotal_row["نسبة الإنجاز الكلية %"] = sup_all_pct
            sup_subtotal_row["_row_type"] = "subtotal"

            rows.append(sup_subtotal_row)

        # صف الإجمالي العام للمحفظة
        grand_total_row: Dict[str, Any] = {
            "المشرف": "🌟 الإجمالي العام للمحفظة",
            "المحصل": "الكل",
        }
        for m in months_meta:
            m_key = m["key"]
            g_paid = grand_totals[m_key]["paid"]
            g_tgt  = grand_totals[m_key]["target"]
            g_pct  = round((g_paid / g_tgt * 100.0), 2) if g_tgt > 0 else 0.0
            grand_total_row[m["col_paid"]] = round(g_paid, 2)
            grand_total_row[m["col_tgt"]]  = round(g_tgt, 2)
            grand_total_row[m["col_pct"]]  = g_pct

        grand_all_pct = round((grand_all_paid / grand_all_tgt * 100.0), 2) if grand_all_tgt > 0 else 0.0
        grand_total_row["إجمالي التحصيل"] = round(grand_all_paid, 2)
        grand_total_row["إجمالي المستهدف"] = round(grand_all_tgt, 2)
        grand_total_row["نسبة الإنجاز الكلية %"] = grand_all_pct
        grand_total_row["_row_type"] = "grand_total"

        rows.append(grand_total_row)

        df_report = pl.DataFrame(rows)

        # بناء ملخص إحصائي
        stats = {
            "نوع التقرير": "📅 تقرير التحصيل بالشهور بالمستهدف",
            "عدد الشهور المشمولة": len(months_meta),
            "إجمالي التحصيل الفعلي": f"{grand_all_paid:,.2f} ﷼",
            "إجمالي المستهدف الكلي": f"{grand_all_tgt:,.2f} ﷼",
            "نسبة الإنجاز الإجمالية": f"{grand_all_pct}%",
        }
        for m in months_meta:
            m_key = m["key"]
            m_paid = grand_totals[m_key]["paid"]
            m_tgt  = grand_totals[m_key]["target"]
            m_pct  = round((m_paid / m_tgt * 100.0), 2) if m_tgt > 0 else 0.0
            stats[f"تحصيل {m['name']}"] = f"{m_paid:,.2f} ﷼"
            stats[f"نسبة {m['name']}"] = f"{m_pct}%"

        return {
            "report_table": df_report,
            "months_meta": months_meta,
            "stats": stats,
            "grand_paid": grand_all_paid,
            "grand_target": grand_all_tgt,
            "grand_pct": grand_all_pct,
        }
