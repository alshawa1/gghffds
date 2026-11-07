"""
core/data_loader.py
───────────────────
High-performance Polars-based loader and classifier for STC Operations Excel files.

Includes:
  1. Smart Cache: Stores DataFrames in memory based on file path and modification time.
  2. Smart File Loading: Automatically detects the file type (main_portfolio, promise_pay, etc.)
     by scanning the first row's column names.
  3. Validation: Structural verification of columns and schemas.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import polars as pl
from python_calamine import CalamineWorkbook

from core.utils import (
    COMPANY_PAY, FILE_LABELS, FILE_REQUIRED_COLUMNS,
    FILE_REQUIRED_COLUMNS_ALT, MAHARAH_PAY,
    MAIN_PORTFOLIO, PROMISE_PAY, logger,
)

# ─── Global Smart Cache ───────────────────────────────────────────────────────

class SmartCache:
    """In-memory cache for loaded DataFrames with modification time checks."""
    _cache: Dict[str, Dict[str, any]] = {}

    @classmethod
    def get(cls, path: str) -> Optional[pl.DataFrame]:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return None
        mtime = os.path.getmtime(abs_path)
        cached = cls._cache.get(abs_path)
        if cached and cached["mtime"] == mtime:
            logger.info("⚡ استرداد الملف من الذاكرة المؤقتة (Smart Cache): %s", os.path.basename(path))
            return cached["df"]
        return None

    @classmethod
    def put(cls, path: str, df: pl.DataFrame):
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            mtime = os.path.getmtime(abs_path)
            cls._cache[abs_path] = {"mtime": mtime, "df": df}

    @classmethod
    def clear(cls):
        cls._cache.clear()
        logger.info("🧹 تم إخلاء الذاكرة المؤقتة بالكامل")


# ─── Validation Result ────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, msg: str):
        self.is_valid = False
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def summary(self) -> str:
        lines = []
        for e in self.errors:
            lines.append(f"❌ {e}")
        for w in self.warnings:
            lines.append(f"⚠  {w}")
        return "\n".join(lines) if lines else "✅ الملف صحيح"


# ─── File Classifier ─────────────────────────────────────────────────────────

class FileClassifier:
    """Detects type of Excel file based on its headers."""

    @staticmethod
    def detect_type(path: str) -> Optional[str]:
        """
        Scan only sheet headers (without reading all data) to classify file type.
        """
        try:
            wb = CalamineWorkbook.from_path(path)
            sheets = wb.sheet_names
            if not sheets:
                return None
            
            # Read first sheet first row
            rows = wb.get_sheet_by_name(sheets[0])
            first_row = next(rows, None)
            if not first_row:
                return None
            
            headers = [str(cell).strip() for cell in first_row if cell is not None]
            
            if "EmpSadad_Id" in headers:
                return MAHARAH_PAY
            if "Service No." in headers and "Payment Amount" in headers:
                return COMPANY_PAY
            if "تاريخ وعد السداد" in headers:
                return PROMISE_PAY
            # If it has main portfolio columns
            portfolio_indicators = ["الرقم الرئيسي", "رقم المديونية", "رقم الحساب", "الحالة الرئيسية"]
            if any(col in headers for col in portfolio_indicators):
                return MAIN_PORTFOLIO
                
            return None
        except Exception as e:
            logger.warning("فشل تصنيف الملف %s: %s", os.path.basename(path), e)
            return None


# ─── Data Loader ──────────────────────────────────────────────────────────────

class DataLoader:

    def __init__(self, file_key: str):
        self.file_key = file_key

    def load(self, path: str) -> Tuple[Optional[pl.DataFrame], ValidationResult]:
        """
        Loads the Excel file using Polars with Calamine engine.
        Ensures all columns are loaded as String to prevent type mismatches.
        """
        result = ValidationResult()
        
        # Check cache first
        cached_df = SmartCache.get(path)
        if cached_df is not None:
            return cached_df, result

        if not os.path.exists(path):
            result.add_error(f"الملف غير موجود: {path}")
            return None, result

        t0 = time.time()
        try:
            from python_calamine import CalamineWorkbook
            wb = CalamineWorkbook.from_path(path)
            sheet = wb.get_sheet_by_name(wb.sheet_names[0])
            data = sheet.to_python()
            if not data:
                df = pl.DataFrame()
            else:
                headers = []
                seen = {}
                for i, h in enumerate(data[0]):
                    h_str = str(h).strip() if h is not None else f"Column_{i}"
                    if not h_str:
                        h_str = f"Column_{i}"
                    if h_str in seen:
                        seen[h_str] += 1
                        h_str = f"{h_str}_{seen[h_str]}"
                    else:
                        seen[h_str] = 0
                    headers.append(h_str)
                records = data[1:]
                # Convert all values to strings to prevent mixed-type errors
                # (e.g., some cells are numbers while others are empty strings)
                str_records = [
                    [str(cell) if cell is not None else "" for cell in row]
                    for row in records
                ]
                df = pl.DataFrame(str_records, schema=headers, orient="row")
            
            # Clean column names (strip whitespace)
            df = df.rename({c: c.strip() for c in df.columns})
            
            # Convert all columns to string representation first to avoid mixed types
            df = df.select([pl.col(c).cast(pl.String).fill_null("") for c in df.columns])

            # Pre-emptively format key columns as cleaned text and amount/payment columns as numbers
            for col in df.columns:
                c_clean = col.strip()
                if c_clean in ["رقم الحساب", "رقم المديونية", "رقم المدينية", "رقم الهوية", "الهوية", "الرقم الرئيسي", "رقم الحساب الرئيسي", "Account No.", "Account No", "Service No.", "Customer ID", "Debt No."]:
                    df = df.with_columns(
                        pl.col(col)
                        .cast(pl.Utf8, strict=False)
                        .fill_null("")
                        .str.strip_chars()
                        .str.replace(r"\.0+$", "")
                        .str.replace_all(" ", "")
                        .alias(col)
                    )
                elif c_clean in ["مبلغ السداد", "مبلغ المديونية", "مبلغ الميدونية", "السدادات الموثقة", "متبقي سداد موثق", "Payment Amount", "Current Balance Due", "مبلغ التعديل", "الشركة", "مهارة", "الفرق"]:
                    df = df.with_columns(
                        pl.col(col)
                        .cast(pl.Utf8, strict=False)
                        .str.replace_all(",", "")
                        .str.strip_chars()
                        .cast(pl.Float64, strict=False)
                        .fill_null(0.0)
                        .alias(col)
                    )

            
            # ── Flexible column validation (any-match per slot) ─────────────
            alt_slots = FILE_REQUIRED_COLUMNS_ALT.get(self.file_key, [])
            existing = set(df.columns)
            if alt_slots:
                # For each slot, at least one candidate must be present
                failed_slots = [
                    slot for slot in alt_slots
                    if not any(c in existing for c in slot)
                ]
                if failed_slots:
                    # Soft warning — don't hard-fail; modules will detect
                    # missing columns and handle gracefully
                    friendly = ", أو ".join(
                        " / ".join(s[:3]) for s in failed_slots
                    )
                    result.add_warning(
                        f"تنبيه: لم يُعثر على أعمدة رئيسية ({friendly}) — "
                        f"قد تكون بعض الميزات محدودة. تأكد من صحة الملف."
                    )

            if df.is_empty():
                result.add_warning("الملف فارغ ولا يحتوي على صفوف بيانات")

            if result.is_valid:


                # Save to Smart Cache
                SmartCache.put(path, df)
                logger.info("✅ تم تحميل الملف بنجاح: %s (%d صف) في %.2f ثانية", 
                            os.path.basename(path), len(df), time.time() - t0)
                
            return df, result
            
        except PermissionError:
            result.add_error(f"لا يمكن فتح الملف (مفتوح في Excel؟): {path}")
        except Exception as exc:
            result.add_error(f"خطأ أثناء قراءة الملف: {exc}")
            
        return None, result


# ─── Batch Loader ─────────────────────────────────────────────────────────────

def load_files(
    paths: Dict[str, str]
) -> Tuple[Dict[str, pl.DataFrame], Dict[str, ValidationResult]]:
    """Loads multiple files concurrently or sequentially."""
    dfs: Dict[str, Optional[pl.DataFrame]] = {}
    results: Dict[str, ValidationResult] = {}

    for key, path in paths.items():
        loader = DataLoader(key)
        df, vr = loader.load(path)
        dfs[key] = df
        results[key] = vr

    return dfs, results


def all_valid(results: Dict[str, ValidationResult]) -> bool:
    return all(v.is_valid for v in results.values())
