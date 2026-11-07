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
    تصنيف حالة التواصل بناءاً على:
    1. 'عدم توصل - أخرى': إذا كانت الحالة الرئيسية = 'عدم توصل' (أولوية قصوى)
    2. 'لا يرد ومغلق'  : إذا كانت الحالة الفرعية تحتوي على (لا يرد / لا برد / مغلق)
                         والحالة الرئيسية ليست 'عدم توصل'
    3. 'تم التوصل'     : كل ما عدا ذلك (متابعة، واعد بالسداد، سداد جزئي، تم السداد...)
    """
    n = len(df)
    main_s = df[main_col].astype(str).str.strip() if main_col and main_col in df.columns else pd.Series(['']*n, index=df.index)
    sub_s  = df[sub_col].astype(str).str.strip()  if sub_col  and sub_col  in df.columns else pd.Series(['']*n, index=df.index)

    # ── الأولوية 1: الحالة الرئيسية = "عدم توصل" ──
    # (بغض النظر عن الحالة الفرعية)
    mask_no_contact = main_s.str.contains('عدم توصل', regex=False, na=False)

    # ── الأولوية 2: الحالة الفرعية = لا يرد / لا برد / مغلق ──
    # (فقط إذا لم تكن الحالة الرئيسية "عدم توصل")
    no_ans_terms = ['لايرد', 'لا يرد', 'لا برد', 'لابرد', 'مغلق', 'مغلق مؤقتا', 'لا برد']
    p_no_ans = '|'.join(no_ans_terms)
    mask_no_ans = sub_s.str.contains(p_no_ans, regex=True, na=False) & ~mask_no_contact

    # ── الباقي: تم التوصل ──
    status_vec = np.full(n, 'تم التوصل', dtype=object)
    status_vec[mask_no_ans]    = 'لا يرد ومغلق'       # أولوية 2
    status_vec[mask_no_contact] = 'عدم توصل - أخرى'  # أولوية 1 (تطغى على أولوية 2)

    return status_vec


