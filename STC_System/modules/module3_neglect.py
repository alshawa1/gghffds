"""
modules/module3_neglect.py
──────────────────────────
Module 3 — الإهمال (Neglect Analysis) using Polars.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Dict, Optional

import polars as pl

from core.utils import parse_date, get_today

_log = logging.getLogger("Module3_Neglect")


class NeglectModule:
    DAYS_COL   = "عدد أيام الإهمال"
    STATUS_COL = "حالة الإهمال"

    def run(self, portfolio: pl.DataFrame) -> Dict:
        _log.info("▶ بدء تحليل الإهمال (Polars) (%d صف)", len(portfolio))
        df = portfolio.clone()

        # 1. تحديد أعمدة الإدخال
        followup_col = next((c for c in ["تاريخ المتابعة"] if c in df.columns), None)
        dist_col = next((c for c in ["تاريخ التوزيع", "تاريخ الإسناد", "تاريخ اسناد المحفظة"] if c in df.columns), "تاريخ التوزيع")
        status_main_col = next((c for c in ["الحالة الرئيسية"] if c in df.columns), "الحالة الرئيسية")
        status_sub_col = next((c for c in ["الحالة الفرعية"] if c in df.columns), "الحالة الفرعية")
        collector_col = next((c for c in ["اسم المحصل", "المحصل", "الموظف"] if c in df.columns), "المحصل")
        supervisor_col = next((c for c in ["المشرف", "اسم المشرف"] if c in df.columns), "المشرف")
        note_col = next((c for c in ["الملاحظة", "الملاحظات", "ملاحظة"] if c in df.columns), "الملاحظة")

        # التأكد من وجود جميع الأعمدة
        for col_name in [followup_col, dist_col, status_main_col, status_sub_col, collector_col, supervisor_col, note_col]:
            if col_name not in df.columns:
                df = df.with_columns(pl.lit("").alias(col_name))
        # ─── استبعاد الحالات الرئيسية والملاحظات المحددة قبل البدء ────────────────────
        # (عدم توصل - مسجون - اعتراض - متوفي - خروج نهائي - تسوية - مقطوع - الرقم غير صحيح - لا يخص)
        if status_main_col in df.columns:
            exclude_list = ["عدم توصل", "مسجون", "متوفي", "خروج نهائي", "تسوية", "تسويه", "مقطوع", "الرقم غير صحيح", "لا يخص", "لايخص"]
            df = df.filter(
                ~pl.col(status_main_col).cast(pl.String).str.strip_chars().is_in(exclude_list) &
                ~pl.col(status_main_col).cast(pl.String).str.contains("اعتراض", literal=True)
            )

        # استبعاد من عمود الملاحظة/المتابعة إذا احتوى على: (مقطوع - الرقم غير صحيح - لا يخص)
        if note_col in df.columns:
            note_str = pl.col(note_col).cast(pl.String).str.strip_chars().str.to_lowercase()
            df = df.filter(
                ~note_str.str.contains("مقطوع", literal=True) &
                ~note_str.str.contains("الرقم غير صحيح", literal=True) &
                ~note_str.str.contains("رقم غير صحيح", literal=True) &
                ~note_str.str.contains("لا يخص", literal=True) &
                ~note_str.str.contains("لايخص", literal=True)
            )
        _log.info("🚫 تم استبعاد الحالات والملاحظات المستثناة من الإهمال - المتبقي: %d صف", len(df))

        # ─── استبعاد العملاء الذين متبقي سداد موثق أقل من 50 ─────────────────
        # هؤلاء سددوا ما عليهم فعلاً ولا يُعتبرون مهملين
        _BAL_COL = next((c for c in ["متبقي سداد موثق", "متبقى سداد موثق", "الرصيد المتبقي", "متبقي السداد"] if c in df.columns), None)
        if _BAL_COL:
            try:
                bal_expr = pl.col(_BAL_COL).cast(pl.Float64, strict=False).fill_null(9999.0)
                before = len(df)
                df = df.filter(bal_expr >= 50.0)
                _log.info("💰 تم استبعاد %d صف بـ %s < 50 من الإهمال", before - len(df), _BAL_COL)
            except Exception as e:
                _log.warning("⚠ لم يُطبَّق فلتر متبقي سداد موثق: %s", e)




        # ─── خطوة 0: حساب عدد العملاء = 1/COUNTIF(رقم الهوية) ──────────────
        # مثل إكسيل: =1/COUNTIF($A:$A,A2) → يُستخدم لحساب العملاء الفريدين عند الجمع
        id_col = next((c for c in ["رقم الهوية", "الهوية"] if c in df.columns), None)
        if id_col:
            df = df.with_columns(
                (pl.lit(1.0) / pl.col(id_col).count().over(id_col).cast(pl.Float64))
                .alias("عدد العملاء")
            )
        else:
            df = df.with_columns(pl.lit(1.0).alias("عدد العملاء"))

        # ─── خطوة 1: تحديد وتوحيد كولومات تاريخ المتابعة وآخر متابعة وتاريخ الإسناد ──────
        followup_col = next((c for c in ["تاريخ المتابعة"] if c in df.columns), None)
        last_fu_col  = None  # لا نستخدم آخر متابعة على العميل — نعتمد فقط على تاريخ المتابعة
        dist_col     = next((c for c in ["تاريخ الاسناد", "تاريخ التوزيع", "تاريخ الإسناد"] if c in df.columns), None)

        def get_parsed_date_expr(col_name):
            if not col_name:
                return pl.lit(None).cast(pl.Date)
            clean_str = pl.col(col_name).cast(pl.String, strict=False).str.strip_chars().str.replace(r"\s+.*$", "")
            return (
                clean_str.str.to_date("%m/%d/%Y", strict=False)
                .fill_null(clean_str.str.to_date("%Y-%m-%d", strict=False))
                .fill_null(clean_str.str.to_date("%d/%m/%Y", strict=False))
                .fill_null(clean_str.str.to_date("%Y/%m/%d", strict=False))
                .fill_null(clean_str.str.to_date("%d-%m-%Y", strict=False))
                .fill_null(clean_str.str.to_date("%m-%d-%Y", strict=False))
            )

        fu_date      = get_parsed_date_expr(followup_col)
        last_fu_date = get_parsed_date_expr(last_fu_col)
        dist_date    = get_parsed_date_expr(dist_col)

        # نأخذ فقط تاريخ المتابعة — لا نعتمد على آخر متابعة على العميل
        best_date = fu_date
        df = df.with_columns(best_date.alias("تاريخ المتابعة (Date)"))

        # ─── كولوم 2: تاريخ اليوم — TODAY() ─────────────────────────────────
        today = get_today()
        today_lit = pl.lit(today)
        df = df.with_columns(today_lit.alias("تاريخ اليوم"))

        # ─── كولوم 3: عدد أيام الإهمال = تاريخ اليوم - تاريخ المتابعة (Date) ─
        days_expr = (
            pl.when(pl.col("تاريخ المتابعة (Date)").is_null())
            .then(pl.lit(999))
            .otherwise((today_lit - pl.col("تاريخ المتابعة (Date)")).dt.total_days())
            .cast(pl.Int64)
        )
        df = df.with_columns(days_expr.alias(self.DAYS_COL))


        # ─── تحديد حالة الإهمال — قواعد الأولوية ────────────────────────────
        # الأولوية 1: المتابعة تحتوي "معاودة اتصال" → 1 يوم
        # الأولوية 2: سداد جزئي → 10 أيام
        # الأولوية 3: واعد + فرعية "طلب مهلة" → 7 أيام
        # الأولوية 4: واعد + أي فرعية أخرى → 3 أيام
        # الأولوية 5: حالة غير محددة أو فارغة → مهمل فوراً
        # الأولوية 6: أي حالة أخرى → 5 أيام

        days  = pl.col(self.DAYS_COL)
        smain = pl.col(status_main_col).cast(pl.String, strict=False).str.strip_chars()
        ssub  = pl.col(status_sub_col).cast(pl.String, strict=False).str.strip_chars().fill_null("")
        snote = pl.col(note_col).cast(pl.String, strict=False).str.strip_chars().fill_null("")

        # تصنيفات الحالة الرئيسية
        is_partial   = smain.str.contains("جزئي", literal=True) | smain.str.contains("جزئى", literal=True)
        is_promise   = smain.str.contains("واعد", literal=True) | smain.str.contains("وعد", literal=True)
        is_empty_status = smain.is_null() | (smain == "") | smain.is_in(["---", "-", "غير محدد"])

        # الأولوية 3: واعد + فرعية "طلب مهلة"
        is_promise_extension = is_promise & (
            ssub.str.contains("مهلة", literal=True) | ssub.str.contains("مهله", literal=True)
        )
        # الأولوية 4: واعد + أي فرعية أخرى (مش طلب مهلة)
        is_promise_other = is_promise & ~(
            ssub.str.contains("مهلة", literal=True) | ssub.str.contains("مهله", literal=True)
        )

        # الأولوية 1: المتابعة تحتوي على "معاودة اتصال"
        has_callback = snote.str.contains("معاودة اتصال", literal=True) | snote.str.contains("معاوده اتصال", literal=True)

        status_expr = (
            # أولوية 1: معاودة اتصال → مهلة يوم واحد
            pl.when(has_callback & (days > 1)).then(pl.lit("مهمل"))
            .when(has_callback).then(pl.lit("غير مهمل"))

            # أولوية 2: سداد جزئي → 10 أيام
            .when(is_partial & (days > 10)).then(pl.lit("مهمل"))
            .when(is_partial).then(pl.lit("غير مهمل"))

            # أولوية 3: واعد + طلب مهلة → 7 أيام
            .when(is_promise_extension & (days > 7)).then(pl.lit("مهمل"))
            .when(is_promise_extension).then(pl.lit("غير مهمل"))

            # أولوية 4: واعد + فرعية أخرى → 3 أيام
            .when(is_promise_other & (days > 3)).then(pl.lit("مهمل"))
            .when(is_promise_other).then(pl.lit("غير مهمل"))

            # أولوية 5: حالة فارغة أو غير محددة → مهمل فوراً
            .when(is_empty_status).then(pl.lit("مهمل"))

            # أي حالة أخرى → غير مهمل
            .otherwise(pl.lit("غير مهمل"))
        )
        df = df.with_columns(status_expr.alias(self.STATUS_COL))

        # ─── سادساً: فصل البيانات إلى شيتين ─────────────────────────────────
        # الشيت الأول: يحتوي على جميع العملاء (مهمل وغير مهمل)
        full_analysis = df.clone()

        # الشيت الثاني: يحتوي فقط على العملاء المهملين
        neglect_only = df.filter(pl.col(self.STATUS_COL) == "مهمل")


        # ─── المحاور الإحصائية (Pivots) على كامل بيانات الفلترة ──────────────
        piv_sup = self._build_pivot(full_analysis, supervisor_col)
        piv_col = self._build_pivot(full_analysis, collector_col)
        piv_status = self._build_pivot(full_analysis, status_main_col)
        
        # الفرع والمحفظة (إذا وجدا)
        branch_col = next((c for c in ["الفرع", "المنطقة", "Branch"] if c in df.columns), None)
        piv_branch = self._build_pivot(full_analysis, branch_col) if branch_col else pl.DataFrame()
        
        portfolio_col = next((c for c in ["المحفظة", "Portfolio"] if c in df.columns), None)
        piv_portfolio = self._build_pivot(full_analysis, portfolio_col) if portfolio_col else pl.DataFrame()

        # ملخص الإهمال الإجمالي
        piv_summary = (
            full_analysis.group_by(self.STATUS_COL)
            .len()
            .rename({"len": "عدد العملاء"})
        )
        total_len = len(full_analysis)
        if total_len > 0:
            piv_summary = piv_summary.with_columns(
                (pl.col("عدد العملاء") / total_len * 100).round(1).alias("النسبة %")
            )
        else:
            piv_summary = piv_summary.with_columns(pl.lit(0.0).alias("النسبة %"))

        # توزيع الأيام
        piv_days = (
            full_analysis.filter(pl.col(self.DAYS_COL).is_not_null())
            .group_by(self.DAYS_COL)
            .len()
            .rename({"len": "عدد العملاء"})
            .sort(self.DAYS_COL)
        )

        # الإحصائيات العامة
        neglected     = full_analysis.filter(pl.col(self.STATUS_COL) == "مهمل").height
        not_neglected = full_analysis.filter(pl.col(self.STATUS_COL) == "غير مهمل").height

        stats = {
            "إجمالي العملاء":       total_len,
            "مهمل":                  neglected,
            "غير مهمل":             not_neglected,
            "نسبة الإهمال %":        round(neglected / total_len * 100, 1) if total_len else 0.0,
            "عتبة الإهمال (أيام)":  5,
        }

        return {
            "data":             neglect_only,    # الشيت الثاني (مهمل فقط)
            "full_analysis":    full_analysis,   # الشيت الأول (مهمل وغير مهمل)
            "pivot_summary":    piv_summary,
            "pivot_supervisor": piv_sup,
            "pivot_collector":  piv_col,
            "pivot_status":     piv_status,
            "pivot_branch":     piv_branch,
            "pivot_portfolio":  piv_portfolio,
            "pivot_days":       piv_days,
            "stats":            stats,
        }

    # ── Pivot Builder ─────────────────────────────────────────────────────────

    def _build_pivot(self, df: pl.DataFrame, group_col: str) -> pl.DataFrame:
        if not group_col or group_col not in df.columns or len(df) == 0:
            return pl.DataFrame()

        try:
            pivot = (
                df.group_by([group_col, self.STATUS_COL])
                .len()
                .pivot(on=self.STATUS_COL, index=group_col, values="len")
                .fill_null(0)
            )

            for c in ["مهمل", "غير مهمل"]:
                if c not in pivot.columns:
                    pivot = pivot.with_columns(pl.lit(0).alias(c))

            pivot = pivot.with_columns(
                (pl.col("مهمل") + pl.col("غير مهمل")).alias("الإجمالي")
            )
            pivot = pivot.with_columns(
                (pl.col("مهمل") / pl.col("الإجمالي") * 100).round(1).alias("نسبة الإهمال %")
            )

            avg_days = (
                df.group_by(group_col)
                .agg(pl.col(self.DAYS_COL).mean().round(1).alias("متوسط أيام الإهمال"))
            )
            
            pivot = pivot.join(avg_days, on=group_col, how="left")
            return pivot
        except Exception as e:
            _log.warning("فشل إنشاء محور الإهمال لـ %s: %s", group_col, e)
            return pl.DataFrame()
