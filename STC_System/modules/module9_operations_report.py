# -*- coding: utf-8 -*-
"""
modules/module9_operations_report.py
───────────────────────────────────
نظام مركز تقارير العمليات (Operations Reporting System):
- الربط بين ملف المحفظة وملف السدادات / التحصيل بدقة كاملة وبدون أي تكرار
- حساب التغطية كعدد عملاء فريدين بناءً على [تاريخ المتابعة] وفق الفترة (يومي / أسبوعي / شهري)
- حساب التحصيل الدقيق من ملف السدادات مع تصفية التاريخ المحددة
- حساب نسب التغطية ونسب التحصيل مقارنة بالمستهدفات
- جدول التقرير التنفيذي:
  المشرف | المحصل | التغطية | مستهدف التغطية | نسبة التغطية % | التحصيل | مستهدف التحصيل | نسبة التحصيل %
"""

from __future__ import annotations
import logging
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import polars as pl
import pandas as pd

_log = logging.getLogger("STC_OPS")

_DEBT_COLS          = ["رقم المديونية", "رقم المديونيه", "رقم العقد", "رقم الحساب", "المديونية", "debt_id", "Debt ID"]
_ID_COLS            = ["رقم الهوية", "الهوية", "هوية العميل", "السجل المدني", "ID", "customer_id"]
_SUPERVISOR_COLS     = ["المشرف", "اسم المشرف", "supervisor", "Supervisor"]
_COLLECTOR_COLS      = ["المحصل", "اسم المحصل", "الموظف", "محصل", "collector", "Collector"]
# نعتمد حصراً وفقط على كولوم تاريخ المتابعة لا غير
_FOLLOWUP_DATE_COLS  = ["تاريخ المتابعة", "تاريخ المتابعه"]
_PAYMENT_AMOUNT_COLS = ["مبلغ السداد", "قيمة السداد", "المبلغ", "amount", "Amount", "paid_amount", "السدادات الموثقة"]
_PAYMENT_DATE_COLS   = ["تاريخ السداد", "تاريخ الدفع", "تاريخ الحركة", "تاريخ العملية", "التاريخ", "date", "Date", "payment_date"]


def _detect(df: pl.DataFrame, candidates: List[str]) -> Optional[str]:
    if df is None or len(df.columns) == 0:
        return None
    # 1. المطابقة التامة أولاً
    for c in candidates:
        if c in df.columns:
            return c
    # 2. مطابقة جزئية مع استبعاد الكلمات العامة
    for cand in candidates:
        cand_clean = cand.strip().lower()
        if len(cand_clean) < 4:
            continue
        for c in df.columns:
            c_clean = c.strip().lower()
            if cand_clean == c_clean or cand_clean in c_clean:
                return c
    return None


def _clean_str_id(val: Any) -> str:
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _clean_float_val(val: Any) -> float:
    if val is None or pd.isna(val):
        return 0.0
    try:
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).replace(",", "").replace(" ", "").replace("﷼", "").strip()
        return float(s) if s else 0.0
    except:
        return 0.0


def parse_date_smart(val: Any) -> str:
    """
    تحويل التاريخ إلى YYYY-MM-DD بدقة عالية مع دعم:
    - أرقام إكسيل التسلسلية (مثل 45000)
    - التواريخ النصية D/M/Y و Y-M-D و M/D/Y
    - النصوص التي تحوي أوقاتاً وساعات
    """
    if val is None or pd.isna(val):
        return ""
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    if not s or s.lower() in ("none", "nan", "null", "-", "غير محدد", "0", "0.0"):
        return ""

    # رقم إكسيل تسلسلي
    try:
        f = float(s)
        if 30000 <= f <= 65000:
            dt = pd.to_datetime(f, unit="D", origin="1899-12-30")
            return dt.strftime("%Y-%m-%d")
    except:
        pass

    # إزالة الوقت
    s_date = s.split(" ")[0].replace("/", "-")
    parts = s_date.split("-")
    if len(parts) == 3 and len(parts[0]) == 4:
        try:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            if 1990 <= y <= 2035 and 1 <= m <= 12 and 1 <= d <= 31:
                return f"{y:04d}-{m:02d}-{d:02d}"
        except:
            pass

    # تجربة صيغة اليوم أولاً ثم الشهر
    for dfmt in [True, False]:
        try:
            dt = pd.to_datetime(s_date, dayfirst=dfmt, errors="coerce")
            if pd.notna(dt) and 1990 <= dt.year <= 2035:
                return dt.strftime("%Y-%m-%d")
        except:
            pass

    return ""


def _detect_and_normalize_date_series(raw_list: List[Any]) -> List[str]:
    return [parse_date_smart(v) for v in raw_list]


def _normalize_date_val(val: Any) -> str:
    return parse_date_smart(val)


class OperationsReportModule:
    """
    مركز تقارير العمليات:
    ربط المحفظة بالسدادات برقم المديونية وحساب التغطية (كعدد عملاء فريدين) والتحصيل الدقيق والمستهدفات.
    """

    @staticmethod
    def detect_available_dates(portfolio: pl.DataFrame) -> Dict[str, Any]:
        """كشف التواريخ والأشهر المتاحة في عمود تاريخ المتابعة بالمحفظة"""
        if portfolio is None or len(portfolio) == 0:
            return {"dates": [], "latest_date": None, "top_date": None, "months": []}
        followup_col = _detect(portfolio, _FOLLOWUP_DATE_COLS)
        if not followup_col or followup_col not in portfolio.columns:
            return {"dates": [], "latest_date": None, "top_date": None, "months": []}
        raw_dates = portfolio[followup_col].drop_nulls().to_list()
        norm_dates = [d for d in _detect_and_normalize_date_series(raw_dates) if d and re.match(r"^\d{4}-\d{2}-\d{2}$", d)]
        if not norm_dates:
            return {"dates": [], "latest_date": None, "top_date": None, "months": []}
        from collections import Counter
        counts = Counter(norm_dates)
        sorted_dates = sorted(counts.keys(), reverse=True)
        top_date = counts.most_common(1)[0][0] if counts else sorted_dates[0]
        months = sorted(list(set(d[:7] for d in sorted_dates)), reverse=True)
        return {
            "dates": sorted_dates,
            "latest_date": sorted_dates[0],
            "top_date": top_date,
            "months": months,
            "date_counts": counts
        }

    @staticmethod
    def get_filter_options(portfolio: pl.DataFrame) -> Dict[str, List[str]]:
        if portfolio is None or len(portfolio) == 0:
            return {}
        sup_col = _detect(portfolio, _SUPERVISOR_COLS)
        col_col = _detect(portfolio, _COLLECTOR_COLS)

        sups = []
        if sup_col and sup_col in portfolio.columns:
            sups = sorted([str(x).strip() for x in portfolio[sup_col].drop_nulls().unique().to_list() if str(x).strip() not in ('', 'nan', 'None')])

        cols = []
        if col_col and col_col in portfolio.columns:
            cols = sorted([str(x).strip() for x in portfolio[col_col].drop_nulls().unique().to_list() if str(x).strip() not in ('', 'nan', 'None')])

        return {"supervisors": sups, "collectors": cols}

    def run(
        self,
        portfolio: pl.DataFrame,
        payments: Optional[pl.DataFrame] = None,
        report_mode: str = "daily",
        target_date: Optional[Any] = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
        supervisors: Optional[List[str]] = None,
        coverage_target: float = 200.0,
        collection_target: float = 50000.0,
        supervisor_targets: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:

        if portfolio is None or len(portfolio) == 0:
            raise ValueError("لم يتم رفع ملف المحفظة أو الملف فارغ!")

        # 1. كشف الأعمدة الحيوية في المحفظة
        debt_col_port = _detect(portfolio, _DEBT_COLS)
        cid_col_port  = _detect(portfolio, _ID_COLS)
        sup_col       = _detect(portfolio, _SUPERVISOR_COLS)
        col_col       = _detect(portfolio, _COLLECTOR_COLS)
        followup_col  = _detect(portfolio, _FOLLOWUP_DATE_COLS)

        if not col_col:
            raise ValueError("لم يتم العثور على عمود المحصل في ملف المحفظة!")
        if not debt_col_port:
            debt_col_port = _detect(portfolio, _ID_COLS) or portfolio.columns[0]

        df_p = portfolio.clone()

        # 2. فلتر المشرفين (إن وُجد)
        if supervisors and sup_col and sup_col in df_p.columns:
            df_p = df_p.filter(pl.col(sup_col).cast(pl.String).str.strip_chars().is_in(supervisors))

        if len(df_p) == 0:
            raise ValueError("لا توجد بيانات مطابقة للمشرفين المحددين!")

        # 3. توحيد وتحديد نطاق التغطية الزمني بناءً على [تاريخ المتابعة]
        today_obj = date.today()
        report_mode = (report_mode or "daily").lower().strip()

        if followup_col and followup_col in df_p.columns:
            raw_dates = df_p[followup_col].to_list()
            norm_dates = _detect_and_normalize_date_series(raw_dates)
            followup_series = pl.Series(norm_dates)
        else:
            followup_series = pl.Series([today_obj.strftime("%Y-%m-%d")] * len(df_p))

        if report_mode == "daily":
            target_date_str = _normalize_date_val(target_date) if target_date else today_obj.strftime("%Y-%m-%d")
            report_title = "📅 التقرير اليومي (Daily Report)"
            report_period_str = f"تاريخ التقرير: {target_date_str}"
            is_covered_expr = (followup_series == target_date_str)

        elif report_mode == "weekly":
            s_dt = _normalize_date_val(start_date) if start_date else (today_obj - timedelta(days=6)).strftime("%Y-%m-%d")
            e_dt = _normalize_date_val(end_date) if end_date else today_obj.strftime("%Y-%m-%d")
            # ضمان أن البداية والنهاية مرتبتان
            if s_dt > e_dt:
                s_dt, e_dt = e_dt, s_dt
            report_title = "🗓 التقرير الأسبوعي (Weekly Report)"
            report_period_str = f"الفترة: من {s_dt} إلى {e_dt}"
            is_covered_expr = (followup_series >= s_dt) & (followup_series <= e_dt) & (followup_series != "")

        elif report_mode == "monthly":
            m_val = int(month) if month else today_obj.month
            y_val = int(year) if year else today_obj.year
            month_prefix = f"{y_val:04d}-{m_val:02d}"
            report_title = "📆 التقرير الشهري (Monthly Report)"
            report_period_str = f"فترة الشهر: {month_prefix} ({m_val}/{y_val})"
            is_covered_expr = followup_series.str.starts_with(month_prefix)
        else:
            report_title = "📊 تقرير العمليات"
            report_period_str = f"التاريخ: {today_obj.strftime('%Y-%m-%d')}"
            is_covered_expr = pl.Series([True] * len(df_p))

        # تنظيف معرفات المديونية ورقم الهوية لحساب عدد العملاء الفريدين
        debt_expr = pl.col(debt_col_port).cast(pl.String).str.replace(r"\.0$", "", literal=False).str.strip_chars().alias("_clean_debt_id")
        if cid_col_port and cid_col_port in df_p.columns:
            cid_expr = pl.col(cid_col_port).cast(pl.String).str.replace(r"\.0$", "", literal=False).str.strip_chars().alias("_clean_cid")
        else:
            cid_expr = pl.col(debt_col_port).cast(pl.String).str.replace(r"\.0$", "", literal=False).str.strip_chars().alias("_clean_cid")

        df_p = df_p.with_columns([
            is_covered_expr.cast(pl.Int32).alias("_is_covered"),
            debt_expr,
            cid_expr
        ])

        # 4. بناء خرائط الربط للمحصلين والمشرفين (لمنع أي تكرار أو إسقاط في التحصيل)
        # مديونية -> (محصل, مشرف)
        # هوية -> (محصل, مشرف)
        debt_to_col: Dict[str, str] = {}
        cid_to_col: Dict[str, str] = {}
        collector_set = set()

        p_debts = df_p["_clean_debt_id"].to_list()
        p_cids  = df_p["_clean_cid"].to_list()
        p_cols  = [str(x).strip() for x in df_p[col_col].to_list()]

        for d_id, c_id, c_name in zip(p_debts, p_cids, p_cols):
            if d_id and d_id not in debt_to_col:
                debt_to_col[d_id] = c_name
            if c_id and c_id not in cid_to_col:
                cid_to_col[c_id] = c_name
            if c_name:
                collector_set.add(c_name)

        # 5. معالجة شيت السدادات / التحصيل بدقة كاملة وبدون أي تكرار
        # كل عملية سداد تُحسب مرة واحدة فقط للمحصل المستحق
        collector_payments: Dict[str, float] = {c: 0.0 for c in collector_set}

        if payments is not None and len(payments) > 0:
            pmt_debt_col = _detect(payments, _DEBT_COLS)
            pmt_cid_col  = _detect(payments, _ID_COLS)
            pmt_amt_col  = _detect(payments, _PAYMENT_AMOUNT_COLS)
            pmt_dt_col   = _detect(payments, _PAYMENT_DATE_COLS)
            pmt_collector_col = _detect(payments, _COLLECTOR_COLS)

            if pmt_amt_col:
                # تنظيف مبالغ السداد
                p_clean_df = payments.with_columns([
                    pl.col(pmt_amt_col).cast(pl.String, strict=False)
                    .str.replace_all(",", "", literal=True)
                    .str.replace_all(" ", "", literal=True)
                    .str.replace_all("﷼", "", literal=True)
                    .str.replace_all(r"[^\d\.-]", "", literal=False)
                    .cast(pl.Float64, strict=False)
                    .fill_null(0.0)
                    .alias("_amt")
                ])

                # تصفية السدادات بالتاريخ إذا كان عمود التاريخ موجوداً
                if pmt_dt_col and pmt_dt_col in p_clean_df.columns:
                    raw_p_dates = p_clean_df[pmt_dt_col].to_list()
                    norm_p_dates = _detect_and_normalize_date_series(raw_p_dates)
                    p_clean_df = p_clean_df.with_columns(pl.Series("_p_date", norm_p_dates))

                    if report_mode == "daily" and 'target_date_str' in locals():
                        # نقبل السدادات المطابقة لتاريخ اليوم (أو التواريخ الفارغة إن لم تتوفر في كل الصفوف)
                        p_clean_df = p_clean_df.filter(pl.col("_p_date") == target_date_str)
                    elif report_mode == "weekly" and 's_dt' in locals() and 'e_dt' in locals():
                        p_clean_df = p_clean_df.filter((pl.col("_p_date") >= s_dt) & (pl.col("_p_date") <= e_dt) & (pl.col("_p_date") != ""))
                    elif report_mode == "monthly" and 'month_prefix' in locals():
                        p_clean_df = p_clean_df.filter(pl.col("_p_date").str.starts_with(month_prefix))

                # استخراج القوائم لإسناد كل سداد للمحصل التابع له بالضبط
                p_amts = p_clean_df["_amt"].to_list()
                p_debts_raw = [_clean_str_id(x) for x in p_clean_df[pmt_debt_col].to_list()] if pmt_debt_col else [""] * len(p_clean_df)
                p_cids_raw  = [_clean_str_id(x) for x in p_clean_df[pmt_cid_col].to_list()] if pmt_cid_col else [""] * len(p_clean_df)
                p_col_names = [str(x).strip() for x in p_clean_df[pmt_collector_col].to_list()] if pmt_collector_col else [""] * len(p_clean_df)

                for amt, did, cid, c_name_direct in zip(p_amts, p_debts_raw, p_cids_raw, p_col_names):
                    if amt <= 0.0:
                        continue
                    # البحث عن المحصل: 1. برقم المديونية -> 2. برقم الهوية -> 3. بالاسم المباشر في شيت السداد
                    assigned_col = debt_to_col.get(did) or cid_to_col.get(cid) or (c_name_direct if c_name_direct in collector_set else None)
                    if assigned_col:
                        collector_payments[assigned_col] = collector_payments.get(assigned_col, 0.0) + amt

        # 6. التجميع لبناء التقرير التنفيذي المطلوب
        # التغطية: عدد العملاء الفريدين الذين تم التواصل معهم في الفترة المحددة
        grp_cols = [sup_col, col_col] if sup_col and sup_col in df_p.columns else [col_col]

        agg_summary = (
            df_p.group_by(grp_cols)
            .agg([
                pl.col("_clean_cid").filter(pl.col("_is_covered") == 1).n_unique().alias("التغطية"),
                pl.col("_clean_cid").n_unique().alias("إجمالي عملاء المحصل"),
                pl.len().alias("إجمالي مديونيات المحصل")
            ])
            .sort(sup_col if sup_col and sup_col in df_p.columns else col_col)
        )

        rows: List[Dict[str, Any]] = []
        supervisor_targets = supervisor_targets or {}

        def_cov_tgt = float(coverage_target if coverage_target and coverage_target > 0 else 200.0)
        def_col_tgt = float(collection_target if collection_target and collection_target > 0 else 50000.0)

        if sup_col and sup_col in agg_summary.columns:
            sup_groups: Dict[str, List[Dict[str, Any]]] = {}
            for r in agg_summary.iter_rows(named=True):
                s_name = str(r.get(sup_col) or "بدون مشرف").strip()
                sup_groups.setdefault(s_name, []).append(r)

            for s_name, cols_list in sup_groups.items():
                s_custom = supervisor_targets.get(s_name, {}) if supervisor_targets else {}
                cov_tgt_val = float(s_custom.get("coverage_target") or def_cov_tgt)
                col_tgt_val = float(s_custom.get("collection_target") or def_col_tgt)

                sup_tot_cov = 0.0
                sup_tot_col = 0.0
                sup_tot_cov_tgt = 0.0
                sup_tot_col_tgt = 0.0

                for c_item in cols_list:
                    c_name = str(c_item.get(col_col) or "").strip()
                    c_cov  = float(c_item.get("التغطية") or 0.0)
                    # التحصيل الدقيق من collector_payments (بدون أي تكرار)
                    c_col  = round(collector_payments.get(c_name, 0.0), 2)

                    c_cov_pct = round((c_cov / cov_tgt_val * 100.0), 2) if cov_tgt_val > 0 else 0.0
                    c_col_pct = round((c_col / col_tgt_val * 100.0), 2) if col_tgt_val > 0 else 0.0

                    sup_tot_cov     += c_cov
                    sup_tot_col     += c_col
                    sup_tot_cov_tgt += cov_tgt_val
                    sup_tot_col_tgt += col_tgt_val

                    rows.append({
                        "المشرف": s_name,
                        "المحصل": c_name,
                        "التغطية": int(c_cov),
                        "مستهدف التغطية": int(cov_tgt_val),
                        "نسبة التغطية %": c_cov_pct,
                        "التحصيل": c_col,
                        "مستهدف التحصيل": round(col_tgt_val, 2),
                        "نسبة التحصيل %": c_col_pct,
                        "_row_type": "collector"
                    })

                sup_cov_pct = round((sup_tot_cov / sup_tot_cov_tgt * 100.0), 2) if sup_tot_cov_tgt > 0 else 0.0
                sup_col_pct = round((sup_tot_col / sup_tot_col_tgt * 100.0), 2) if sup_tot_col_tgt > 0 else 0.0

                rows.append({
                    "المشرف": f"إجمالي مشرف: {s_name}",
                    "المحصل": f"({len(cols_list)} محصلين)",
                    "التغطية": int(sup_tot_cov),
                    "مستهدف التغطية": int(sup_tot_cov_tgt),
                    "نسبة التغطية %": sup_cov_pct,
                    "التحصيل": round(sup_tot_col, 2),
                    "مستهدف التحصيل": round(sup_tot_col_tgt, 2),
                    "نسبة التحصيل %": sup_col_pct,
                    "_row_type": "subtotal"
                })

        else:
            for c_item in agg_summary.iter_rows(named=True):
                c_name = str(c_item.get(col_col) or "").strip()
                c_cov  = float(c_item.get("التغطية") or 0.0)
                c_col  = round(collector_payments.get(c_name, 0.0), 2)

                c_cov_pct = round((c_cov / def_cov_tgt * 100.0), 2) if def_cov_tgt > 0 else 0.0
                c_col_pct = round((c_col / def_col_tgt * 100.0), 2) if def_col_tgt > 0 else 0.0

                rows.append({
                    "المشرف": "-",
                    "المحصل": c_name,
                    "التغطية": int(c_cov),
                    "مستهدف التغطية": int(def_cov_tgt),
                    "نسبة التغطية %": c_cov_pct,
                    "التحصيل": c_col,
                    "مستهدف التحصيل": round(def_col_tgt, 2),
                    "نسبة التحصيل %": c_col_pct,
                    "_row_type": "collector"
                })

        # ── صف الإجمالي العام النهائي ──
        grand_cov     = sum(r["التغطية"] for r in rows if r["_row_type"] == "collector")
        grand_cov_tgt = sum(r["مستهدف التغطية"] for r in rows if r["_row_type"] == "collector")
        grand_col     = sum(r["التحصيل"] for r in rows if r["_row_type"] == "collector")
        grand_col_tgt = sum(r["مستهدف التحصيل"] for r in rows if r["_row_type"] == "collector")

        grand_cov_pct = round((grand_cov / grand_cov_tgt * 100.0), 2) if grand_cov_tgt > 0 else 0.0
        grand_col_pct = round((grand_col / grand_col_tgt * 100.0), 2) if grand_col_tgt > 0 else 0.0

        rows.append({
            "المشرف": "🌟 الإجمالي العام للمحفظة",
            "المحصل": "الكل",
            "التغطية": int(grand_cov),
            "مستهدف التغطية": int(grand_cov_tgt),
            "نسبة التغطية %": grand_cov_pct,
            "التحصيل": round(grand_col, 2),
            "مستهدف التحصيل": round(grand_col_tgt, 2),
            "نسبة التحصيل %": grand_col_pct,
            "_row_type": "grand_total"
        })

        df_report = pl.DataFrame(rows)

        # إضافة عمود التحصيل في df_p للعرض التفصيلي
        col_to_amt = [collector_payments.get(str(c).strip(), 0.0) for c in df_p[col_col].to_list()]
        df_p = df_p.with_columns(pl.Series("_row_paid_amount", col_to_amt))

        stats = {
            "نوع التقرير": report_title,
            "الفترة الزمنية": report_period_str,
            "إجمالي التغطية الفعلية": f"{int(grand_cov):,} عميل",
            "مستهدف التغطية الكلي": f"{int(grand_cov_tgt):,} عميل",
            "نسبة التغطية الكلية": f"{grand_cov_pct}%",
            "إجمالي التحصيل الفعلي": f"{grand_col:,.2f} ﷼",
            "مستهدف التحصيل الكلي": f"{grand_col_tgt:,.2f} ﷼",
            "نسبة التحصيل الكلية": f"{grand_col_pct}%",
        }

        return {
            "report_mode": report_mode,
            "report_title": report_title,
            "report_period": report_period_str,
            "report_table": df_report,
            "data": df_p,
            "stats": stats,
            "pivot_supervisor": df_report.filter(pl.col("_row_type") != "collector"),
            "pivot_collector": df_report.filter(pl.col("_row_type") == "collector"),
        }
