import re

def clean_float(val) -> float:
    """removes commas, non-numeric chars, returns 0.0 if invalid"""
    if val is None or val == '':
        return 0.0
    try:
        if isinstance(val, (int, float)):
            return float(val)
        val_str = str(val)
        # Remove anything that's not a digit, dot or minus sign
        val_str = re.sub(r'[^\d.-]', '', val_str)
        if not val_str:
            return 0.0
        return float(val_str)
    except Exception:
        return 0.0

def clean_int(val) -> int:
    """similar for integers"""
    try:
        return int(clean_float(val))
    except Exception:
        return 0

def format_currency(val: float) -> str:
    """formats as '1,234.56 ريال'"""
    try:
        return f"{val:,.2f} ريال"
    except Exception:
        return "0.00 ريال"

def format_percentage(val: float) -> str:
    """formats as '12.34%'"""
    try:
        return f"{val:.2f}%"
    except Exception:
        return "0.00%"
