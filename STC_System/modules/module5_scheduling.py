"""
modules/module5_scheduling.py
─────────────────────────────
Module 5 — الجدولة (Scheduling) using Polars.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Dict

import polars as pl

from core.utils import get_today, parse_date

_log = logging.getLogger("Module5_Scheduling")


class SchedulingModule:

    def run(
        self,
        portfolio: pl.DataFrame,
        maharah: pl.DataFrame,
    ) -> Dict:
        _log.info("▶ تحليل الجدولة (Polars) (%d صف)", len(portfolio))

        if len(portfolio) == 0:
            return {
                "data": pl.DataFrame(),
                "pivot_type": pl.DataFrame(),
                "pivot_month": pl.DataFrame(),
                "pivot_year": pl.DataFrame(),
                "pivot_count": pl.DataFrame(),
                "pivot_supervisor": pl.DataFrame(),
                "stats": {"إجمالي العملاء": 0, "جدولة مؤكدة": 0, "احتمال": 0, "متعثر": 0}
            }

        # Helper to clean keys
        def clean_key(series: pl.Series) -> pl.Series:
            return (
                series.cast(pl.Utf8, strict=False)
                .fill_null("")
                .str.strip_chars()
                .str.replace(r"\.0+$", "")
                .str.replace_all(" ", "")
            )

        # 1. Clean portfolio keys
        p_clean = portfolio.clone()
        p_clean = p_clean.with_columns([
            clean_key(pl.col("رقم الحساب")).alias("رقم الحساب"),
            clean_key(pl.col("رقم المديونية")).alias("رقم المديونية"),
        ])

        # Find correct debt amount column name
        debt_amt_col = next((c for c in ["مبلغ الميدونية", "مبلغ المديونية"] if c in p_clean.columns), "مبلغ المديونية")

        # Parse portfolio numeric columns as float
        for col in [debt_amt_col, "السدادات الموثقة", "متبقي سداد موثق"]:
            if col in p_clean.columns:
                p_clean = p_clean.with_columns(
                    pl.col(col)
                    .cast(pl.Utf8, strict=False)
                    .str.replace_all(",", "")
                    .str.strip_chars()
                    .cast(pl.Float64, strict=False)
                    .fill_null(0.0)
                    .alias(col)
                )
            else:
                p_clean = p_clean.with_columns(pl.lit(0.0).alias(col))

        # 2. Add columns 1 & 2: نسبة السداد ونسبة المتبقي
        p_clean = p_clean.with_columns([
            pl.when(pl.col(debt_amt_col) > 0.0)
            .then((pl.col("السدادات الموثقة") / pl.col(debt_amt_col)) * 100.0)
            .otherwise(0.0)
            .alias("نسبة السداد"),

            pl.when(pl.col(debt_amt_col) > 0.0)
            .then((pl.col("متبقي سداد موثق") / pl.col(debt_amt_col)) * 100.0)
            .otherwise(0.0)
            .alias("نسبة المتبقي"),
        ])

        # 3. Clean maharah keys and parse payment date
        m_clean = maharah.clone()
        acc_col_maharah = "رقم الحساب" if "رقم الحساب" in m_clean.columns else "Account No."
        debt_col_maharah = "رقم المديونية" if "رقم المديونية" in m_clean.columns else "Debt No."
        amt_col_maharah = "مبلغ السداد" if "مبلغ السداد" in m_clean.columns else "Payment Amount"
        date_col_maharah = "تاريخ السداد" if "تاريخ السداد" in m_clean.columns else "Payment Date"

        # Ensure correct column existence
        for c, default in [(acc_col_maharah, "رقم الحساب"), (debt_col_maharah, "رقم المديونية"), 
                            (amt_col_maharah, "مبلغ السداد"), (date_col_maharah, "تاريخ السداد")]:
            if c not in m_clean.columns:
                m_clean = m_clean.with_columns(pl.lit("").alias(c))

        m_clean = m_clean.with_columns([
            clean_key(pl.col(acc_col_maharah)).alias("رقم الحساب"),
            clean_key(pl.col(debt_col_maharah)).alias("رقم المديونية"),
        ])

        # Parse maharah payment amount
        m_clean = m_clean.with_columns(
            pl.col(amt_col_maharah)
            .cast(pl.Utf8, strict=False)
            .str.replace_all(",", "")
            .str.strip_chars()
            .cast(pl.Float64, strict=False)
            .fill_null(0.0)
            .alias("مبلغ السداد")
        )

        # Standardize date column — vectorized بدون map_elements
        if date_col_maharah in m_clean.columns:
            raw = pl.col(date_col_maharah).cast(pl.String, strict=False).str.strip_chars()
            std_date = (
                raw.str.to_date("%Y-%m-%d", strict=False).fill_null(
                raw.str.to_date("%d/%m/%Y", strict=False).fill_null(
                raw.str.to_date("%d-%m-%Y", strict=False)))
            )
            m_clean = m_clean.with_columns(
                std_date.cast(pl.String).alias("_standardized_date")
            )
        else:
            m_clean = m_clean.with_columns(pl.lit(None).cast(pl.String).alias("_standardized_date"))

        # 4. Aggregate payments by رقم المديونية
        # count payments
        count_df = m_clean.filter(pl.col("رقم المديونية") != "").group_by("رقم المديونية").agg(
            pl.len().alias("عدد الدفعات")
        )

        # Sort ascending for oldest (first) payment
        oldest_df = (
            m_clean.filter((pl.col("رقم المديونية") != "") & (pl.col("_standardized_date").is_not_null()))
            .sort("_standardized_date", descending=False)
            .unique(subset=["رقم المديونية"], keep="first")
            .select([
                pl.col("رقم المديونية"),
                pl.col("_standardized_date").alias("تاريخ أول دفعة"),
                pl.col("مبلغ السداد").alias("مبلغ أول دفعة")
            ])
        )

        # Sort descending for newest (last) payment
        newest_df = (
            m_clean.filter((pl.col("رقم المديونية") != "") & (pl.col("_standardized_date").is_not_null()))
            .sort("_standardized_date", descending=True)
            .unique(subset=["رقم المديونية"], keep="first")
            .select([
                pl.col("رقم المديونية"),
                pl.col("_standardized_date").alias("تاريخ آخر دفعة"),
                pl.col("مبلغ السداد").alias("مبلغ آخر دفعة")
            ])
        )

        # Join the aggregations back to p_clean
        df_joined = p_clean.join(count_df, on="رقم المديونية", how="left")
        df_joined = df_joined.join(oldest_df, on="رقم المديونية", how="left")
        df_joined = df_joined.join(newest_df, on="رقم المديونية", how="left")

        # Fill missing count as 0
        df_joined = df_joined.with_columns(
            pl.col("عدد الدفعات").fill_null(0).cast(pl.Int32)
        )

        # Add year/month helper columns from date of last payment
        df_joined = df_joined.with_columns([
            pl.col("تاريخ آخر دفعة").str.slice(5, 2).cast(pl.Int32, strict=False).alias("_month_last"),
            pl.col("تاريخ آخر دفعة").str.slice(0, 4).cast(pl.Int32, strict=False).alias("_year_last"),
        ]).with_columns([
            pl.col("_month_last").cast(pl.String).fill_null("").alias("شهر آخر دفعة"),
            pl.col("_year_last").cast(pl.String).fill_null("").alias("سنة آخر دفعة"),
        ])

        # 5. Scheduling rules:
        # Determine "نوع الجدولة" on the records
        current_year = date.today().year

        df_joined = df_joined.with_columns(
            pl.when(pl.col("عدد الدفعات") == 0)
            .then(pl.lit("لا توجد دفعات"))
            .otherwise(
                pl.when(pl.col("نسبة السداد") > 100.0)
                .then(pl.lit("مستبعد (نسبة السداد > 100%)"))
                .otherwise(
                    pl.when(pl.col("نسبة المتبقي") == 0.0)
                    .then(pl.lit("مستبعد (نسبة المتبقي = 0)"))
                    .otherwise(
                        pl.when(pl.col("تاريخ آخر دفعة").is_null() | (pl.col("تاريخ آخر دفعة") == ""))
                        .then(pl.lit("مستبعد (تاريخ غير صالح)"))
                        .otherwise(
                            pl.when((pl.col("_year_last") == current_year) & (pl.col("_month_last") >= 10))
                            .then(pl.lit("جدولة مؤكدة"))
                            .otherwise(
                                pl.when((pl.col("_year_last") == current_year) & (pl.col("_month_last") < 10))
                                .then(pl.lit("احتمال"))
                                .otherwise(pl.lit("متعثر"))
                            )
                        )
                    )
                )
            )
            .alias("نوع الجدولة")
        )

        # Drop the temp helper columns
        df_joined = df_joined.drop(["_month_last", "_year_last"])

        # Pivot tables:
        # 1. عدد العملاء وإجمالي المديونية حسب نوع الجدولة
        piv_type = df_joined.group_by("نوع الجدولة").agg([
            pl.len().alias("عدد العملاء"),
            pl.col(debt_amt_col).sum().alias("إجمالي المديونية")
        ]).sort("نوع الجدولة")

        # 2. عدد العملاء حسب شهر آخر دفعة
        piv_month = df_joined.filter(pl.col("شهر آخر دفعة") != "").group_by("شهر آخر دفعة").agg([
            pl.len().alias("عدد العملاء")
        ]).sort("شهر آخر دفعة")

        # 3. عدد العملاء حسب سنة آخر دفعة
        piv_year = df_joined.filter(pl.col("سنة آخر دفعة") != "").group_by("سنة آخر دفعة").agg([
            pl.len().alias("عدد العملاء")
        ]).sort("سنة آخر دفعة")

        # 4. عدد العملاء حسب عدد الدفعات
        piv_count = df_joined.group_by("عدد الدفعات").agg([
            pl.len().alias("عدد العملاء")
        ]).sort("عدد الدفعات")

        piv_sup = self._build_group_pivot(df_joined, "المشرف")

        stats = {
            "إجمالي العملاء": len(df_joined),
            "جدولة مؤكدة": df_joined.filter(pl.col("نوع الجدولة") == "جدولة مؤكدة").height,
            "احتمال": df_joined.filter(pl.col("نوع الجدولة") == "احتمال").height,
            "متعثر": df_joined.filter(pl.col("نوع الجدولة") == "متعثر").height,
            "لا توجد دفعات": df_joined.filter(pl.col("نوع الجدولة") == "لا توجد دفعات").height,
        }

        return {
            "data": df_joined,
            "pivot_type": piv_type,
            "pivot_month": piv_month,
            "pivot_year": piv_year,
            "pivot_count": piv_count,
            "pivot_supervisor": piv_sup,
            "stats": stats,
        }

    def _build_group_pivot(self, df: pl.DataFrame, group_col: str) -> pl.DataFrame:
        if not group_col or group_col not in df.columns or len(df) == 0:
            return pl.DataFrame()

        try:
            pivot = (
                df.group_by([group_col, "نوع الجدولة"])
                .len()
                .pivot(on="نوع الجدولة", index=group_col, values="len")
                .fill_null(0)
            )
            # Add total column
            cols = [c for c in pivot.columns if c != group_col]
            if cols:
                pivot = pivot.with_columns(
                    sum(pl.col(c) for c in cols).alias("الإجمالي")
                )
            return pivot
        except Exception as e:
            _log.warning("فشل إنشاء المحور للجدولة لـ %s: %s", group_col, e)
            return pl.DataFrame()
