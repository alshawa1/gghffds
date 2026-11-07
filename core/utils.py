"""
core/utils.py
─────────────
Shared helpers: date parsing, Arabic text utilities, constants, logging setup.
"""
import logging
import os
from datetime import date, datetime
from typing import Dict, List, Optional

import math
from dateutil import parser as dateutil_parser

# ─── Logging ────────────────────────────────────────────────────────────────

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "system.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("STC_OPS")


# ─── Date helpers ────────────────────────────────────────────────────────────

def get_today() -> date:
    """Return today's date."""
    return date.today()


def _is_nan(value) -> bool:
    """Check if value is null, None, NaN, NaT or blank string."""
    if value is None:
        return True
    if isinstance(value, float):
        return math.isnan(value)
    if isinstance(value, str):
        v = value.strip().lower()
        return v in ["", "nan", "nat", "null", "none"]
    return False


def parse_date(value) -> Optional[date]:
    """
    Safely parse any date-like value (datetime, str, None …)
    Returns a date object or None.
    """
    if _is_nan(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return dateutil_parser.parse(value, dayfirst=True).date()
        except Exception:
            return None
    return None


def days_since(value) -> Optional[int]:
    """Return number of days from *value* to today. None if unparsable."""
    d = parse_date(value)
    if d is None:
        return None
    return (get_today() - d).days


def is_future_or_today(value) -> bool:
    """Return True if *value* is today or a future date."""
    d = parse_date(value)
    if d is None:
        return False
    return d >= get_today()


# ─── Arabic text helpers ─────────────────────────────────────────────────────

def clean_text(value) -> str:
    """Return stripped string or empty string."""
    if _is_nan(value):
        return ""
    return str(value).strip()


def is_empty(value) -> bool:
    """True if value is None / NaN / blank string."""
    return _is_nan(value)


def is_unclear(value) -> bool:
    """
    True if *value* is empty OR is a trivial / unclear note.
    Extend the GENERIC_NOTES list to tune detection.
    """
    if is_empty(value):
        return True
    text = clean_text(value).lower()
    GENERIC_NOTES = [
        "لا يوجد", "بدون", "-", ".", "..", "...", "لايوجد",
        "تم التواصل", "تواصل", "ok", "okay", "n/a", "na",
    ]
    return text in GENERIC_NOTES


# ─── Task / file configuration ───────────────────────────────────────────────

# Human-readable task names (Arabic + English)
TASK_NAMES = {
    1: "اخطاء النظام — System Errors",
    2: "التوصل وعدم التوصل — Contact Status",
    3: "الاهمال — Neglect Analysis",
    4: "السدادات والتسوية — Payments & Reconciliation",
    5: "الجدولة — Scheduling",
    6: "السحب والتدوير — Withdrawal & Rotation",
    7: "العملاء المستهدفة — Target Customers",
    8: "تشغيل جميع المهام — Full Operations Report",
}

# Logical file keys
MAIN_PORTFOLIO  = "main_portfolio"
PROMISE_PAY     = "promise_pay"
MAHARAH_PAY     = "maharah_pay"
COMPANY_PAY     = "company_pay"

# Files required per task
TASK_FILE_REQUIREMENTS = {
    1: [MAIN_PORTFOLIO, PROMISE_PAY],
    2: [MAIN_PORTFOLIO],
    3: [MAIN_PORTFOLIO],
    4: [MAIN_PORTFOLIO, MAHARAH_PAY, COMPANY_PAY],
    5: [MAIN_PORTFOLIO, MAHARAH_PAY],
    6: [MAIN_PORTFOLIO],
    7: [MAIN_PORTFOLIO, PROMISE_PAY, MAHARAH_PAY],
    8: [MAIN_PORTFOLIO, PROMISE_PAY, MAHARAH_PAY, COMPANY_PAY],
}

FILE_LABELS = {
    MAIN_PORTFOLIO: "المحفظة الموزعة (Main Portfolio)",
    PROMISE_PAY:    "وعود السداد (Promise To Pay)",
    MAHARAH_PAY:    "سداد مهارة (Maharah Payments)",
    COMPANY_PAY:    "سداد الشركة (Parent Company Payments)",
}

# ─── Required columns per file (minimum validation set) ──────────────────────
# NOTE: Validation uses ANY-match logic — the file passes if at least ONE
# column from any alternative group is found. This allows portfolios with
# different column names (e.g. رقم المدينية vs رقم المديونية) to load fine.

# Alternative column sets — each inner list = one "slot"; file is valid if
# at least ONE column from the slot exists.
FILE_REQUIRED_COLUMNS_ALT: Dict[str, List[List[str]]] = {
    MAIN_PORTFOLIO: [
        # At least one ID-like column
        ["رقم الحساب", "رقم المديونية", "رقم المدينية", "رقم الهوية", "الهوية",
         "الرقم الرئيسي", "Account No.", "Account No", "Customer ID", "Debt No."],
    ],
    PROMISE_PAY: [
        ["رقم الحساب", "رقم المديونية", "رقم المدينية", "رقم الهوية",
         "الرقم الرئيسي", "Account No."],
    ],
    MAHARAH_PAY: [
        ["رقم الحساب", "رقم المديونية", "EmpSadad_Id", "Account No.",
         "رقم الهوية", "الهوية"],
    ],
    COMPANY_PAY: [
        ["Account No.", "Account No", "Service No.", "رقم الحساب"],
    ],
}

# Keep old dict for compatibility (not used for validation any more)
FILE_REQUIRED_COLUMNS: Dict[str, List[str]] = {
    MAIN_PORTFOLIO: ["رقم الحساب", "رقم المديونية", "الحالة الرئيسية", "المشرف"],
    PROMISE_PAY:    ["رقم الحساب", "رقم المديونية", "تاريخ وعد السداد"],
    MAHARAH_PAY:    ["رقم الحساب", "رقم المديونية", "مبلغ السداد"],
    COMPANY_PAY:    ["Account No.", "Payment Amount", "Current Balance Due"],
}

# ─── Business constants ───────────────────────────────────────────────────────

NEGLECT_THRESHOLD_DAYS = 7  # days without follow-up → مهمل

# Statuses that indicate a fully-paid customer
PAID_STATUSES = {
    "مسدد", "مسدد كليا", "مسدد كلياً", "تم السداد",
    "سداد كامل", "سداد تام", "مسدد بالكامل",
    "paid", "full payment",
}

# Statuses that indicate successful contact
CONTACTED_STATUSES = {
    "وعد السداد", "وعد سداد", "مسدد", "مسدد جزئي",
    "سداد جزئي", "تم التواصل", "قسط", "اتفاق سداد",
    "تسوية", "جدولة", "إعادة جدولة", "تحويل",
    "تم الرد", "رجع الاتصال", "رد علينا",
}

# Statuses that indicate no contact
NOT_CONTACTED_STATUSES = {
    "لا يرد", "لايرد", "مغلق", "خارج التغطية",
    "لا يوجد رد", "لا يتكلم عربي", "رسالة صوتية",
    "خط معطل", "لا يتم الاتصال", "ارجاء",
    "مرفوض", "لم يرد", "لم نتمكن من التواصل",
}
