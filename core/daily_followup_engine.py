import pandas as pd
import numpy as np
import io
from datetime import date, timedelta
import streamlit as st

def detect_col(df, candidates):
    if df is None or df.empty:
        return None
    cols_lower = {c.strip().lower(): c for c in df.columns}
    for c in candidates:
        if c.strip().lower() in cols_lower:
            return cols_lower[c.strip().lower()]
    for c in candidates:
        for col in df.columns:
            if c.strip() in str(col):
                return col
    return None

def classify_contact_status_series(df, main_col=None, sub_col=None, note_col=None):
    """
    Classifies contact status strictly based on Main Status and Sub Status:
    1. 'لا يرد ومغلق': If Sub Status contains (لايرد, لا يرد, لا برد, لابرد, مغلق, مغلق مؤقتا).
    2. 'عدم توصل - أخرى': If Main Status is 'عدم توصل' or Sub Status has disconnected / invalid indicators.
    3. 'تم التوصل': All other statuses (متابعة, واعد بالسداد, سداد جزئي, تم السداد, رافض السداد, متجاوب...).
    """
    n = len(df)
    main_s = df[main_col].astype(str).str.strip() if main_col and main_col in df.columns else pd.Series(['']*n)
    sub_s  = df[sub_col].astype(str).str.strip()  if sub_col and sub_col in df.columns  else pd.Series(['']*n)

    # 1. No Answer & Closed (لا يرد ومغلق) - purely from Sub Status
    no_ans_terms = ['لايرد', 'لا يرد', 'لا برد', 'لابرد', 'مغلق', 'مغلق مؤقتا']
    p_no_ans = '|'.join(no_ans_terms)
    mask_no_ans = sub_s.str.contains(p_no_ans, regex=True, na=False)

    # 2. Non-contact (عدم توصل - أخرى) - Main Status is عدم توصل or Sub Status has disconnected / wrong number
    other_terms = ['الرقم لا يخص', 'لا يوجد ارقام', 'مقطوع', 'الرقم غير مستعمل', 'خارج الخدمة']
    p_other = '|'.join(other_terms)
    mask_other = (main_s.str.contains('عدم توصل', regex=True, na=False)) | (sub_s.str.contains(p_other, regex=True, na=False))

    # Base: تم التوصل
    status_vec = np.full(n, 'تم التوصل', dtype=object)
    # عدم توصل - أخرى applies first if condition met and not no_ans
    status_vec[mask_other] = 'عدم توصل - أخرى'
    # لا يرد ومغلق has priority if sub_status specifies no answer / closed
    status_vec[mask_no_ans] = 'لا يرد ومغلق'

    return status_vec

