# -*- coding: utf-8 -*-
"""
modules/module14_portfolio_analytics.py
──────────────────────────────────────
التحليل الشامل للمحفظة (Portfolio Analytics):

1. تحليل حالات التواصل (من قواعد موديول 2 رسمياً)
2. تحليل عمر الدين (سنة إنتهاء الحساب / فصل الخدمة) ربطاً بشيت التحصيل
3. تقييم أداء المشرفين وفرق المحصلين
4. أفضل وأسوأ 10 محصلين بناءً على التحصيل
"""

from __future__ import annotations
import io
import logging
import re
from datetime import datetime, date
from typing import Dict, List, Optional, Any
import polars as pl
import pandas as pd

from modules.module2_contact import (
    ContactStatusModule,
    CONTACTED,
    NOT_CONTACTED,
    NOT_CONTACT_CLOSED
)

_log = logging.getLogger("PORTFOLIO_ANALYTICS")

_DEBT_COLS         = ["رقم المديونية", "رقم المديونيه", "رقم العقد", "رقم الحساب", "المديونية", "debt_id"]
_ID_COLS           = ["رقم الهوية", "الهوية", "هوية العميل", "السجل المدني", "ID", "customer_id"]
_DEBT_AMT_COLS     = ["مبلغ المديونية", "مبلغ الميدونية", "المديونية", "debt_amount", "amount", "قيمة المديونية"]
_REMAIN_AMT_COLS   = ["متبقي سداد موثق", "المتبقي الموثق", "المتبقي", "remaining_amount", "متبقي السداد", "remaining"]
_SUPERVISOR_COLS   = ["المشرف", "اسم المشرف", "supervisor"]
_COLLECTOR_COLS    = ["المحصل", "اسم المحصل", "الموظف", "collector"]

# مرادفات تاريخ انتهاء الحساب (الخيار الأول)
_END_DATE_COLS     = [
    "تاريخ إنتهاء الحساب", "تاريخ انتهاء الحساب", "تاريخ إنتهاء  الحساب", "تاريخ انتهاء  الحساب",
    "تاريخ انتهاء الخدمة", "تاريخ إنتهاء الخدمة", "تاريخ الانتهاء", "تاريخ الإنتهاء",
    "انتهاء الحساب", "إنتهاء الحساب", "تاريخ النهاية", "end_date", "expiry_date", "account_end_date"
]

# مرادفات تاريخ فصل الخدمة (البديل في حال عدم وجود الأول)
_DISC_DATE_COLS    = [
    "تاريخ فصل الخدمة", "تاريخ فصل الخدمه", "تاريخ فصل  الخدمة", "تاريخ فصل  الخدمه",
    "فصل الخدمة", "فصل الخدمه", "تاريخ الفصل", "تاريخ فصل", "فصل", "سنة فصل الخدمة", "سنة الفصل",
    "disconnection_date", "disc_date", "disconnect_date", "service_disconnect_date"
]

_PAY_AMT_COLS      = ["مبلغ السداد", "قيمة السداد", "المبلغ", "amount", "paid_amount", "السدادات الموثقة"]
_PAY_DATE_COLS     = ["تاريخ السداد", "تاريخ الدفع", "تاريخ الحركة", "التاريخ", "payment_date", "date"]


def _norm_str(s: str) -> str:
    s = re.sub(r'[\s_]+', ' ', str(s or '')).strip().lower()
    s = re.sub(r'[إأآا]', 'ا', s)
    s = s.replace('ة', 'ه').replace('ى', 'ي')
    return s


def _detect_col(df: Any, candidates: List[str]) -> Optional[str]:
    cols = df.columns if hasattr(df, "columns") else []
    for c in candidates:
        if c in cols:
            return c
    norm_candidates = [_norm_str(cand) for cand in candidates]
    for c in cols:
        c_norm = _norm_str(c)
        for cand_norm in norm_candidates:
            if c_norm == cand_norm:
                return c
    for c in cols:
        c_norm = _norm_str(c)
        for cand_norm in norm_candidates:
            if len(cand_norm) >= 4 and cand_norm in c_norm:
                return c
    return None


def clean_id(val: Any) -> str:
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def to_clean_num(series: Any) -> pd.Series:
    if series is None:
        return pd.Series(dtype=float)
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").fillna(0.0)
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.replace(" ", "", regex=False).str.replace("﷼", "", regex=False),
        errors="coerce"
    ).fillna(0.0)


def extract_year_smart(val: Any) -> str:
    """استخراج سنة إنتهاء الحساب أو فصل الخدمة (عمر الدين) من صيغ التواريخ المختلفة أو أرقام إكسيل"""
    if val is None or pd.isna(val):
        return "غير محدد"
    s = str(val).strip()
    if not s or s.lower() in ("none", "nan", "null", "-", "غير محدد", "0", "0.0"):
        return "غير محدد"
    
    # 1. رقم إكسيل تسلسلي أو سنة مباشرة
    try:
        f = float(s)
        if 30000 <= f <= 65000:
            dt = pd.to_datetime(f, unit="D", origin="1899-12-30")
            return str(dt.year)
        elif 1980 <= f <= 2035:
            return str(int(f))
    except:
        pass

    # 2. بحث عن سنة رباعية صريحة
    m = re.search(r"\b(19[89]\d|20[0-3]\d)\b", s)
    if m:
        return m.group(1)

    # 3. محاولة بالتحويل الزمني
    for dfmt in [True, False]:
        try:
            dt = pd.to_datetime(s.split(" ")[0], errors="coerce", dayfirst=dfmt)
            if pd.notna(dt) and 1980 <= dt.year <= 2035:
                return str(dt.year)
        except:
            pass

    return "غير محدد"


class StrategicPortfolioModule:

    def run(
        self,
        portfolio: Any,
        payments: Optional[Any] = None,
        date_from: Optional[Any] = None,
        date_to: Optional[Any] = None,
        supervisors: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:

        # ── 1. تجهيز المحفظة كـ Polars DataFrame لتشغيل موديول 2 ──
        if isinstance(portfolio, pl.DataFrame):
            pl_p = portfolio.clone()
        else:
            pl_p = pl.DataFrame(portfolio)

        if pl_p.height == 0:
            raise ValueError("ملف المحفظة فارغ!")

        # ── 2. تشغيل موديول 2 (ContactStatusModule) لاستخراج تصنيف التوصل الرسمي ──
        contact_mod = ContactStatusModule()
        contact_res = contact_mod.run(pl_p)
        df_contact_pl = contact_res["data"]

        # تحويل لـ Pandas لإكمال عمليات الربط المالي والتحليل
        df_p = df_contact_pl.to_pandas()

        # ── 3. كشف وتوحيد أسماء الأعمدة الأساسية ──
        col_debt   = _detect_col(df_p, _DEBT_COLS)
        col_id     = _detect_col(df_p, _ID_COLS)
        col_debt_a = _detect_col(df_p, _DEBT_AMT_COLS)
        col_rem_a  = _detect_col(df_p, _REMAIN_AMT_COLS)
        col_sup    = _detect_col(df_p, _SUPERVISOR_COLS)
        col_coll   = _detect_col(df_p, _COLLECTOR_COLS)

        # كشف عمودي تاريخ انتهاء الحساب وتاريخ فصل الخدمة (مع البديل التلقائي)
        col_end_date  = _detect_col(df_p, _END_DATE_COLS)
        col_disc_date = _detect_col(df_p, _DISC_DATE_COLS)

        if col_end_date and col_disc_date:
            vintage_source_desc = f"{col_end_date} (وبديل: {col_disc_date})"
        elif col_end_date:
            vintage_source_desc = col_end_date
        elif col_disc_date:
            vintage_source_desc = col_disc_date
        else:
            vintage_source_desc = "غير متوفر"

        # ── 4. استخراج وإضافة كولوم [عمر الدين] في المحفظة ──
        def _get_vintage_year(row) -> str:
            # الخيار الأول: تاريخ انتهاء الحساب
            if col_end_date and col_end_date in row:
                yr = extract_year_smart(row[col_end_date])
                if yr != "غير محدد":
                    return yr
            # الخيار الثاني (البديل): تاريخ فصل الخدمة
            if col_disc_date and col_disc_date in row:
                yr = extract_year_smart(row[col_disc_date])
                if yr != "غير محدد":
                    return yr
            return "غير محدد"

        df_p["عمر الدين"] = df_p.apply(_get_vintage_year, axis=1)

        # تنظيف الحقول التحليلية
        df_p["_debt_clean"] = df_p[col_debt].apply(clean_id) if col_debt else [""] * len(df_p)
        df_p["_cid_clean"]  = df_p[col_id].apply(clean_id) if col_id else [""] * len(df_p)
        df_p["_debt_amt"]   = to_clean_num(df_p[col_debt_a]) if col_debt_a else pd.Series(0.0, index=df_p.index)
        df_p["_remain_amt"] = to_clean_num(df_p[col_rem_a]) if col_rem_a else pd.Series(0.0, index=df_p.index)
        df_p["_supervisor"] = df_p[col_sup].fillna("غير محدد").astype(str).str.strip() if col_sup else pd.Series("غير محدد", index=df_p.index)
        df_p["_collector"]  = df_p[col_coll].fillna("غير محدد").astype(str).str.strip() if col_coll else pd.Series("غير محدد", index=df_p.index)

        # فلترة المشرفين إذا تم تحديدهم
        if supervisors and len(supervisors) > 0:
            clean_sups = set(str(s).strip() for s in supervisors if str(s).strip())
            if clean_sups:
                df_p = df_p[df_p["_supervisor"].isin(clean_sups)].copy()
                if df_p.empty:
                    raise ValueError("لا توجد سجلات مطابقة للمشرفين المحددين في ملف المحفظة!")

        # حالة التوصل الناتجة مباشرة من موديول 2
        df_p["_contact_status"] = df_p["حالة التوصل"].fillna(NOT_CONTACTED).astype(str).str.strip()

        # خريطة أولوية التوصل للعميل: تم التوصل (1) > لا يرد ومغلق (2) > عدم التوصل (3)
        prio_map = {CONTACTED: 1, NOT_CONTACT_CLOSED: 2, NOT_CONTACTED: 3}
        df_p["_prio"] = df_p["_contact_status"].map(prio_map).fillna(3)

        # ── 5. بناء خرائط ربط رقم المديونية بعمر الدين والمحصل (من المحفظة) ──
        # هذا الربط يستخدم لاحقاً في معالجة شيت التحصيل
        debt_to_col: Dict[str, str] = {}
        cid_to_col: Dict[str, str] = {}
        debt_to_vintage: Dict[str, str] = {}  # رقم المديونية → سنة عمر الدين (من المحفظة)
        cid_to_vintage: Dict[str, str] = {}

        for _, r in df_p.iterrows():
            did = r["_debt_clean"]
            cid = r["_cid_clean"]
            col_name = r["_collector"]
            v_year = str(r["عمر الدين"]).strip()

            if did:
                debt_to_col.setdefault(did, col_name)
                debt_to_vintage.setdefault(did, v_year)
            if cid:
                cid_to_col.setdefault(cid, col_name)
                cid_to_vintage.setdefault(cid, v_year)

        # تجميع تحصيل المحصل والسنة (سيُملأ من شيت التحصيل)
        collector_collection: Dict[str, float] = {c: 0.0 for c in df_p["_collector"].unique()}
        # vintage_collection: مجموع التحصيل من شيت التحصيل مقسوم حسب سنة عمر الدين (من المحفظة)
        vintage_collection: Dict[str, float] = {y: 0.0 for y in df_p["عمر الدين"].unique()}
        debt_collection_map: Dict[str, float] = {}
        total_pay_amt = 0.0

        has_payments = False
        if payments is not None:
            if isinstance(payments, pl.DataFrame):
                df_pay = payments.to_pandas()
            else:
                df_pay = pd.DataFrame(payments).copy()

            if not df_pay.empty:
                pay_debt_col = _detect_col(df_pay, _DEBT_COLS)
                pay_cid_col  = _detect_col(df_pay, _ID_COLS)
                pay_amt_col  = _detect_col(df_pay, _PAY_AMT_COLS)
                pay_date_col = _detect_col(df_pay, _PAY_DATE_COLS)
                pay_col_col  = _detect_col(df_pay, _COLLECTOR_COLS)

                if pay_amt_col:
                    has_payments = True
                    df_pay["_amt"] = to_clean_num(df_pay[pay_amt_col])

                    # فلترة تاريخ السداد لو وُجد النطاق
                    if pay_date_col:
                        df_pay["_p_date"] = pd.to_datetime(df_pay[pay_date_col], errors="coerce")
                        if date_from:
                            df_pay = df_pay[df_pay["_p_date"] >= pd.Timestamp(date_from)]
                        if date_to:
                            df_pay = df_pay[df_pay["_p_date"] <= pd.Timestamp(date_to)]

                    p_debts = df_pay[pay_debt_col].apply(clean_id) if pay_debt_col else [""] * len(df_pay)
                    p_cids  = df_pay[pay_cid_col].apply(clean_id) if pay_cid_col else [""] * len(df_pay)
                    p_cols  = df_pay[pay_col_col].astype(str).str.strip() if pay_col_col else [""] * len(df_pay)
                    p_amts  = df_pay["_amt"].values

                    for amt, did, cid, direct_col in zip(p_amts, p_debts, p_cids, p_cols):
                        if amt <= 0.0:
                            continue
                        total_pay_amt += amt

                        # تجميع التحصيل لكل مديونية
                        if did:
                            debt_collection_map[did] = debt_collection_map.get(did, 0.0) + amt

                        # تحديد المحصل من المحفظة أو مباشرة من شيت التحصيل
                        assigned_col = debt_to_col.get(did) or cid_to_col.get(cid) or (direct_col if direct_col in collector_collection else None)
                        if assigned_col:
                            collector_collection[assigned_col] = collector_collection.get(assigned_col, 0.0) + amt

                        # تحديد سنة عمر الدين من المحفظة (عبر رقم المديونية)
                        assigned_year = debt_to_vintage.get(did) or cid_to_vintage.get(cid) or "غير محدد"
                        vintage_collection[assigned_year] = vintage_collection.get(assigned_year, 0.0) + amt

        df_p["_collected_amt"] = df_p["_debt_clean"].map(debt_collection_map).fillna(0.0)

        # ── 6. ملخص حالات التواصل الشامل (مطابق 100% لموديول 2) ──
        total_records = len(df_p)
        cnt_contacted = int((df_p["_contact_status"] == CONTACTED).sum())
        cnt_closed    = int((df_p["_contact_status"] == NOT_CONTACT_CLOSED).sum())
        cnt_not       = int((df_p["_contact_status"] == NOT_CONTACTED).sum())
        cnt_total_not = cnt_closed + cnt_not

        pct_contacted = round(cnt_contacted / total_records * 100, 1) if total_records > 0 else 0.0
        pct_closed    = round(cnt_closed / total_records * 100, 1) if total_records > 0 else 0.0
        pct_not       = round(cnt_not / total_records * 100, 1) if total_records > 0 else 0.0
        pct_total_not = round(cnt_total_not / total_records * 100, 1) if total_records > 0 else 0.0

        # على مستوى العملاء الفريدين (بالهوية)
        cust_agg = df_p.groupby("_cid_clean")["_prio"].min().reset_index()
        u_total     = len(cust_agg)
        u_contacted = int((cust_agg["_prio"] == 1).sum())
        u_closed    = int((cust_agg["_prio"] == 2).sum())
        u_not       = int((cust_agg["_prio"] == 3).sum())
        u_total_not = u_closed + u_not

        u_pct_contacted = round(u_contacted / u_total * 100, 1) if u_total > 0 else 0.0
        u_pct_closed    = round(u_closed / u_total * 100, 1) if u_total > 0 else 0.0
        u_pct_not       = round(u_not / u_total * 100, 1) if u_total > 0 else 0.0
        u_pct_total_not = round(u_total_not / u_total * 100, 1) if u_total > 0 else 0.0

        contact_summary_df = pd.DataFrame([
            {
                "حالة التواصل": CONTACTED,
                "عدد الحسابات (السجلات)": cnt_contacted,
                "نسبة الحسابات %": f"{pct_contacted}%",
                "عدد العملاء (الهويات)": u_contacted,
                "نسبة العملاء %": f"{u_pct_contacted}%"
            },
            {
                "حالة التواصل": NOT_CONTACT_CLOSED,
                "عدد الحسابات (السجلات)": cnt_closed,
                "نسبة الحسابات %": f"{pct_closed}%",
                "عدد العملاء (الهويات)": u_closed,
                "نسبة العملاء %": f"{u_pct_closed}%"
            },
            {
                "حالة التواصل": NOT_CONTACTED,
                "عدد الحسابات (السجلات)": cnt_not,
                "نسبة الحسابات %": f"{pct_not}%",
                "عدد العملاء (الهويات)": u_not,
                "نسبة العملاء %": f"{u_pct_not}%"
            },
            {
                "حالة التواصل": "إجمالي عدم التوصل (مغلق + عدم توصل)",
                "عدد الحسابات (السجلات)": cnt_total_not,
                "نسبة الحسابات %": f"{pct_total_not}%",
                "عدد العملاء (الهويات)": u_total_not,
                "نسبة العملاء %": f"{u_pct_total_not}%"
            },
            {
                "حالة التواصل": "الإجمالي العام",
                "عدد الحسابات (السجلات)": total_records,
                "نسبة الحسابات %": "100.0%",
                "عدد العملاء (الهويات)": u_total,
                "نسبة العملاء %": "100.0%"
            }
        ])

        # ── 7. جدول عمر الدين ──
        # مبلغ المديونية: من المحفظة (مجموع لكل سنة)
        # إجمالي التحصيل: من شيت التحصيل (مربوط برقم المديونية → سنة عمر الدين من المحفظة)
        tot_debt_all  = df_p["_debt_amt"].sum()
        tot_remain_all = df_p["_remain_amt"].sum()
        tot_coll_rate = round(total_pay_amt / tot_debt_all * 100, 2) if tot_debt_all > 0 else 0.0

        v_rows = []
        for v_yr, grp in df_p.groupby("عمر الدين"):
            n_recs = len(grp)
            n_cust = grp["_cid_clean"].nunique()
            d_amt  = grp["_debt_amt"].sum()          # من المحفظة
            r_amt  = grp["_remain_amt"].sum()         # من المحفظة
            c_amt  = vintage_collection.get(str(v_yr).strip(), 0.0)  # من شيت التحصيل
            c_pct  = round(c_amt / d_amt * 100, 2) if d_amt > 0 else 0.0

            yr_contacted = (grp["_contact_status"] == CONTACTED).sum()
            yr_contact_pct = round(yr_contacted / n_recs * 100, 1) if n_recs > 0 else 0.0

            v_rows.append({
                "عمر الدين (السنة)": str(v_yr),
                "عدد الحسابات": n_recs,
                "عدد العملاء": n_cust,
                "مبلغ المديونية": round(d_amt, 2),
                "متبقي سداد موثق": round(r_amt, 2),
                "إجمالي التحصيل": round(c_amt, 2),
                "نسبة التحصيل %": c_pct,
                "تم التوصل": yr_contacted,
                "نسبة التوصل %": f"{yr_contact_pct}%"
            })

        vintage_df = pd.DataFrame(v_rows)

        def _yr_sort(val):
            try: return int(val)
            except: return -1

        if not vintage_df.empty:
            vintage_df["sort_k"] = vintage_df["عمر الدين (السنة)"].apply(_yr_sort)
            vintage_df = vintage_df.sort_values("sort_k", ascending=False).drop(columns=["sort_k"]).reset_index(drop=True)

            v_tot = {
                "عمر الدين (السنة)": "الإجمالي",
                "عدد الحسابات": total_records,
                "عدد العملاء": u_total,
                "مبلغ المديونية": round(tot_debt_all, 2),
                "متبقي سداد موثق": round(tot_remain_all, 2),
                "إجمالي التحصيل": round(total_pay_amt, 2),
                "نسبة التحصيل %": tot_coll_rate,
                "تم التوصل": cnt_contacted,
                "نسبة التوصل %": f"{pct_contacted}%"
            }
            vintage_table_display = pd.concat([vintage_df, pd.DataFrame([v_tot])], ignore_index=True)
        else:
            vintage_table_display = pd.DataFrame()

        # ── 8. جدول أداء المشرفين ──
        sup_rows = []
        for s_name, grp in df_p.groupby("_supervisor"):
            s_recs = len(grp)
            s_cust = grp["_cid_clean"].nunique()
            s_debt = grp["_debt_amt"].sum()
            s_rem  = grp["_remain_amt"].sum()

            s_cols = grp["_collector"].unique()
            s_coll = sum(collector_collection.get(c, 0.0) for c in s_cols)
            s_pct  = round(s_coll / s_debt * 100, 2) if s_debt > 0 else 0.0

            s_contacted = int((grp["_contact_status"] == CONTACTED).sum())
            s_closed    = int((grp["_contact_status"] == NOT_CONTACT_CLOSED).sum())
            s_not       = int((grp["_contact_status"] == NOT_CONTACTED).sum())
            s_contact_pct = round(s_contacted / s_recs * 100, 1) if s_recs > 0 else 0.0
            s_not_pct     = round((s_closed + s_not) / s_recs * 100, 1) if s_recs > 0 else 0.0

            sup_rows.append({
                "المشرف": s_name,
                "عدد الحسابات": s_recs,
                "عدد العملاء": s_cust,
                "مبلغ المديونية": round(s_debt, 2),
                "متبقي سداد موثق": round(s_rem, 2),
                "إجمالي التحصيل": round(s_coll, 2),
                "نسبة التحصيل %": s_pct,
                "تم التوصل": s_contacted,
                "لا يرد ومغلق": s_closed,
                "عدم التوصل": s_not,
                "نسبة التوصل %": f"{s_contact_pct}%",
                "نسبة عدم التوصل %": f"{s_not_pct}%"
            })

        sup_df = pd.DataFrame(sup_rows)
        if not sup_df.empty:
            sup_df = sup_df.sort_values("إجمالي التحصيل", ascending=False).reset_index(drop=True)

        # ── 9. جدول المحصلين وترتيب التوب 10 والأسوأ 10 ──
        col_rows = []
        for c_name, grp in df_p.groupby("_collector"):
            c_recs = len(grp)
            c_cust = grp["_cid_clean"].nunique()
            c_debt = grp["_debt_amt"].sum()
            c_rem  = grp["_remain_amt"].sum()
            c_coll = collector_collection.get(c_name, 0.0)
            c_pct  = round(c_coll / c_debt * 100, 2) if c_debt > 0 else 0.0

            c_sup = grp["_supervisor"].iloc[0] if not grp["_supervisor"].empty else "غير محدد"

            c_contacted = int((grp["_contact_status"] == CONTACTED).sum())
            c_closed    = int((grp["_contact_status"] == NOT_CONTACT_CLOSED).sum())
            c_not       = int((grp["_contact_status"] == NOT_CONTACTED).sum())
            c_contact_pct = round(c_contacted / c_recs * 100, 1) if c_recs > 0 else 0.0

            col_rows.append({
                "المحصل": c_name,
                "المشرف": c_sup,
                "عدد الحسابات": c_recs,
                "عدد العملاء": c_cust,
                "مبلغ المديونية": round(c_debt, 2),
                "متبقي سداد موثق": round(c_rem, 2),
                "إجمالي التحصيل": round(c_coll, 2),
                "نسبة التحصيل %": c_pct,
                "تم التوصل": c_contacted,
                "نسبة التوصل %": f"{c_contact_pct}%"
            })

        col_df = pd.DataFrame(col_rows)
        if not col_df.empty:
            col_df_sorted = col_df.sort_values("إجمالي التحصيل", ascending=False).reset_index(drop=True)
            top_10    = col_df_sorted.head(10).copy()
            bottom_10 = col_df_sorted.tail(10).sort_values("إجمالي التحصيل", ascending=True).reset_index(drop=True)
        else:
            col_df_sorted = pd.DataFrame()
            top_10        = pd.DataFrame()
            bottom_10     = pd.DataFrame()

        # تنظيف المحفظة للإخراج (بدون أعمدة مؤقتة، مع إبقاء عمر الدين)
        export_portfolio = df_p.drop(
            columns=["_debt_clean", "_cid_clean", "_debt_amt", "_remain_amt",
                     "_supervisor", "_collector", "_prio", "_contact_status", "_collected_amt"],
            errors="ignore"
        )

        # ── 10. الإحصائيات العامة ──
        stats = {
            "إجمالي الحسابات": f"{total_records:,} حساب",
            "إجمالي العملاء": f"{u_total:,} عميل",
            "إجمالي مبلغ المديونية": f"{tot_debt_all:,.2f} ﷼",
            "إجمالي متبقي سداد موثق": f"{tot_remain_all:,.2f} ﷼",
            "إجمالي التحصيل": f"{total_pay_amt:,.2f} ﷼",
            "نسبة التحصيل العامة %": f"{tot_coll_rate}%",
            "تم التوصل": f"{cnt_contacted:,} ({pct_contacted}%)",
            "لا يرد ومغلق": f"{cnt_closed:,} ({pct_closed}%)",
            "عدم التوصل": f"{cnt_not:,} ({pct_not}%)",
            "نسبة التوصل العامة %": f"{pct_contacted}%",
            "نسبة عدم التوصل العامة %": f"{pct_total_not}%",
            "عدد المحصلين": int(df_p["_collector"].nunique()),
            "عدد المشرفين": int(df_p["_supervisor"].nunique()),
            "عدد سنوات عمر الدين": len(vintage_df),
            "عمود عمر الدين المستخدم": vintage_source_desc
        }

        return {
            "portfolio_with_vintage": export_portfolio,
            "contact_summary": contact_summary_df,
            "vintage_table": vintage_table_display,
            "supervisor_table": sup_df,
            "top_10_collectors": top_10,
            "bottom_10_collectors": bottom_10,
            "all_collectors": col_df_sorted,
            "supervisors_list": sorted([s for s in df_p["_supervisor"].unique() if s != "غير محدد"]),
            "stats": stats,
            "has_payments": has_payments
        }


def export_analytics_excel_bytes(results: Dict[str, Any]) -> bytes:
    """تصدير التقرير الشامل في شيت واحد فقط بتنسيق RTL وأعمدة متناسقة"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book

        # ─── تعريف التنسيقات ───
        hdr_fmt = workbook.add_format({
            "bold": True, "bg_color": "#1E3A8A", "font_color": "#FFFFFF",
            "border": 1, "align": "center", "valign": "vcenter",
            "font_size": 11
        })
        section_fmt = workbook.add_format({
            "bold": True, "bg_color": "#2563EB", "font_color": "#FFFFFF",
            "border": 1, "align": "right", "valign": "vcenter",
            "font_size": 12
        })
        cell_fmt = workbook.add_format({
            "border": 1, "align": "center", "valign": "vcenter",
            "font_size": 10
        })
        total_fmt = workbook.add_format({
            "bold": True, "bg_color": "#DBEAFE", "border": 1,
            "align": "center", "valign": "vcenter", "font_size": 10
        })
        pct_fmt = workbook.add_format({
            "border": 1, "align": "center", "valign": "vcenter",
            "font_size": 10, "num_format": "0.00%"
        })

        sheet_name = "التقرير الشامل"
        worksheet = workbook.add_worksheet(sheet_name)
        worksheet.right_to_left()
        worksheet.set_zoom(90)

        current_row = 0

        def write_section_header(title: str, num_cols: int):
            nonlocal current_row
            worksheet.merge_range(current_row, 0, current_row, num_cols - 1, title, section_fmt)
            worksheet.set_row(current_row, 22)
            current_row += 1

        def write_dataframe(df: pd.DataFrame, is_total_last: bool = False):
            nonlocal current_row
            if df is None or df.empty:
                worksheet.write(current_row, 0, "لا توجد بيانات", cell_fmt)
                current_row += 2
                return

            # رأس الأعمدة
            for col_idx, col_name in enumerate(df.columns):
                worksheet.write(current_row, col_idx, str(col_name), hdr_fmt)
                # ضبط عرض العمود
                val_lens = [len(str(x)) for x in df[col_name].head(200).values]
                max_len = max([len(str(col_name))] + val_lens) if val_lens else len(str(col_name))
                worksheet.set_column(col_idx, col_idx, min(max(max_len + 2, 12), 40))
            current_row += 1

            # الصفوف
            for row_idx, (_, row) in enumerate(df.iterrows()):
                is_last = is_total_last and row_idx == len(df) - 1
                fmt = total_fmt if is_last else cell_fmt
                for col_idx, val in enumerate(row.values):
                    worksheet.write(current_row, col_idx, val, fmt)
                current_row += 1
            current_row += 1  # فراغ بين الأقسام

        # ─── القسم 1: ملخص حالات التواصل ───
        contact_df = results.get("contact_summary")
        n_cols = len(contact_df.columns) if contact_df is not None and not contact_df.empty else 5
        write_section_header("ملخص حالات التواصل", n_cols)
        write_dataframe(contact_df, is_total_last=True)

        # ─── القسم 2: تحليل عمر الدين ───
        vintage_df = results.get("vintage_table")
        n_cols = len(vintage_df.columns) if vintage_df is not None and not vintage_df.empty else 9
        write_section_header("تحليل عمر الدين (سنة إنتهاء الحساب / فصل الخدمة)", n_cols)
        write_dataframe(vintage_df, is_total_last=True)

        # ─── القسم 3: أداء المشرفين ───
        sup_df = results.get("supervisor_table")
        n_cols = len(sup_df.columns) if sup_df is not None and not sup_df.empty else 12
        write_section_header("أداء المشرفين", n_cols)
        write_dataframe(sup_df)

        # ─── القسم 4: أفضل 10 محصلين ───
        top10_df = results.get("top_10_collectors")
        n_cols = len(top10_df.columns) if top10_df is not None and not top10_df.empty else 10
        write_section_header("أفضل 10 محصلين تحصيلاً", n_cols)
        write_dataframe(top10_df)

        # ─── القسم 5: أسوأ 10 محصلين ───
        bot10_df = results.get("bottom_10_collectors")
        n_cols = len(bot10_df.columns) if bot10_df is not None and not bot10_df.empty else 10
        write_section_header("أقل 10 محصلين تحصيلاً", n_cols)
        write_dataframe(bot10_df)

        # ─── إضافة رسم بياني لعمر الدين ───
        if vintage_df is not None and not vintage_df.empty and len(vintage_df) > 1:
            chart = workbook.add_chart({"type": "column"})
            # البيانات موجودة في شيت التقرير — نبني مرجع بناءً على موضعها
            # البداية بعد contact (نعتمد على current_row المُجمّع للحصول على موقع vintage)
            # نستخدم مخزون بديل: نكتب بيانات الرسم في شيت مخفي
            data_sheet = workbook.add_worksheet("_chart_data")
            data_sheet.hide()
            v_data = vintage_df[vintage_df["عمر الدين (السنة)"] != "الإجمالي"].copy()
            data_sheet.write(0, 0, "السنة")
            data_sheet.write(0, 1, "مبلغ المديونية")
            data_sheet.write(0, 2, "متبقي سداد موثق")
            data_sheet.write(0, 3, "إجمالي التحصيل")
            for i, (_, vrow) in enumerate(v_data.iterrows(), start=1):
                data_sheet.write(i, 0, str(vrow.get("عمر الدين (السنة)", "")))
                data_sheet.write(i, 1, float(vrow.get("مبلغ المديونية", 0) or 0))
                data_sheet.write(i, 2, float(vrow.get("متبقي سداد موثق", 0) or 0))
                data_sheet.write(i, 3, float(vrow.get("إجمالي التحصيل", 0) or 0))

            n_v = len(v_data)
            chart.add_series({
                "name": "مبلغ المديونية",
                "categories": ["_chart_data", 1, 0, n_v, 0],
                "values": ["_chart_data", 1, 1, n_v, 1],
                "fill": {"color": "#1E3A8A"}
            })
            chart.add_series({
                "name": "متبقي سداد موثق",
                "categories": ["_chart_data", 1, 0, n_v, 0],
                "values": ["_chart_data", 1, 2, n_v, 2],
                "fill": {"color": "#2563EB"}
            })
            if results.get("has_payments"):
                chart.add_series({
                    "name": "إجمالي التحصيل",
                    "categories": ["_chart_data", 1, 0, n_v, 0],
                    "values": ["_chart_data", 1, 3, n_v, 3],
                    "fill": {"color": "#60A5FA"}
                })
            chart.set_title({"name": "المديونية والمتبقي والتحصيل حسب سنة عمر الدين"})
            chart.set_x_axis({"name": "سنة عمر الدين"})
            chart.set_y_axis({"name": "المبلغ (ريال)"})
            chart.set_style(10)
            chart.set_size({"width": 700, "height": 350})
            worksheet.insert_chart(current_row, 0, chart)
            current_row += 20

    return output.getvalue()
