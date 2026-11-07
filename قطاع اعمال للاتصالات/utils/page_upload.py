"""
utils/page_upload.py
====================
Reusable per-page portfolio uploader.
Each page calls: df, col_map, raw_df = page_portfolio_uploader(page_key)
- Data is cached in st.session_state under the page_key so re-runs are instant.
- The ORIGINAL raw_df is kept untouched; only clean_df is returned for analysis.
- Payment file uploader is provided separately for pages that need it.
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.loader import load_portfolio_file, load_payment_file
from data.cleaner import clean_portfolio, clean_payment_file


def page_portfolio_uploader(page_key: str, label: str = "📂 ارفع ملف المحفظة (Excel)"):
    """
    Renders a self-contained portfolio file uploader for a page.

    Returns:
        (clean_df, column_map, raw_df) if file loaded successfully.
        (None, {}, None) if no file yet.
    """
    sk_data  = f"{page_key}_clean_df"
    sk_raw   = f"{page_key}_raw_df"
    sk_map   = f"{page_key}_col_map"

    # Already loaded → return cached instantly
    if sk_data in st.session_state and st.session_state[sk_data] is not None:
        c1, c2 = st.columns([4, 1])
        with c1:
            st.success(f"📁 تم تحميل المحفظة لصفحة ({page_key}) بحالة جيدة ({len(st.session_state[sk_data]):,} سجل)")
        with c2:
            if st.button("🔄 تغيير الملف", key=f"reupload_{page_key}"):
                reset_page_data(page_key)
                st.rerun()
        return (
            st.session_state[sk_data],
            st.session_state.get(sk_map, {}),
            st.session_state.get(sk_raw)
        )

    st.markdown("---")
    st.subheader("📂 رفع ملف المحفظة لهذا البرنامج")
    uploaded = st.file_uploader(label, type=["xlsx", "xls"], key=f"uploader_{page_key}")

    if uploaded is None:
        st.info("👆 يرجى رفع ملف المحفظة أولاً لبدء العمل في هذا البرنامج.")
        return None, {}, None

    with st.spinner("جاري قراءة وتنظيف ملف المحفظة..."):
        res = load_portfolio_file(uploaded)
        if res.get("error"):
            st.error(f"❌ خطأ في الملف: {res['error']}")
            return None, {}, None

        raw_df  = res["raw_df"]
        col_map = res["column_map"]
        clean_df = clean_portfolio(raw_df, col_map)

        st.session_state[sk_data] = clean_df
        st.session_state[sk_raw]  = raw_df
        st.session_state[sk_map]  = col_map

        st.success(f"✅ تم تحميل {len(clean_df):,} سجل بنجاح!")
        st.markdown("---")
        st.rerun()

    return clean_df, col_map, raw_df


def page_payment_uploader(page_key: str, label: str = "📂 ارفع ملف السدادات (اختياري)"):
    """
    Renders a self-contained payment file uploader for pages that need it.

    Returns:
        (payment_df, payment_map) if loaded, else (None, {})
    """
    sk_pay     = f"{page_key}_payment_df"
    sk_pay_map = f"{page_key}_payment_map"

    if sk_pay in st.session_state and st.session_state[sk_pay] is not None:
        return st.session_state[sk_pay], st.session_state.get(sk_pay_map, {})

    uploaded = st.file_uploader(label, type=["xlsx", "xls"], key=f"pay_uploader_{page_key}")

    if uploaded is None:
        return None, {}

    with st.spinner("جاري قراءة ملف السدادات..."):
        res = load_payment_file(uploaded)
        if res.get("error"):
            st.error(f"❌ خطأ في ملف السدادات: {res['error']}")
            return None, {}

        raw_pay = res["raw_df"]
        pay_map = res["column_map"]
        clean_pay = clean_payment_file(raw_pay, pay_map)

        st.session_state[sk_pay]     = clean_pay
        st.session_state[sk_pay_map] = pay_map

        st.success(f"✅ تم تحميل {len(clean_pay):,} عملية سداد!")

    return clean_pay, pay_map


def reset_page_data(page_key: str):
    """Clear all cached data for a specific page."""
    for k in [f"{page_key}_clean_df", f"{page_key}_raw_df", f"{page_key}_col_map",
              f"{page_key}_payment_df", f"{page_key}_payment_map"]:
        st.session_state.pop(k, None)


def render_supervisor_filter(df, col_map: dict, page_key: str, label: str = "👥 تصفية حسب المشرفين (اختياري - جميع المشرفين لو ترك فارغاً):"):
    """
    Renders a multiselect box for filtering by Supervisor across any page.
    Returns filtered_df.
    """
    import pandas as pd
    if df is None or df.empty:
        return df

    sup_col = col_map.get('supervisor', 'المشرف')
    if sup_col not in df.columns:
        sup_col = '_supervisor'
    if sup_col not in df.columns:
        return df

    all_sups = sorted([s for s in df[sup_col].unique() if pd.notna(s) and str(s).strip() not in ('', 'nan')])
    if not all_sups:
        return df

    selected_sups = st.multiselect(
        label,
        all_sups,
        default=None,
        key=f"sup_filter_{page_key}"
    )

    if selected_sups:
        filtered_df = df[df[sup_col].isin(selected_sups)].copy()
        st.caption(f"👥 تم تحديد العمل على **{len(selected_sups)}** مشرف ({len(filtered_df):,} سجل من إجمالي {len(df):,})")
        return filtered_df

    return df

