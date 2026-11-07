"""
modules/module4_payments.py
───────────────────────────
Module 4 — السدادات والتسوية (Payments & Reconciliation) using Polars.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Dict

import polars as pl

_log = logging.getLogger("Module4_Payments")


class PaymentsModule:

    def __init__(self):
        self.company_processed_all = pl.DataFrame()

    def run(
        self,
        portfolio: pl.DataFrame,
        maharah: pl.DataFrame,
        company: pl.DataFrame,
    ) -> Dict:
        _log.info("▶ تحليل السدادات والتسوية (Polars)")

        # Helper to clean keys
        def clean_key(series: pl.Series) -> pl.Series:
            return (
                series.cast(pl.Utf8, strict=False)
                .fill_null("")
                .str.strip_chars()
                .str.replace(r"\.0+$", "")
                .str.replace_all(" ", "")
            )

        acc_col_company = "Account No." if "Account No." in company.columns else "رقم الحساب"
        acc_col_maharah = "رقم الحساب" if "رقم الحساب" in maharah.columns else "Account No."

        # Clean keys on all inputs to ensure 100% correct joins
        if "رقم الحساب" in portfolio.columns:
            portfolio = portfolio.with_columns(clean_key(pl.col("رقم الحساب")).alias("رقم الحساب"))
        if "رقم المديونية" in portfolio.columns:
            portfolio = portfolio.with_columns(clean_key(pl.col("رقم المديونية")).alias("رقم المديونية"))
        if "رقم الهوية" in portfolio.columns:
            portfolio = portfolio.with_columns(clean_key(pl.col("رقم الهوية")).alias("رقم الهوية"))
        if "الهوية" in portfolio.columns:
            portfolio = portfolio.with_columns(clean_key(pl.col("الهوية")).alias("الهوية"))

        if acc_col_company in company.columns:
            company = company.with_columns(clean_key(pl.col(acc_col_company)).alias(acc_col_company))
        
        if acc_col_maharah in maharah.columns:
            maharah = maharah.with_columns(clean_key(pl.col(acc_col_maharah)).alias(acc_col_maharah))
        if "رقم المديونية" in maharah.columns:
            maharah = maharah.with_columns(clean_key(pl.col("رقم المديونية")).alias("رقم المديونية"))

        # Run steps
        step1 = self._step1_addition(portfolio, maharah, company)
        step2 = self._step2_settlement(portfolio, company)
        step3 = self._step3_edit_delete(portfolio, maharah, company)

        stats = {
            **step1["stats"],
            **step2["stats"],
            **step3["stats"],
        }

        return {
            "addition_data":    step1["data"],
            "settlement_data":  step2["data"],
            "edit_delete_data": step3["data"],
            "stats":            stats,
        }

    # ── Step 1: Addition ──────────────────────────────────────────────────────

    def _step1_addition(
        self,
        portfolio: pl.DataFrame,
        maharah: pl.DataFrame,
        company: pl.DataFrame,
    ) -> Dict:
        acc_col_company = "Account No." if "Account No." in company.columns else "رقم الحساب"
        amt_col_company = "Payment Amount" if "Payment Amount" in company.columns else "مبلغ السداد"

        # 1. Working copy and clean amount
        company_cleaned = company.clone().with_columns(
            pl.col(amt_col_company)
            .str.replace_all(",", "")
            .str.strip_chars()
            .cast(pl.Float64, strict=False)
            .fill_null(0.0)
            .alias(amt_col_company)
        )

        # 2. Group by Account Number and SUMIF
        company_sums = company_cleaned.group_by(acc_col_company).agg(
            pl.col(amt_col_company).sum().alias("_total_company_payment")
        )
        company_processed = company_cleaned.join(company_sums, on=acc_col_company, how="left").with_columns(
            pl.col("_total_company_payment").alias(amt_col_company)
        ).drop("_total_company_payment")

        # Remove duplicate Account Numbers
        company_unique = company_processed.unique(subset=[acc_col_company], keep="first")

        # 3. Create: مهارة, الفرق, الملاحظة
        acc_col_maharah = "رقم الحساب" if "رقم الحساب" in maharah.columns else "Account No."
        amt_col_maharah = "مبلغ السداد" if "مبلغ السداد" in maharah.columns else "Payment Amount"

        maharah_sums = maharah.with_columns(
            pl.col(amt_col_maharah)
            .str.replace_all(",", "")
            .str.strip_chars()
            .cast(pl.Float64, strict=False)
            .fill_null(0.0)
            .alias(amt_col_maharah)
        ).group_by(acc_col_maharah).agg(
            pl.col(amt_col_maharah).sum().alias("مهارة")
        )

        company_unique = company_unique.join(
            maharah_sums,
            left_on=acc_col_company,
            right_on=acc_col_maharah,
            how="left"
        ).with_columns(
            pl.col("مهارة").fill_null(0.0)
        )

        company_unique = company_unique.rename({amt_col_company: "الشركة"})

        # Difference = مهارة - الشركة
        company_unique = company_unique.with_columns(
            (pl.col("مهارة") - pl.col("الشركة")).alias("الفرق")
        ).with_columns(
            pl.when(pl.col("الفرق") < 0.0).then(pl.lit("مراجعة"))
            .otherwise(
                pl.when(pl.col("الفرق") == 0.0).then(pl.lit("مطابق"))
                .otherwise(pl.lit("إضافة"))
            )
            .alias("الملاحظة")
        )

        # Store for Step 3
        self.company_processed_all = company_unique

        # 4. Filter only for 'إضافة'
        addition_df = company_unique.filter(pl.col("الملاحظة") == "إضافة")

        # 5. Append columns from portfolio
        port_cols = portfolio.columns
        lookup_mappings = {
            "المشرف": "المشرف",
            "المحصل": "المحصل",
            "الحالة الرئيسية": "الحالة الرئيسية",
            "الحالة الفرعية": "الحالة الفرعية",
            "اسم المستخدم": "اسم المستخدم",
        }
        
        if "المحفظة" in port_cols:
            lookup_mappings["المحفظة"] = "المحفظة"
        elif "اسم الحاوية" in port_cols:
            lookup_mappings["المحفظة"] = "اسم الحاوية"

        select_cols = ["رقم الحساب"]
        rename_dict = {}
        for target, source in lookup_mappings.items():
            if source in port_cols:
                select_cols.append(source)
                if source != target:
                    rename_dict[source] = target

        portfolio_slim = portfolio.select(select_cols).unique(subset=["رقم الحساب"], keep="first")
        if rename_dict:
            portfolio_slim = portfolio_slim.rename(rename_dict)

        addition_df = addition_df.join(
            portfolio_slim,
            left_on=acc_col_company,
            right_on="رقم الحساب",
            how="left"
        )

        # Make sure all requested columns exist
        requested_cols = ["المشرف", "المحصل", "الحالة الرئيسية", "الحالة الفرعية", "اسم المستخدم", "المحفظة"]
        for c in requested_cols:
            if c not in addition_df.columns:
                addition_df = addition_df.with_columns(pl.lit("").alias(c))

        stats = {
            "إجمالي السدادات (الإضافة)": len(addition_df),
            "إضافة":  addition_df.height,
            "مطابق":  company_unique.filter(pl.col("الملاحظة") == "مطابق").height,
            "مراجعة": company_unique.filter(pl.col("الملاحظة") == "مراجعة").height,
        }

        return {"data": addition_df, "stats": stats}

    # ── Step 2: Settlement ────────────────────────────────────────────────────

    def _step2_settlement(self, portfolio: pl.DataFrame, company: pl.DataFrame) -> Dict:
        acc_col_company = "Account No." if "Account No." in company.columns else "رقم الحساب"
        bal_col_company = "Current Balance Due" if "Current Balance Due" in company.columns else "متبقي سداد موثق"

        settlement_df = company.clone()

        if bal_col_company in settlement_df.columns:
            settlement_df = settlement_df.with_columns(
                pl.col(bal_col_company)
                .str.replace_all(",", "")
                .str.strip_chars()
                .cast(pl.Float64, strict=False)
                .fill_null(0.0)
                .alias(bal_col_company)
            )
            settlement_df = settlement_df.with_columns(
                pl.when(pl.col(bal_col_company) <= 0.0)
                .then(pl.lit("تسوية كاملة"))
                .otherwise(pl.lit("تسوية جزئية"))
                .alias("نوع التسوية")
            )
        else:
            settlement_df = settlement_df.with_columns(
                pl.lit("تسوية جزئية").alias("نوع التسوية")
            )

        port_cols = portfolio.columns
        select_cols = ["رقم الحساب"]
        rename_dict = {}

        if "المشرف" in port_cols:
            select_cols.append("المشرف")
        if "المحصل" in port_cols:
            select_cols.append("المحصل")
        if "السدادات الموثقة" in port_cols:
            select_cols.append("السدادات الموثقة")
            rename_dict["السدادات الموثقة"] = "مبلغ السداد الموثق"

        portfolio_settle = portfolio.select(select_cols).unique(subset=["رقم الحساب"], keep="first")
        if rename_dict:
            portfolio_settle = portfolio_settle.rename(rename_dict)

        settlement_df = settlement_df.join(
            portfolio_settle,
            left_on=acc_col_company,
            right_on="رقم الحساب",
            how="left"
        )

        for c in ["المشرف", "المحصل", "مبلغ السداد الموثق"]:
            if c not in settlement_df.columns:
                settlement_df = settlement_df.with_columns(pl.lit(0.0 if c == "مبلغ السداد الموثق" else "").alias(c))

        settlement_df = settlement_df.with_columns(
            pl.col("مبلغ السداد الموثق")
            .cast(pl.Utf8, strict=False)
            .str.replace_all(",", "")
            .str.strip_chars()
            .cast(pl.Float64, strict=False)
            .fill_null(0.0)
            .alias("مبلغ السداد الموثق")
        )

        if bal_col_company in settlement_df.columns:
            settlement_df = settlement_df.with_columns(
                (pl.col(bal_col_company) + pl.col("مبلغ السداد الموثق")).alias("مبلغ التعديل")
            )
        else:
            settlement_df = settlement_df.with_columns(
                pl.col("مبلغ السداد الموثق").alias("مبلغ التعديل")
            )

        stats = {
            "تسوية كاملة":  settlement_df.filter(pl.col("نوع التسوية") == "تسوية كاملة").height,
            "تسوية جزئية": settlement_df.filter(pl.col("نوع التسوية") == "تسوية جزئية").height,
        }

        return {"data": settlement_df, "stats": stats}

    # ── Step 3: Edit / Delete ─────────────────────────────────────────────────

    def _step3_edit_delete(
        self,
        portfolio: pl.DataFrame,
        maharah: pl.DataFrame,
        company: pl.DataFrame,
    ) -> Dict:
        if len(self.company_processed_all) == 0:
            return {
                "data": pl.DataFrame(),
                "stats": {"إجمالي المراجعة": 0, "قرار مطابق": 0, "قرار تعديل": 0, "قرار حذف": 0}
            }

        acc_col_company = "Account No." if "Account No." in company.columns else "رقم الحساب"

        company_notes = self.company_processed_all.select([
            pl.col(acc_col_company).alias("__acc__"),
            pl.col("الملاحظة").alias("ملاحظة_شركة")
        ])

        portfolio_with_notes = portfolio.join(
            company_notes,
            left_on="رقم الحساب",
            right_on="__acc__",
            how="left"
        ).with_columns(
            pl.col("ملاحظة_شركة").fill_null("#N/A")
        )

        edit_delete_df = portfolio_with_notes.filter(
            (pl.col("ملاحظة_شركة") == "مراجعة") | (pl.col("ملاحظة_شركة") == "#N/A")
        ).rename({"ملاحظة_شركة": "ملاحظة الشركة"})

        if len(edit_delete_df) == 0:
            return {
                "data": pl.DataFrame(),
                "stats": {"إجمالي المراجعة": 0, "قرار مطابق": 0, "قرار تعديل": 0, "قرار حذف": 0}
            }

        id_col = next((c for c in ["رقم الهوية", "الهوية", "National ID"] if c in edit_delete_df.columns), None)
        if id_col:
            edit_delete_df = edit_delete_df.sort(id_col)
            edit_delete_df = edit_delete_df.with_columns(
                pl.col(id_col).is_duplicated().alias("تكرار")
            )
        else:
            edit_delete_df = edit_delete_df.with_columns(pl.lit(False).alias("تكرار"))

        acc_col_maharah = "رقم الحساب" if "رقم الحساب" in maharah.columns else "Account No."
        amt_col_maharah = "مبلغ السداد" if "مبلغ السداد" in maharah.columns else "Payment Amount"

        maharah_sums = maharah.with_columns(
            pl.col(amt_col_maharah)
            .str.replace_all(",", "")
            .str.strip_chars()
            .cast(pl.Float64, strict=False)
            .fill_null(0.0)
            .alias(amt_col_maharah)
        ).group_by(acc_col_maharah).agg(
            pl.col(amt_col_maharah).sum().alias("مهارة")
        )

        amt_col_company = "Payment Amount" if "Payment Amount" in company.columns else "مبلغ السداد"
        company_sums = company.with_columns(
            pl.col(amt_col_company)
            .str.replace_all(",", "")
            .str.strip_chars()
            .cast(pl.Float64, strict=False)
            .fill_null(0.0)
            .alias(amt_col_company)
        ).group_by(acc_col_company).agg(
            pl.col(amt_col_company).sum().alias("الشركة")
        )

        edit_delete_df = edit_delete_df.join(
            maharah_sums,
            left_on="رقم الحساب",
            right_on=acc_col_maharah,
            how="left"
        ).with_columns(
            pl.col("مهارة").fill_null(0.0)
        )

        edit_delete_df = edit_delete_df.join(
            company_sums,
            left_on="رقم الحساب",
            right_on=acc_col_company,
            how="left"
        ).with_columns(
            pl.col("الشركة").fill_null(0.0)
        )

        edit_delete_df = edit_delete_df.with_columns(
            (pl.col("مهارة") - pl.col("الشركة")).alias("الفرق")
        )

        edit_delete_df = edit_delete_df.with_columns(
            pl.when(pl.col("الشركة") == 0.0)
            .then(pl.lit("حذف"))
            .otherwise(
                pl.when(pl.col("الفرق") == 0.0).then(pl.lit("مطابق"))
                .otherwise(pl.lit("تعديل"))
            )
            .alias("الإجراء")
        ).with_columns(
            pl.when(pl.col("الإجراء") == "تعديل")
            .then(pl.col("الشركة"))
            .otherwise(pl.lit(None))
            .alias("مبلغ التعديل")
        )

        stats = {
            "إجمالي المراجعة":     len(edit_delete_df),
            "قرار مطابق":          edit_delete_df.filter(pl.col("الإجراء") == "مطابق").height,
            "قرار تعديل":          edit_delete_df.filter(pl.col("الإجراء") == "تعديل").height,
            "قرار حذف":            edit_delete_df.filter(pl.col("الإجراء") == "حذف").height,
        }

        if "الإجراء" in edit_delete_df.columns:
            edit_delete_df = edit_delete_df.with_columns(
                pl.col("الإجراء").alias("القرار")
            )

        return {"data": edit_delete_df, "stats": stats}
