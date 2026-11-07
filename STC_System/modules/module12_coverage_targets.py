# -*- coding: utf-8 -*-
"""
Module 12: Coverage & Coverage Targets (التغطية ومستهدف التغطية والتحصيل)
Dedicated module for Individual System (سيستم الأفراد).

Calculates unique customer coverage, coverage target achievement, collection targets & actuals,
gaps, daily cumulative unique coverage, collector/supervisor/portfolio breakdowns,
and detailed covered/non-covered customer lists.
"""
import pandas as pd
import numpy as np
import polars as pl
import io
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple

class CoverageTargetsModule:
    """
    ماديول التغطية ومستهدف التغطية والتحصيل الخاص بسيستم الأفراد
    """

    def _detect_col(self, df: pd.DataFrame, candidates: List[str], default: str = "") -> str:
        for c in candidates:
            if c in df.columns:
                return c
        for c in df.columns:
            for cand in candidates:
                if cand.lower() in str(c).lower():
                    return c
        return default

    def _clean_date_str(self, val: Any) -> str:
        if pd.isna(val) or val is None or str(val).strip() in ("", "None", "nan", "NaT"):
            return ""
        s = str(val).strip()
        if len(s) >= 10 and s[:10].replace("-", "").isdigit():
            parts = s[:10].split("-")
            if len(parts) == 3 and len(parts[0]) == 4:
                return s[:10]
        try:
            dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
            if pd.notna(dt):
                return dt.strftime("%Y-%m-%d")
        except Exception:
            pass
        return ""

    def _safe_float(self, val: Any) -> float:
        if pd.isna(val) or val is None:
            return 0.0
        try:
            s = str(val).replace(",", "").strip()
            return float(s)
        except Exception:
            return 0.0

    def run(

        self,
        portfolio_in: Any,
        payments_in: Optional[Any] = None,
        coverage_start_date: Optional[str] = None,
        coverage_end_date: Optional[str] = None,
        payment_start_date: Optional[str] = None,
        payment_end_date: Optional[str] = None,
        target_type: str = "percent",  # "percent" or "count"
        target_value: float = 80.0,
        collection_target_value: float = 0.0,  # مستهدف التحصيل المالي بالريال
        supervisors: Optional[List[str]] = None,
        collectors: Optional[List[str]] = None,
        portfolios: Optional[List[str]] = None,
        threshold_green: float = 100.0,
        threshold_yellow: float = 80.0,
    ) -> Dict[str, Any]:
        """
        تنفيذ تحليل التغطية ومستهدف التغطية والتحصيل الموحد للأفراد
        """
        # 1. تحويل المدخلات إلى Pandas DataFrames مع حماية البيانات الأصلية
        if isinstance(portfolio_in, pl.DataFrame):
            df_port = portfolio_in.to_pandas()
        elif isinstance(portfolio_in, pd.DataFrame):
            df_port = portfolio_in.copy()
        else:
            return {"error": "ملف المحفظة غير صالح!"}

        if df_port.empty:
            return {"error": "المحفظة فارغة!"}

        df_pay = None
        if payments_in is not None:
            if isinstance(payments_in, pl.DataFrame):
                df_pay = payments_in.to_pandas()
            elif isinstance(payments_in, pd.DataFrame):
                df_pay = payments_in.copy()

        # 2. اكتشاف الأعمدة الرئيسية في المحفظة
        cust_id_col = self._detect_col(df_port, [
            "رقم الهوية", "الهوية", "رقم الحساب", "رقم المديونية", "رقم المدينية",
            "الرقم الرئيسي", "ID", "Customer ID", "Account No.", "Account No", "Debt No."
        ], "")
        cust_name_col = self._detect_col(df_port, ["اسم العميل", "العميل", "Customer Name", "Name", "الاسم"], "")
        sup_col = self._detect_col(df_port, ["المشرف", "اسم المشرف", "مشرف", "Supervisor", "supervisor"], "")
        col_col = self._detect_col(df_port, ["المحصل", "اسم المحصل", "محصل", "Collector", "collector"], "")
        prt_col = self._detect_col(df_port, ["المحافظ", "المحفظة", "اسم المحفظة", "Portfolio", "محفظة"], "")
        date_col = self._detect_col(df_port, [
            "تاريخ المتابعة", "تاريخ التواصل", "تاريخ آخر متابعة", "آخر تاريخ متابعة",
            "تاريخ الاتصال", "Followup Date", "Follow Up Date", "التاريخ", "تاريخ"
        ], "")
        debt_col = self._detect_col(df_port, [
            "مبلغ المديونية", "متبقي سداد موثق", "المديونية المتبقية", "إجمالي المديونية",
            "متبقي المديونية", "المديونية", "Debt Amount", "Balance"
        ], "")

        # fallback: if no cust_id col found, create synthetic
        if not cust_id_col or cust_id_col not in df_port.columns:
            df_port["_cust_id"] = ["CUST_" + str(i) for i in range(len(df_port))]
            cust_id_col = "_cust_id"

        # 3. الفلترة المسبقة
        df_filt = df_port.copy()
        if supervisors and sup_col and sup_col in df_filt.columns:
            df_filt = df_filt[df_filt[sup_col].astype(str).str.strip().isin(supervisors)]
        if collectors and col_col and col_col in df_filt.columns:
            df_filt = df_filt[df_filt[col_col].astype(str).str.strip().isin(collectors)]
        if portfolios and prt_col and prt_col in df_filt.columns:
            df_filt = df_filt[df_filt[prt_col].astype(str).str.strip().isin(portfolios)]

        if df_filt.empty:
            return {"error": "لا توجد بيانات مطابقة للفلاتر المحددة!"}

        # 4. تنظيف التواريخ
        if date_col and date_col in df_filt.columns:
            df_filt = df_filt.copy()
            df_filt["_clean_followup_date"] = df_filt[date_col].apply(self._clean_date_str)
        else:
            df_filt = df_filt.copy()
            df_filt["_clean_followup_date"] = ""

        cov_start = self._clean_date_str(coverage_start_date) or "2000-01-01"
        cov_end = self._clean_date_str(coverage_end_date) or "2099-12-31"

        pay_start = self._clean_date_str(payment_start_date) or cov_start
        pay_end = self._clean_date_str(payment_end_date) or cov_end

        # 5. تنظيف ملف السدادات ومطابقة المبالغ
        pay_cust_col = pay_amt_col = pay_date_col = ""
        has_payments = False
        pay_filt = pd.DataFrame()
        cust_payment_totals = {}  # {cust_id: total_amount}

        if df_pay is not None and not df_pay.empty:
            pay_cust_col = self._detect_col(df_pay, ["رقم الهوية", "الهوية", "رقم الحساب", "ID"], "رقم الهوية")
            pay_amt_col = self._detect_col(df_pay, ["مبلغ السداد", "مبلغ السداد الموثق", "السدادات الموثقة", "المبلغ", "Amount"], "مبلغ السداد")
            pay_date_col = self._detect_col(df_pay, ["تاريخ السداد", "تاريخ الدفع", "التاريخ", "Date"], "تاريخ السداد")
            if pay_cust_col in df_pay.columns:
                has_payments = True
                df_pay["_clean_pay_date"] = df_pay[pay_date_col].apply(self._clean_date_str) if pay_date_col in df_pay.columns else ""
                
                # تحويل مبالغ السداد إلى أرقام
                if pay_amt_col in df_pay.columns:
                    df_pay["_clean_amt"] = pd.to_numeric(df_pay[pay_amt_col].astype(str).str.replace(",", ""), errors="coerce").fillna(0.0)
                else:
                    df_pay["_clean_amt"] = 0.0

                pay_filt = df_pay[
                    (df_pay["_clean_pay_date"] >= pay_start) &
                    (df_pay["_clean_pay_date"] <= pay_end)
                ] if "_clean_pay_date" in df_pay.columns else df_pay.copy()

        # 6. تحديد العملاء المؤهلين الفراداوين
        eligible_cust_ids = set(df_filt[cust_id_col].astype(str).str.strip().unique())
        total_eligible_unique = len(eligible_cust_ids)

        # 7. تحديد العملاء المغطين
        fol_covered_df = df_filt[
            (df_filt["_clean_followup_date"] >= cov_start) &
            (df_filt["_clean_followup_date"] <= cov_end)
        ] if "_clean_followup_date" in df_filt.columns else pd.DataFrame()

        fol_covered_custs = {}
        if not fol_covered_df.empty:
            for cid, grp in fol_covered_df.groupby(cust_id_col):
                cid_str = str(cid).strip()
                dates = [d for d in grp["_clean_followup_date"].tolist() if d]
                max_d = max(dates) if dates else cov_start
                fol_covered_custs[cid_str] = {"count": len(grp), "last_date": max_d}

        pay_covered_custs = {}
        if has_payments and not pay_filt.empty:
            for cid, grp in pay_filt.groupby(pay_cust_col):
                cid_str = str(cid).strip()
                if cid_str in eligible_cust_ids:
                    dates = [d for d in grp["_clean_pay_date"].tolist() if d]
                    max_d = max(dates) if dates else pay_start
                    tot_amt = grp["_clean_amt"].sum()
                    cust_payment_totals[cid_str] = tot_amt
                    pay_covered_custs[cid_str] = {"count": len(grp), "last_date": max_d, "amount": tot_amt}

        covered_cust_info = {}
        for cid in eligible_cust_ids:
            has_fol = cid in fol_covered_custs
            has_pay = cid in pay_covered_custs
            if has_fol or has_pay:
                src = "سداد ومتابعة" if (has_fol and has_pay) else ("سداد" if has_pay else "متابعة")
                cnt = (fol_covered_custs[cid]["count"] if has_fol else 0) + (pay_covered_custs[cid]["count"] if has_pay else 0)
                d1 = fol_covered_custs[cid]["last_date"] if has_fol else ""
                d2 = pay_covered_custs[cid]["last_date"] if has_pay else ""
                last_d = max(d1, d2)
                cov_d = min([d for d in [d1, d2] if d] or [cov_start])
                pay_amt = pay_covered_custs[cid]["amount"] if has_pay else 0.0

                covered_cust_info[cid] = {
                    "source": src,
                    "activity_count": cnt,
                    "last_date": last_d,
                    "coverage_date": cov_d,
                    "payment_amount": pay_amt
                }

        total_covered_unique = len(covered_cust_info)
        total_actual_collection = sum(cust_payment_totals.values())

        # 8. مستهدفات التغطية والتحصيل
        if target_type == "percent":
            target_customers = int(round(total_eligible_unique * (float(target_value) / 100.0)))
        else:
            target_customers = int(target_value)

        target_customers = max(0, target_customers)
        coverage_rate_pct = round((total_covered_unique / total_eligible_unique * 100.0), 2) if total_eligible_unique > 0 else 0.0
        target_achievement_pct = round((total_covered_unique / target_customers * 100.0), 2) if target_customers > 0 else 0.0
        gap_customers = max(0, target_customers - total_covered_unique)

        collection_target_amt = float(collection_target_value)
        collection_achievement_pct = round((total_actual_collection / collection_target_amt * 100.0), 2) if collection_target_amt > 0 else 0.0
        collection_gap = max(0.0, collection_target_amt - total_actual_collection)

        # 9. تفاصيل العملاء
        df_first = df_filt.drop_duplicates(subset=[cust_id_col]).copy()
        covered_rows = []
        not_covered_rows = []

        for _, r in df_first.iterrows():
            cid = str(r[cust_id_col]).strip()
            cname = str(r.get(cust_name_col, "")) if (cust_name_col and cust_name_col in r.index) else ""
            sup = str(r.get(sup_col, "")) if (sup_col and sup_col in r.index) else ""
            col = str(r.get(col_col, "")) if (col_col and col_col in r.index) else ""
            prt = str(r.get(prt_col, "")) if (prt_col and prt_col in r.index) else ""
            debt = self._safe_float(r.get(debt_col, 0.0)) if (debt_col and debt_col in r.index) else 0.0
            last_fol = str(r.get("_clean_followup_date", ""))

            if cid in covered_cust_info:
                info = covered_cust_info[cid]
                covered_rows.append({
                    "رقم الهوية": cid,
                    "اسم العميل": cname,
                    "المحفظة": prt,
                    "المحصل": col,
                    "المشرف": sup,
                    "تاريخ التغطية": info["coverage_date"],
                    "عدد مرات النشاط": info["activity_count"],
                    "مبلغ السداد": round(info["payment_amount"], 2),
                    "آخر تاريخ نشاط": info["last_date"],
                    "مصدر التغطية": info["source"]
                })
            else:
                not_covered_rows.append({
                    "رقم الهوية": cid,
                    "اسم العميل": cname,
                    "المحفظة": prt,
                    "المحصل": col,
                    "المشرف": sup,
                    "المديونية": debt,
                    "آخر متابعة": last_fol,
                    "سبب عدم التغطية": "لم يتم السداد أو المتابعة خلال الفترة المحددة"
                })

        df_covered_custs = pd.DataFrame(covered_rows)
        df_not_covered_custs = pd.DataFrame(not_covered_rows)

        # 10. التجميع حسب المحصل (Collector Breakdown)
        collector_rows = []
        if col_col and col_col in df_filt.columns:
            for cname, grp in df_filt.groupby(col_col):
                c_cids = set(grp[cust_id_col].astype(str).str.strip().unique())
                c_elig = len(c_cids)
                c_cov_cids = c_cids.intersection(covered_cust_info.keys())
                c_cov = len(c_cov_cids)
                c_pay_amt = sum(covered_cust_info[cid]["payment_amount"] for cid in c_cov_cids)

                if target_type == "percent":
                    c_tgt = int(round(c_elig * (float(target_value) / 100.0)))
                else:
                    ratio = c_elig / total_eligible_unique if total_eligible_unique > 0 else 0
                    c_tgt = int(round(target_value * ratio))

                ratio_col = c_elig / total_eligible_unique if total_eligible_unique > 0 else 0
                c_pay_tgt = collection_target_amt * ratio_col

                c_cov_pct = round((c_cov / c_elig * 100.0), 2) if c_elig > 0 else 0.0
                c_ach_pct = round((c_cov / c_tgt * 100.0), 2) if c_tgt > 0 else 0.0
                c_pay_ach_pct = round((c_pay_amt / c_pay_tgt * 100.0), 2) if c_pay_tgt > 0 else 0.0
                c_gap = max(0, c_tgt - c_cov)

                if c_ach_pct >= threshold_green:
                    status = "🟢 حقق المستهدف"
                elif c_ach_pct >= threshold_yellow:
                    status = "🟡 قريب من المستهدف"
                else:
                    status = "🔴 أقل من المستهدف"

                collector_rows.append({
                    "المحصل": str(cname),
                    "العملاء": c_elig,
                    "المغطى": c_cov,
                    "التغطية %": c_cov_pct,
                    "مستهدف التغطية": c_tgt,
                    "تحقيق التغطية %": c_ach_pct,
                    "المتبقي للتغطية": c_gap,
                    "إجمالي التحصيل": round(c_pay_amt, 2),
                    "مستهدف التحصيل": round(c_pay_tgt, 2) if c_pay_tgt > 0 else None,
                    "تحقيق التحصيل %": c_pay_ach_pct if c_pay_tgt > 0 else None,
                    "الحالة": status
                })

        df_collector = pd.DataFrame(collector_rows)
        if not df_collector.empty:
            df_collector = df_collector.sort_values(by=["تحقيق التغطية %", "المغطى"], ascending=False)

        # 11. التجميع حسب المشرف (Supervisor Breakdown)
        supervisor_rows = []
        if sup_col and sup_col in df_filt.columns:
            for sname, grp in df_filt.groupby(sup_col):
                s_cids = set(grp[cust_id_col].astype(str).str.strip().unique())
                s_elig = len(s_cids)
                s_cov_cids = s_cids.intersection(covered_cust_info.keys())
                s_cov = len(s_cov_cids)
                s_pay_amt = sum(covered_cust_info[cid]["payment_amount"] for cid in s_cov_cids)

                if target_type == "percent":
                    s_tgt = int(round(s_elig * (float(target_value) / 100.0)))
                else:
                    ratio = s_elig / total_eligible_unique if total_eligible_unique > 0 else 0
                    s_tgt = int(round(target_value * ratio))

                ratio_sup = s_elig / total_eligible_unique if total_eligible_unique > 0 else 0
                s_pay_tgt = collection_target_amt * ratio_sup

                s_cov_pct = round((s_cov / s_elig * 100.0), 2) if s_elig > 0 else 0.0
                s_ach_pct = round((s_cov / s_tgt * 100.0), 2) if s_tgt > 0 else 0.0
                s_pay_ach_pct = round((s_pay_amt / s_pay_tgt * 100.0), 2) if s_pay_tgt > 0 else 0.0
                s_gap = max(0, s_tgt - s_cov)

                if s_ach_pct >= threshold_green:
                    status = "🟢 حقق المستهدف"
                elif s_ach_pct >= threshold_yellow:
                    status = "🟡 قريب من المستهدف"
                else:
                    status = "🔴 أقل من المستهدف"

                supervisor_rows.append({
                    "المشرف": str(sname),
                    "العملاء": s_elig,
                    "المغطى": s_cov,
                    "التغطية %": s_cov_pct,
                    "مستهدف التغطية": s_tgt,
                    "تحقيق التغطية %": s_ach_pct,
                    "المتبقي للتغطية": s_gap,
                    "إجمالي التحصيل": round(s_pay_amt, 2),
                    "مستهدف التحصيل": round(s_pay_tgt, 2) if s_pay_tgt > 0 else None,
                    "تحقيق التحصيل %": s_pay_ach_pct if s_pay_tgt > 0 else None,
                    "الحالة": status
                })

        df_supervisor = pd.DataFrame(supervisor_rows)
        if not df_supervisor.empty:
            df_supervisor = df_supervisor.sort_values(by=["تحقيق التغطية %", "المغطى"], ascending=False)

        # 12. التجميع حسب المحفظة (Portfolio Breakdown)
        portfolio_rows = []
        if prt_col and prt_col in df_filt.columns:
            for pname, grp in df_filt.groupby(prt_col):
                p_cids = set(grp[cust_id_col].astype(str).str.strip().unique())
                p_elig = len(p_cids)
                p_cov_cids = p_cids.intersection(covered_cust_info.keys())
                p_cov = len(p_cov_cids)
                p_pay_amt = sum(covered_cust_info[cid]["payment_amount"] for cid in p_cov_cids)

                if target_type == "percent":
                    p_tgt = int(round(p_elig * (float(target_value) / 100.0)))
                else:
                    ratio = p_elig / total_eligible_unique if total_eligible_unique > 0 else 0
                    p_tgt = int(round(target_value * ratio))

                ratio_prt = p_elig / total_eligible_unique if total_eligible_unique > 0 else 0
                p_pay_tgt = collection_target_amt * ratio_prt

                p_cov_pct = round((p_cov / p_elig * 100.0), 2) if p_elig > 0 else 0.0
                p_ach_pct = round((p_cov / p_tgt * 100.0), 2) if p_tgt > 0 else 0.0
                p_pay_ach_pct = round((p_pay_amt / p_pay_tgt * 100.0), 2) if p_pay_tgt > 0 else 0.0
                p_gap = max(0, p_tgt - p_cov)

                portfolio_rows.append({
                    "المحفظة": str(pname),
                    "العملاء": p_elig,
                    "المغطى": p_cov,
                    "التغطية %": p_cov_pct,
                    "مستهدف التغطية": p_tgt,
                    "تحقيق التغطية %": p_ach_pct,
                    "المتبقي للتغطية": p_gap,
                    "إجمالي التحصيل": round(p_pay_amt, 2),
                    "مستهدف التحصيل": round(p_pay_tgt, 2) if p_pay_tgt > 0 else None,
                    "تحقيق التحصيل %": p_pay_ach_pct if p_pay_tgt > 0 else None
                })

        df_portfolio = pd.DataFrame(portfolio_rows)
        if not df_portfolio.empty:
            df_portfolio = df_portfolio.sort_values(by=["تحقيق التغطية %", "المغطى"], ascending=False)

        # 13. التغطية اليومية والتجميعية
        daily_rows = []
        if not df_covered_custs.empty and "تاريخ التغطية" in df_covered_custs.columns:
            df_cov_sorted = df_covered_custs.sort_values(by="تاريخ التغطية")
            dates_list = sorted([d for d in df_cov_sorted["تاريخ التغطية"].unique() if d])
            
            seen_cids = set()
            for d_str in dates_list:
                d_custs = df_cov_sorted[df_cov_sorted["تاريخ التغطية"] == d_str]["رقم الهوية"].tolist()
                new_today = len(set(d_custs))
                seen_cids.update(d_custs)
                cum_unique = len(seen_cids)
                
                daily_cov_pct = round((new_today / total_eligible_unique * 100.0), 2) if total_eligible_unique > 0 else 0.0
                cum_cov_pct = round((cum_unique / total_eligible_unique * 100.0), 2) if total_eligible_unique > 0 else 0.0

                daily_rows.append({
                    "التاريخ": d_str,
                    "العملاء المؤهلون": total_eligible_unique,
                    "المغطى اليومي": new_today,
                    "نسبة التغطية اليومية %": daily_cov_pct,
                    "التغطية التجميعية (فريد)": cum_unique,
                    "نسبة التغطية التجميعية %": cum_cov_pct,
                    "المستهدف الكلي": target_customers,
                    "الفرق التجميعي": max(0, target_customers - cum_unique)
                })

        df_daily = pd.DataFrame(daily_rows)

        # 14. ملخص الإحصائيات (Stats)
        stats = {
            "إجمالي العملاء": total_eligible_unique,
            "مستهدف التغطية": target_customers,
            "العملاء المغطاة": total_covered_unique,
            "نسبة التغطية %": f"{coverage_rate_pct:.2f}%",
            "تحقيق مستهدف التغطية %": f"{target_achievement_pct:.2f}%",
            "المتبقي لمستهدف التغطية": gap_customers,
            "إجمالي التحصيل": f"{total_actual_collection:,.2f} ﷼",
            "مستهدف التحصيل": f"{collection_target_amt:,.2f} ﷼" if collection_target_amt > 0 else "غير محدد",
            "تحقيق مستهدف التحصيل %": f"{collection_achievement_pct:.2f}%" if collection_target_amt > 0 else "غير محدد",
        }

        period_warning = ""
        if has_payments:
            period_warning = f"⚠️ تنبيه: بيانات التغطية تعتمد على فترة السدادات المرفوعة فقط ({pay_start} إلى {pay_end}). عدم وجود العميل لا يعني عدم التغطية تاريخياً بل فقط خلال هذه الفترة."

        return {
            "stats": stats,
            "total_eligible": total_eligible_unique,
            "target_customers": target_customers,
            "total_covered": total_covered_unique,
            "coverage_rate_pct": coverage_rate_pct,
            "target_achievement_pct": target_achievement_pct,
            "gap_customers": gap_customers,
            "total_actual_collection": total_actual_collection,
            "collection_target_amt": collection_target_amt,
            "collection_achievement_pct": collection_achievement_pct,
            "collection_gap": collection_gap,
            "daily_coverage": df_daily,
            "collector_coverage": df_collector,
            "supervisor_coverage": df_supervisor,
            "portfolio_coverage": df_portfolio,
            "covered_customers": df_covered_custs,
            "not_covered_customers": df_not_covered_custs,
            "period_warning": period_warning,
            "coverage_period_str": f"من {cov_start} إلى {cov_end}",
            "payment_period_str": f"من {pay_start} إلى {pay_end}" if has_payments else "لم يتم تقديم ملف سدادات"
        }

    def export_excel(self, result_dict: Dict[str, Any]) -> bytes:
        """
        توليد تقرير Excel شامل بأسلوب مهاره المنسق
        - يضمن دائماً وجود شيت واحد على الأقل (ملخص) حتى لا تحدث IndexError
        """
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            # ─── 1. ملخص التغطية والتحصيل (دائماً مرئي) ───────────────────
            stats_data = result_dict.get("stats", {})
            stats_df = pd.DataFrame(
                list(stats_data.items()) if stats_data else [["لا توجد بيانات", "-"]],
                columns=["المؤشر", "القيمة"]
            )
            stats_df.to_excel(writer, sheet_name="ملخص التغطية والتحصيل", index=False)

            # ─── 2. التغطية اليومية ──────────────────────────────────────────
            daily = result_dict.get("daily_coverage")
            if daily is not None and isinstance(daily, pd.DataFrame) and not daily.empty:
                try:
                    daily.to_excel(writer, sheet_name="التغطية اليومية", index=False)
                except Exception:
                    pass

            # ─── 3. تغطية المحصلين ───────────────────────────────────────────
            coll = result_dict.get("collector_coverage")
            if coll is not None and isinstance(coll, pd.DataFrame) and not coll.empty:
                try:
                    coll.to_excel(writer, sheet_name="تغطية المحصلين", index=False)
                except Exception:
                    pass

            # ─── 4. تغطية المشرفين ───────────────────────────────────────────
            sup = result_dict.get("supervisor_coverage")
            if sup is not None and isinstance(sup, pd.DataFrame) and not sup.empty:
                try:
                    sup.to_excel(writer, sheet_name="تغطية المشرفين", index=False)
                except Exception:
                    pass

            # ─── 5. تغطية المحافظ ────────────────────────────────────────────
            prt = result_dict.get("portfolio_coverage")
            if prt is not None and isinstance(prt, pd.DataFrame) and not prt.empty:
                try:
                    prt.to_excel(writer, sheet_name="تغطية المحافظ", index=False)
                except Exception:
                    pass

            # ─── 6. العملاء المغطاة ──────────────────────────────────────────
            cov_c = result_dict.get("covered_customers")
            if cov_c is not None and isinstance(cov_c, pd.DataFrame) and not cov_c.empty:
                try:
                    cov_c.to_excel(writer, sheet_name="العملاء المغطاة", index=False)
                except Exception:
                    pass

            # ─── 7. العملاء غير المغطاة ─────────────────────────────────────
            ncov_c = result_dict.get("not_covered_customers")
            if ncov_c is not None and isinstance(ncov_c, pd.DataFrame) and not ncov_c.empty:
                try:
                    ncov_c.to_excel(writer, sheet_name="العملاء غير المغطاة", index=False)
                except Exception:
                    pass

        return output.getvalue()

