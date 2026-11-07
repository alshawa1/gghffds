import pandas as pd
from datetime import datetime, date
from typing import Optional, Union
import warnings

def normalize_date(val: Union[str, datetime, date, pd.Timestamp, int, float, None]) -> str:
    """converts any date format to YYYY-MM-DD."""
    if pd.isna(val) or val is None or str(val).strip() == '' or str(val).strip().lower() in ('none', 'null', 'nan', '-'):
        return ''
    
    try:
        if isinstance(val, (datetime, date, pd.Timestamp)):
            return val.strftime('%Y-%m-%d')
        
        val_str = str(val).strip()
        
        # Excel serial date
        if val_str.replace('.', '', 1).isdigit():
            val_float = float(val)
            if val_float > 30000: # reasonable serial date
                return pd.to_datetime(val_float, unit='D', origin='1899-12-30').strftime('%Y-%m-%d')
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # Try parsing directly without hardcoding dayfirst
            parsed = pd.to_datetime(val_str, errors='coerce', dayfirst=False)
            if pd.isna(parsed):
                parsed = pd.to_datetime(val_str, dayfirst=True, errors='coerce')
        
        if not pd.isna(parsed):
            return parsed.strftime('%Y-%m-%d')
            
        return ''
    except Exception:
        return ''

def parse_date_safe(val: Union[str, datetime, date, pd.Timestamp, int, float, None]) -> Optional[date]:
    """returns date object or None"""
    normalized = normalize_date(val)
    if normalized:
        return datetime.strptime(normalized, '%Y-%m-%d').date()
    return None

def days_since(date_str: str) -> int:
    """days from date_str to today, returns 9999 if invalid"""
    parsed = parse_date_safe(date_str)
    if parsed:
        return (date.today() - parsed).days
    return 9999

def extract_unique_dates(df: pd.DataFrame, date_column: str) -> list[str]:
    """
    Extract clean, unique YYYY-MM-DD date strings sorted in descending order.
    Eliminates strange timestamps and trailing digits.
    """
    if date_column not in df.columns:
        return []
    
    ser = df[date_column].dropna()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        dates_dt = pd.to_datetime(ser, errors='coerce', dayfirst=False)
        if dates_dt.isna().mean() > 0.5:
            dates_dt = pd.to_datetime(ser, errors='coerce', dayfirst=True)
    dates_clean = dates_dt.dropna().dt.strftime('%Y-%m-%d').unique().tolist()
    return sorted([d for d in dates_clean if d and len(d) == 10], reverse=True)

