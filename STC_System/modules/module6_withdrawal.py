"""
modules/module6_withdrawal.py
─────────────────────────────
Module 6 — السحب والتدوير (Withdrawal & Rotation) using Polars.
"""
from __future__ import annotations

import logging
from typing import Dict

import polars as pl

from core.utils import get_today, parse_date, days_since

_log = logging.getLogger("Module6_Withdrawal")

WITHDRAW_THRESHOLD_DAYS     = 30
MISSED_PROMISE_THRESHOLD    = 3

WITHDRAW   = "يُسحب"
KEEP       = "يُبقى"


class WithdrawalRotationModule:
    REC_COL    = "توصية السحب"
    REASON_COL = "سبب السحب"

    def run(
        self,
        portfolio: pl.DataFrame,
        promise: pl.DataFrame,
    ) -> Dict:
        _log.info("▶ تحليل السحب والتدوير (Polars) (%d صف)", len(portfolio))
        df = portfolio.clone()

        # 1. Enrich with expired promise counts
        df = self._enrich_promise_stats(df, promise)

        # 2. Calculate days without contact — vectorized
        followup_candidates = ["تاريخ المتابعة", "أخر متابعة للعميل", "آخر متابعة على العميل", "تاريخ الحالة", "آخر متابعة"]
        followup_col = next((c for c in followup_candidates if c in df.columns), None)
        if followup_col:
            today_lit = pl.lit(get_today())
            fu_str = pl.col(followup_col).cast(pl.String, strict=False).str.strip_chars().str.replace(r"\s+.*$", "")
            fu_date = (
                fu_str.str.to_date("%m/%d/%Y", strict=False)
                .fill_null(fu_str.str.to_date("%Y-%m-%d", strict=False))
                .fill_null(fu_str.str.to_date("%d/%m/%Y", strict=False))
                .fill_null(fu_str.str.to_date("%Y/%m/%d", strict=False))
                .fill_null(fu_str.str.to_date("%d-%m-%Y", strict=False))
                .fill_null(fu_str.str.to_date("%m-%d-%Y", strict=False))
            )
            df = df.with_columns(
                pl.when(fu_date.is_null())
                  .then(pl.lit(None).cast(pl.Int64))
                  .otherwise((today_lit - fu_date).dt.total_days().cast(pl.Int64))
                  .alias("عدد أيام بدون تواصل")
            )
        else:
            df = df.with_columns(pl.lit(None).cast(pl.Int64).alias("عدد أيام بدون تواصل"))

        # 3. Vectorized withdrawal evaluation — fully vectorized بدون map_elements
        missed = pl.col("عدد الوعود المنتهية").fill_null(0)
        days   = pl.col("عدد أيام بدون تواصل")

        is_many_missed  = missed >= MISSED_PROMISE_THRESHOLD
        is_long_silence = days.is_not_null() & (days > WITHDRAW_THRESHOLD_DAYS)

        rec_expr = pl.when(is_many_missed | is_long_silence).then(pl.lit(WITHDRAW)).otherwise(pl.lit(KEEP))

        reason_missed  = pl.when(is_many_missed).then(pl.concat_str([pl.lit("وعود منتهية: "), missed.cast(pl.String)])).otherwise(pl.lit(None))
        reason_silence = pl.when(is_long_silence).then(pl.concat_str([pl.lit("أيام بدون تواصل: "), days.cast(pl.String)])).otherwise(pl.lit(None))
        reason_expr    = pl.concat_str([reason_missed, reason_silence], separator=" | ", ignore_nulls=True)

        df = df.with_columns([
            rec_expr.alias(self.REC_COL),
            reason_expr.alias(self.REASON_COL),
        ])

        # Pivots
        piv_sup = self._build_pivot(df, "المشرف")
        collector = next((c for c in ["المحصل", "الموظف"] if c in df.columns), "")
        piv_col   = self._build_pivot(df, collector) if collector else pl.DataFrame()

        total = len(df)
        withdraw = df.filter(pl.col(self.REC_COL) == WITHDRAW).height
        stats = {
            "إجمالي العملاء":    total,
            "يُسحب":             withdraw,
            "يُبقى":             total - withdraw,
            "نسبة السحب %":      round(withdraw / total * 100, 1) if total else 0.0,
        }

        return {
            "data":             df,
            "pivot_supervisor": piv_sup,
            "pivot_collector":  piv_col,
            "stats":            stats,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _enrich_promise_stats(self, df: pl.DataFrame, promise: pl.DataFrame) -> pl.DataFrame:
        if "تاريخ وعد السداد" not in promise.columns or "رقم الحساب" not in promise.columns:
            return df.with_columns(pl.lit(0).cast(pl.Int32).alias("عدد الوعود المنتهية"))

        try:
            today     = get_today()
            today_lit = pl.lit(today)

            # مقارنة التاريخ vectorized — بدون map_elements
            pr_str  = pl.col("تاريخ وعد السداد").cast(pl.String, strict=False).str.strip_chars().str.replace(r"\s+.*$", "")
            pr_date = (
                pr_str.str.to_date("%m/%d/%Y", strict=False)
                .fill_null(pr_str.str.to_date("%Y-%m-%d", strict=False))
                .fill_null(pr_str.str.to_date("%d/%m/%Y", strict=False))
                .fill_null(pr_str.str.to_date("%Y/%m/%d", strict=False))
                .fill_null(pr_str.str.to_date("%d-%m-%Y", strict=False))
                .fill_null(pr_str.str.to_date("%m-%d-%Y", strict=False))
            )
            is_expired = pr_date.is_not_null() & (pr_date < today_lit)

            expired_counts = (
                promise.with_columns(is_expired.alias("_expired"))
                .filter(pl.col("_expired"))
                .group_by("رقم الحساب")
                .len()
                .rename({"len": "عدد الوعود المنتهية"})
            )

            result = df.join(expired_counts, on="رقم الحساب", how="left")
            if "عدد الوعود المنتهية" not in result.columns:
                result = result.with_columns(pl.lit(0).cast(pl.Int32).alias("عدد الوعود المنتهية"))
            else:
                result = result.with_columns(
                    pl.col("عدد الوعود المنتهية").fill_null(0).cast(pl.Int32)
                )
            return result
        except Exception as exc:
            _log.warning("فشل إثراء وعود السداد المنتهية: %s", exc)
            return df.with_columns(pl.lit(0).cast(pl.Int32).alias("عدد الوعود المنتهية"))

    def _build_pivot(self, df: pl.DataFrame, group_col: str) -> pl.DataFrame:
        if not group_col or group_col not in df.columns:
            return pl.DataFrame()

        try:
            pivot = (
                df.group_by([group_col, self.REC_COL])
                .len()
                .pivot(on=self.REC_COL, index=group_col, values="len")
                .fill_null(0)
            )
            for col in [WITHDRAW, KEEP]:
                if col not in pivot.columns:
                    pivot = pivot.with_columns(pl.lit(0).alias(col))
            pivot = pivot.with_columns(
                (pl.col(WITHDRAW) + pl.col(KEEP)).alias("الإجمالي")
            )
            pivot = pivot.with_columns(
                (pl.col(WITHDRAW) / pl.col("الإجمالي") * 100).round(1).alias("نسبة السحب %")
            )
            return pivot
        except Exception as e:
            _log.warning("فشل إنشاء محور السحب لـ %s: %s", group_col, e)
            return pl.DataFrame()
