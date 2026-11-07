"""
modules/module6b_rotation.py
─────────────────────────────
Module 6B — السحب والتدوير الفعلي (Portfolio Rotation Execution) using Polars.

يقوم بـ:
1. استخراج عملاء المحصل/المحصلين المسحوب منهم (يدعم تحديد محصل واحد أو عدة محصلين مسحوبين معا)
2. تصفية الحالات الرئيسية المختارة لتوزيعها على المحصلين المستقبلين (Round Robin by رقم الهوية)
3. توجيه باقي الحالات غير المختارة إلى كود التحصيل الإلكتروني test.t
4. ضمان توحيد العميل بالكامل (عدم تكرار نفس العميل/الهوية مع أكثر من محصل)
5. إنتاج 3 تقارير: ملخص التوزيع، ملف التنفيذ، ملخص السحب
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Dict, List, Optional, Union

import polars as pl

from core.utils import get_today

_log = logging.getLogger("Module6B_Rotation")

# أعمدة المحفظة المعتمدة (Smart Detection)
_ID_COLS         = ["رقم الهوية", "الهوية"]
_BALANCE_COLS    = ["متبقي سداد موثق", "متبقي السداد الموثق", "متبقي سداد", "الرصيد المتبقي"]
_YEAR_COLS       = ["سنة التعثر", "سنة_التعثر"]
_SUPERVISOR_COLS = ["المشرف", "اسم المشرف"]
_COLLECTOR_COLS  = ["المحصل", "اسم المحصل", "الموظف"]
_USER_COLS       = ["اسم المستخدم", "اليوزر", "User", "user", "المستخدم"]
_MAIN_STATUS     = ["الحالة الرئيسية"]
_SUB_STATUS      = ["الحالة الفرعية"]


def _detect(df: pl.DataFrame, candidates: List[str]) -> Optional[str]:
    """إيجاد أول عمود مطابق من قائمة المرشحين."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


class PortfolioRotationModule:
    """تنفيذ عملية السحب والتدوير الفعلي."""

    @staticmethod
    def get_supervisors(portfolio: pl.DataFrame) -> List[str]:
        """استخراج قائمة المشرفين المتاحين من المحفظة"""
        sup_col = _detect(portfolio, _SUPERVISOR_COLS)
        if not sup_col or sup_col not in portfolio.columns:
            return []
        s = (
            portfolio[sup_col]
            .cast(pl.String, strict=False)
            .str.strip_chars()
            .drop_nulls()
            .unique()
            .sort()
        )
        return [v for v in s.to_list() if v and str(v).strip() != ""]

    @staticmethod
    def get_collectors_for_supervisor(portfolio: pl.DataFrame, supervisor_name: str) -> List[str]:
        """استخراج المحصلين التابعين لمشرف معين"""
        sup_col = _detect(portfolio, _SUPERVISOR_COLS)
        col_col = _detect(portfolio, _COLLECTOR_COLS)
        if not sup_col or not col_col or sup_col not in portfolio.columns or col_col not in portfolio.columns:
            return []
        mask = pl.col(sup_col).cast(pl.String).str.strip_chars() == str(supervisor_name).strip()
        s = (
            portfolio.filter(mask)[col_col]
            .cast(pl.String, strict=False)
            .str.strip_chars()
            .drop_nulls()
            .unique()
            .sort()
        )
        return [v for v in s.to_list() if v and str(v).strip() != ""]

    @staticmethod
    def get_main_statuses(portfolio: pl.DataFrame) -> List[str]:
        """استخراج قائمة الحالات الرئيسية المتاحة من المحفظة"""
        main_col = _detect(portfolio, _MAIN_STATUS)
        if not main_col or main_col not in portfolio.columns:
            return []
        s = (
            portfolio[main_col]
            .cast(pl.String, strict=False)
            .str.strip_chars()
            .drop_nulls()
            .unique()
            .sort()
        )
        return [v for v in s.to_list() if v and str(v).strip() != ""]

    def run(
        self,
        portfolio: pl.DataFrame,
        withdrawn_collector: Union[str, List[str]],
        supervisor_name: str,
        target_collectors: Optional[List[str]] = None,
        smart_assignment: bool = False,
        selected_main_statuses: Optional[List[str]] = None,
        electronic_code: str = "test.t",
    ) -> Dict:
        """
        تنفيذ السحب والتدوير.

        Parameters
        ----------
        portfolio              : DataFrame كامل ملف المحفظة الموزعة
        withdrawn_collector    : اسم المحصل أو قائمة المحصلين المراد سحب محافظهم
        supervisor_name        : اسم المشرف (لاستخراج المحصلين التابعين له)
        target_collectors      : قائمة المحصلين المستقبلين المراد التوزيع عليهم (اختياري)
        smart_assignment       : تفعيل التوجيه الذكي (opertaions/test)
        selected_main_statuses : قائمة الحالات الرئيسية المراد توزيعها على المحصلين المستقبلين (الباقي يذهب للتحصيل الإلكتروني test.t)
        electronic_code        : كود التحصيل الإلكتروني للحالات غير المختارة (افتراضياً test.t)
        """
        if isinstance(withdrawn_collector, list):
            withdrawn_list = [str(c).strip() for c in withdrawn_collector if c and str(c).strip()]
        else:
            withdrawn_list = [str(withdrawn_collector).strip()] if withdrawn_collector else []

        withdrawn_str = ", ".join(withdrawn_list)
        _log.info("▶ بدء السحب والتدوير — المحصلون المسحوبون: %s — المشرف: %s",
                  withdrawn_str, supervisor_name)

        # ── الكشف التلقائي عن الأعمدة ────────────────────────────────────────
        id_col   = _detect(portfolio, _ID_COLS)
        bal_col  = _detect(portfolio, _BALANCE_COLS)
        yr_col   = _detect(portfolio, _YEAR_COLS)
        sup_col  = _detect(portfolio, _SUPERVISOR_COLS)
        col_col  = _detect(portfolio, _COLLECTOR_COLS)
        usr_col  = _detect(portfolio, _USER_COLS)
        main_col = _detect(portfolio, _MAIN_STATUS)
        sub_col  = _detect(portfolio, _SUB_STATUS)

        if not col_col:
            raise ValueError("لم يتم العثور على عمود المحصل في المحفظة")
        if not id_col:
            raise ValueError("لم يتم العثور على عمود رقم الهوية في المحفظة")

        df = portfolio.clone()

        # ── استخراج عملاء المحصلين المسحوبين ─────────────────────────────────
        withdrawn_df = df.filter(
            pl.col(col_col).cast(pl.String).str.strip_chars().is_in(withdrawn_list)
        )
        _log.info("  📋 عدد سجلات المحصلين المسحوبين: %d", len(withdrawn_df))

        if len(withdrawn_df) == 0:
            raise ValueError(f"لا توجد سجلات للمحصلين المحددين: {withdrawn_str}")

        # ── إضافة عمود "إجمالي العميل" (SUMIF by رقم الهوية) ─────────────────
        if bal_col:
            bal_expr = (
                pl.col(bal_col)
                .cast(pl.String, strict=False)
                .str.replace_all(",", "")
                .str.strip_chars()
                .cast(pl.Float64, strict=False)
                .fill_null(0.0)
            )
            withdrawn_df = withdrawn_df.with_columns(bal_expr.alias("_bal_clean"))
            withdrawn_df = withdrawn_df.with_columns(
                pl.col("_bal_clean").sum().over(id_col).alias("إجمالي العميل")
            )
        else:
            withdrawn_df = withdrawn_df.with_columns(pl.lit(0.0).alias("إجمالي العميل"))

        # ── عمود "سنة التعثر" ─────────────────────────────────────────────────
        if yr_col:
            withdrawn_df = withdrawn_df.with_columns(
                pl.col(yr_col)
                .cast(pl.String, strict=False)
                .str.strip_chars()
                .cast(pl.Int32, strict=False)
                .fill_null(9999)
                .alias("سنة التعثر")
            )
        else:
            withdrawn_df = withdrawn_df.with_columns(pl.lit(9999).cast(pl.Int32).alias("سنة التعثر"))

        # ── قائمة المحصلين المتاحين (المستقبلين) ──────────────────────────────
        withdrawn_set = set(withdrawn_list)
        if target_collectors and len(target_collectors) > 0:
            collectors_pool = [c.strip() for c in target_collectors if c and c.strip() not in withdrawn_set]
        elif sup_col:
            sup_mask = pl.col(sup_col).cast(pl.String).str.strip_chars() == supervisor_name.strip()
            collectors_pool: List[str] = (
                df.filter(sup_mask)
                .select(col_col)
                .unique()
                .to_series()
                .cast(pl.String)
                .str.strip_chars()
                .to_list()
            )
            collectors_pool = [
                c for c in collectors_pool
                if c.strip() not in withdrawn_set
            ]
        else:
            collectors_pool = []

        collectors_pool = sorted(list(set(collectors_pool)))  # فريدة ومترتبة أبجدياً
        _log.info("  👥 المحصلون المستقبلون المتاحون (%d): %s", len(collectors_pool), collectors_pool)

        if not collectors_pool and (not selected_main_statuses or len(selected_main_statuses) > 0):
            # If no target collectors and we need to distribute some statuses
            if not selected_main_statuses or len(selected_main_statuses) > 0:
                raise ValueError(
                    f"لم يتم العثور على محصلين مستقبلين متاحين لنقل المحفظة إليهم!"
                )

        # ── 1. تحديد المشرف التابع له كل محصل مستقبل ────────────────────────
        sup_map = {}
        if sup_col and col_col:
            sup_pairs = (
                df.select([col_col, sup_col])
                .unique(subset=[col_col])
                .with_columns([
                    pl.col(col_col).cast(pl.String).str.strip_chars(),
                    pl.col(sup_col).cast(pl.String).str.strip_chars(),
                ])
            )
            for r in sup_pairs.iter_rows():
                if r[0]:
                    sup_map[r[0]] = r[1]

        # ── 2. تحديد العملاء المستهدفين للتوزيع والعملاء المحولين للتحصيل الإلكتروني ──
        # قاعدة توحيد العميل: كل رقم هوية يسند بالكامل لجهة واحدة فقط لمنع التكرار
        unique_ids = (
            withdrawn_df
            .select([id_col, "إجمالي العميل", "سنة التعثر"])
            .unique(subset=[id_col])
            .sort(["سنة التعثر", "إجمالي العميل"], descending=[False, True])
        )

        n_customers = len(unique_ids)
        assignments = {}

        # إذا حدد المستخدم حالات رئيسية معينة للتوزيع
        if selected_main_statuses is not None and main_col and main_col in withdrawn_df.columns:
            selected_statuses_set = set([str(s).strip() for s in selected_main_statuses if str(s).strip()])
            
            # استخراج الهويات التي لديها على الأقل مديونية واحدة ضمن الحالات المختارة
            matching_ids = (
                withdrawn_df.filter(
                    pl.col(main_col).cast(pl.String).str.strip_chars().is_in(list(selected_statuses_set))
                )
                .select(id_col)
                .unique()
                .get_column(id_col)
                .cast(pl.String)
                .to_list()
            )
            matching_ids_set = set(matching_ids)

            dist_unique_ids = unique_ids.filter(
                pl.col(id_col).cast(pl.String).is_in(list(matching_ids_set))
            )
            elec_unique_ids = unique_ids.filter(
                ~pl.col(id_col).cast(pl.String).is_in(list(matching_ids_set))
            )

            # توزيع الهويات المختارة على المحصلين المستقبلين بالتساوي
            n_collectors = len(collectors_pool) if collectors_pool else 1
            for i, row in enumerate(dist_unique_ids.iter_rows()):
                if collectors_pool:
                    assignments[str(row[0])] = collectors_pool[i % n_collectors]
                else:
                    assignments[str(row[0])] = electronic_code

            # باقي الهويات التي لا تحتوي على أي حالة مختارة تسند للتحصيل الإلكتروني
            for row in elec_unique_ids.iter_rows():
                assignments[str(row[0])] = electronic_code

        else:
            # التوزيع العادي لكامل الهويات
            n_collectors = len(collectors_pool)
            for i, row in enumerate(unique_ids.iter_rows()):
                assignments[str(row[0])] = collectors_pool[i % n_collectors]

        id_series = unique_ids.get_column(id_col).cast(pl.String)
        col_assigned = pl.Series(
            "التوزيع",
            [assignments.get(str(i), electronic_code) for i in id_series.to_list()]
        )
        assign_df = pl.DataFrame({
            id_col: id_series,
            "التوزيع": col_assigned,
        })

        # ── 3. Join التوزيع الابتدائي على مستوى العميل (ضمان عدم تكرار العميل) ─
        withdrawn_df = withdrawn_df.with_columns(
            pl.col(id_col).cast(pl.String).alias(id_col)
        )
        assign_df = assign_df.with_columns(
            pl.col(id_col).cast(pl.String)
        )
        withdrawn_df = withdrawn_df.join(assign_df.select([id_col, "التوزيع"]),
                                         on=id_col, how="left")
        withdrawn_df = withdrawn_df.rename({"التوزيع": "المحصل الجديد"})

        # ── 4. عمود اليوزر الجديد الابتدائي (XLOOKUP: المحصل الجديد → اليوزر) ─
        if usr_col:
            user_map = (
                df.select([col_col, usr_col])
                .unique(subset=[col_col])
                .with_columns([
                    pl.col(col_col).cast(pl.String).str.strip_chars(),
                    pl.col(usr_col).cast(pl.String).str.strip_chars(),
                ])
            )
            withdrawn_df = withdrawn_df.join(
                user_map.rename({col_col: "المحصل الجديد", usr_col: "اليوزر الجديد"}),
                on="المحصل الجديد",
                how="left",
            )
        else:
            withdrawn_df = withdrawn_df.with_columns(pl.lit("").alias("اليوزر الجديد"))

        # إذا كان المحصل الجديد هو كود التحصيل الإلكتروني -> اليوزر والمشرف
        is_electronic = pl.col("المحصل الجديد") == electronic_code
        withdrawn_df = withdrawn_df.with_columns([
            pl.when(is_electronic)
            .then(pl.lit(electronic_code))
            .otherwise(pl.col("اليوزر الجديد"))
            .alias("اليوزر الجديد")
        ])

        # ── 5. تطبيق قواعد التعيين الذكي (في حال تفعيل الخيار الذكي) ─────────
        if smart_assignment:
            neg_keywords = [
                "عدم توصل", "عدم التوصل", "مسجون", "متوفي", "متوفى",
                "رافض", "لايرد", "لا يرد", "مقطوع", "مغلق", "غير متاح",
                "إهمال", "اهمال", "سلب", "غير مهتم", "الرقم غير", "لا يخص"
            ]

            status_text_expr = pl.lit("")
            if main_col and main_col in withdrawn_df.columns:
                status_text_expr = status_text_expr + pl.col(main_col).fill_null("").cast(pl.String)
            if sub_col and sub_col in withdrawn_df.columns:
                status_text_expr = status_text_expr + " " + pl.col(sub_col).fill_null("").cast(pl.String)

            is_zero_bal = pl.col("إجمالي العميل") <= 0

            # فحص وجود أي كلمة سلبية
            is_negative = pl.lit(False)
            for kw in neg_keywords:
                is_negative = is_negative | status_text_expr.str.contains(kw)

            withdrawn_df = withdrawn_df.with_columns([
                pl.when(is_zero_bal)
                .then(pl.lit("opertaions"))
                .otherwise(pl.col("المحصل الجديد"))
                .alias("المحصل الجديد"),

                pl.when(is_zero_bal)
                .then(pl.lit("opertaions"))
                .when(is_negative & ~is_electronic)
                .then(pl.lit("test"))
                .otherwise(pl.col("اليوزر الجديد"))
                .alias("اليوزر الجديد"),
            ])

        # تحديث المشرف الجديد حسب المشرف الفعلي للمحصل الجديد أو إلكتروني
        if sup_col and sup_col in withdrawn_df.columns:
            def resolve_sup(c_name):
                c_str = str(c_name).strip()
                if c_str == electronic_code:
                    return "تحصيل إلكتروني"
                if c_str == "opertaions":
                    return "opertaions"
                return sup_map.get(c_str, supervisor_name)

            withdrawn_df = withdrawn_df.with_columns(
                pl.col("المحصل الجديد").map_elements(resolve_sup, return_dtype=pl.String).alias("المشرف الجديد")
            )
        else:
            withdrawn_df = withdrawn_df.with_columns(
                pl.when(is_electronic)
                .then(pl.lit("تحصيل إلكتروني"))
                .otherwise(pl.lit(supervisor_name))
                .alias("المشرف الجديد")
            )

        # ── الفرز النهائي ─────────────────────────────────────────────────────
        sort_cols   = []
        sort_descs  = []
        if main_col and main_col in withdrawn_df.columns:
            sort_cols.append(main_col);  sort_descs.append(False)
        if sub_col  and sub_col  in withdrawn_df.columns:
            sort_cols.append(sub_col);   sort_descs.append(False)
        sort_cols.append("سنة التعثر");  sort_descs.append(False)
        sort_cols.append("إجمالي العميل"); sort_descs.append(True)

        withdrawn_df = withdrawn_df.sort(sort_cols, descending=sort_descs)

        if "_bal_clean" in withdrawn_df.columns:
            withdrawn_df = withdrawn_df.drop("_bal_clean")

        # ── ملف التنفيذ ───────────────────────────────────────────────────────
        exec_cols = [id_col, "اسم العميل", "المحصل الجديد", "اليوزر الجديد", "المشرف الجديد"] \
            if "اسم العميل" in withdrawn_df.columns \
            else [id_col, "المحصل الجديد", "اليوزر الجديد", "المشرف الجديد"]
        execution_report = (
            withdrawn_df
            .select([c for c in exec_cols if c in withdrawn_df.columns])
            .unique(subset=[id_col])
            .sort(id_col)
        )

        # ── ملخص التوزيع ─────────────────────────────────────────────────────
        dist_agg = (
            withdrawn_df
            .unique(subset=[id_col])
            .group_by("المحصل الجديد")
            .agg([
                pl.len().cast(pl.Int64).alias("عدد العملاء"),
                pl.col("إجمالي العميل").sum().round(2).alias("إجمالي متبقي السداد"),
                pl.col("إجمالي العميل").mean().round(2).alias("متوسط قيمة العميل"),
            ])
            .sort("عدد العملاء", descending=True)
        )

        total_row_dist = pl.DataFrame({
            "المحصل الجديد": ["📈 الإجمالي"],
            "عدد العملاء": [int(n_customers)],
            "إجمالي متبقي السداد": [round(unique_ids.get_column("إجمالي العميل").sum(), 2)],
            "متوسط قيمة العميل": [round(unique_ids.get_column("إجمالي العميل").mean(), 2) if n_customers > 0 else 0.0],
        })
        distribution_summary = pl.concat([dist_agg, total_row_dist])

        # ── ملخص السحب ───────────────────────────────────────────────────────
        withdrawn_agg = (
            withdrawn_df
            .unique(subset=[id_col])
            .group_by(col_col)
            .agg([
                pl.len().cast(pl.Int64).alias("عدد العملاء المسحوبين"),
                pl.col("إجمالي العميل").sum().round(2).alias("إجمالي المبالغ المسحوبة"),
            ])
            .rename({col_col: "المحصل المسحوب منه"})
            .sort("عدد العملاء المسحوبين", descending=True)
        )

        total_row_with = pl.DataFrame({
            "المحصل المسحوب منه": ["📉 الإجمالي"],
            "عدد العملاء المسحوبين": [int(n_customers)],
            "إجمالي المبالغ المسحوبة": [round(unique_ids.get_column("إجمالي العميل").sum(), 2)],
        })
        withdrawal_summary = pl.concat([withdrawn_agg, total_row_with])

        n_dest_collectors = len([c for c in collectors_pool if c != electronic_code])
        stats = {
            "المحصل المسحوب منه":  withdrawn_str,
            "المشرف المسؤول":      supervisor_name,
            "عدد السجلات المسحوبة": len(withdrawn_df),
            "عدد العملاء (هوية)":  n_customers,
            "عدد المحصلين المستلمين": n_dest_collectors,
            "متوسط عملاء/محصل":   round(n_customers / n_dest_collectors, 1) if n_dest_collectors > 0 else 0,
        }

        _log.info("  ✅ اكتمل السحب والتدوير بنجاح — %d سجل، %d عميل", len(withdrawn_df), n_customers)

        return {
            "data":                 withdrawn_df,
            "execution_report":     execution_report,
            "distribution_summary": distribution_summary,
            "withdrawal_summary":   withdrawal_summary,
            "stats":                stats,
        }
