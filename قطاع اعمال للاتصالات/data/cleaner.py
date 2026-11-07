import pandas as pd
from utils import date_utils, number_utils

def _normalize_date_series(series: pd.Series) -> pd.Series:
    """تحويل سريع لكولوم التواريخ — vectorized بدل apply."""
    # محاولة أولى: pandas مباشر
    result = pd.to_datetime(series, errors='coerce', dayfirst=False)
    # محاولة ثانية للفاشلين: dayfirst=True
    mask_failed = result.isna() & series.notna() & (series.astype(str).str.strip() != '')
    if mask_failed.any():
        result2 = pd.to_datetime(series[mask_failed], errors='coerce', dayfirst=True)
        result = result.where(~mask_failed, result2)
    return result.dt.strftime('%Y-%m-%d').fillna('')


def clean_portfolio(raw_df: pd.DataFrame, column_map: dict) -> pd.DataFrame:
    df = raw_df.copy()

    # ── 1. تنظيف كولومات النص: vectorized بدل apply ──
    str_cols = df.select_dtypes(['object']).columns.tolist()
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip().replace({'nan': '', 'None': '', 'NaT': ''})

    # ── 2. تحويل الأرقام: vectorized ──
    def _to_numeric_col(col_name):
        if col_name not in df.columns:
            return
        df[col_name] = pd.to_numeric(
            df[col_name].astype(str).str.replace(',', '', regex=False).str.extract(r'(-?\d+\.?\d*)')[0],
            errors='coerce'
        ).fillna(0.0)

    debt_col = column_map.get('مبلغ الميدونية') or column_map.get('debt_amount') or \
               next((c for c in df.columns if 'مديون' in c or 'ميدون' in c), None)
    paid_col = column_map.get('السدادات الموثقة') or column_map.get('paid_doc') or \
               next((c for c in df.columns if 'سداد' in c and 'موث' in c), None)
    rem_col  = column_map.get('متبقي سداد موثق') or column_map.get('remaining_doc') or \
               next((c for c in df.columns if 'متبقي' in c), None)

    for c in [debt_col, paid_col, rem_col]:
        if c:
            _to_numeric_col(c)

    # ── 3. إضافة الكولومات المشتقة: كلها vectorized ──
    def _get(key):
        col = column_map.get(key)
        return df[col] if col and col in df.columns else pd.Series([''] * len(df), index=df.index)

    df['_customer_id']   = _get('رقم الهوية').astype(str).str.strip()
    df['_debt_amount']   = pd.to_numeric(df[debt_col], errors='coerce').fillna(0.0) if debt_col and debt_col in df.columns else 0.0
    df['_paid_doc']      = pd.to_numeric(df[paid_col], errors='coerce').fillna(0.0) if paid_col and paid_col in df.columns else 0.0
    df['_remaining_doc'] = pd.to_numeric(df[rem_col],  errors='coerce').fillna(0.0) if rem_col  and rem_col  in df.columns else 0.0
    df['_portfolio']     = _get('المحافظ').astype(str).str.strip()
    df['_collector']     = _get('المحصل').astype(str).str.strip()
    df['_supervisor']    = _get('المشرف').astype(str).str.strip()
    df['_main_status']   = _get('الحالة الرئيسية').astype(str).str.strip()
    df['_sub_status']    = _get('الحالة الفرعية').astype(str).str.strip()

    # ── 4. تواريخ: vectorized بدل apply ──
    followup_col = column_map.get('تاريخ المتابعة')
    if followup_col and followup_col in df.columns:
        df['_followup_date'] = _normalize_date_series(df[followup_col])
    else:
        df['_followup_date'] = ''

    return df


def clean_payment_file(raw_df: pd.DataFrame, column_map: dict) -> pd.DataFrame:
    df = raw_df.copy()

    # 1. تنظيف النصوص
    str_cols = df.select_dtypes(['object']).columns.tolist()
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip().replace({'nan': '', 'None': '', 'NaT': ''})

    def get_col(key):
        col_name = column_map.get(key)
        return df[col_name] if col_name and col_name in df.columns else pd.Series([''] * len(df), index=df.index)

    df['_customer_id'] = get_col('رقم الهوية').astype(str).str.strip()

    # مبلغ السداد
    pay_col = column_map.get('مبلغ السداد') or next((c for c in df.columns if 'سداد' in c or 'مبلغ' in c), None)
    if pay_col and pay_col in df.columns:
        df[pay_col] = pd.to_numeric(
            df[pay_col].astype(str).str.replace(',', '', regex=False).str.extract(r'(-?\d+\.?\d*)')[0],
            errors='coerce'
        ).fillna(0.0)
        df['_payment_amount'] = df[pay_col]
    else:
        df['_payment_amount'] = 0.0

    # تاريخ السداد
    date_col = column_map.get('تاريخ السداد') or next((c for c in df.columns if 'تاريخ' in c), None)
    if date_col and date_col in df.columns:
        df['_payment_date'] = _normalize_date_series(df[date_col])
    else:
        df['_payment_date'] = ''

    return df

