"""
core/matcher.py
───────────────
Optimized Polars-based matcher for STC Operations matching priorities.

Matching priority (per company policy):
  1. رقم الحساب   (Account Number)
  2. رقم المديونية (Debt Number)
  3. رقم الهوية / الهوية (National ID)
"""
from __future__ import annotations

import logging
from typing import List, Optional

import polars as pl

_log = logging.getLogger("Matcher")

PRIORITY_KEYS = [
    ("رقم الحساب",    "رقم الحساب"),
    ("رقم المديونية", "رقم المديونية"),
    ("الهوية",        "رقم الهوية"),
    ("الهوية",        "الهوية"),
    ("رقم الهوية",    "رقم الهوية"),
]


class Matcher:

    @staticmethod
    def enrich(
        left: pl.DataFrame,
        right: pl.DataFrame,
        cols_to_bring: List[str],
    ) -> pl.DataFrame:
        """
        Left-joins `right` onto `left` bringing `cols_to_bring`
        following the company's matching key priorities.
        """
        # Find the first key pair that exists in both DataFrames
        match_pair = None
        for left_key, right_key in PRIORITY_KEYS:
            if left_key in left.columns and right_key in right.columns:
                match_pair = (left_key, right_key)
                break

        if match_pair is None:
            _log.warning("لا يوجد عمود مشترك للربط — تم إرجاع المحفظة بدون إثراء")
            # Create columns with empty values
            lazy_df = left.lazy()
            for col in cols_to_bring:
                if col not in left.columns:
                    lazy_df = lazy_df.with_columns(pl.lit("").alias(col))
            return lazy_df.collect()

        left_key, right_key = match_pair
        _log.info("ربط البيانات بالاعتماد على: %s ↔ %s", left_key, right_key)

        # Build slim right DataFrame containing key and target columns, dropping duplicates
        cols_to_select = [right_key] + [c for c in cols_to_bring if c in right.columns and c != right_key]
        right_slim = (
            right.select(cols_to_select)
            .unique(subset=[right_key], keep="last")
        )

        # Join the DataFrames
        result = left.join(
            right_slim,
            left_on=left_key,
            right_on=right_key,
            how="left",
        )
        
        return result

    @staticmethod
    def sumif(
        source: pl.DataFrame,
        key_col: str,
        value_col: str,
        target_keys: pl.Series,
    ) -> pl.Series:
        """
        Equivalent to Excel's SUMIF.
        Computes the sum of value_col in source grouped by key_col,
        mapped onto target_keys.
        """
        if key_col not in source.columns or value_col not in source.columns:
            return pl.Series([0.0] * len(target_keys))

        # Check if the column is string/utf8 type
        is_string = source.schema[value_col] in (pl.Utf8, pl.String)

        # Perform aggregation in Polars
        val_expr = pl.col(value_col)
        if is_string:
            val_expr = (
                val_expr
                .str.replace_all(",", "")
                .str.strip_chars()
                .cast(pl.Float64, strict=False)
            )
        else:
            val_expr = val_expr.cast(pl.Float64, strict=False)

        agg = (
            source.lazy()
            .select([
                pl.col(key_col),
                val_expr.fill_null(0.0).alias("_val")
            ])
            .group_by(key_col)
            .agg(pl.col("_val").sum().alias("_sum"))
            .collect()
        )

        # Build map
        agg_map = {row[0]: row[1] for row in agg.iter_rows()}
        
        # Map values back to target_keys
        sums = [agg_map.get(key, 0.0) for key in target_keys.to_list()]
        return pl.Series(sums)

