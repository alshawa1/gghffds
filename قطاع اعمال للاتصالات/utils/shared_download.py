"""
shared_download.py
Standard Maharah System Download Bar:
Generates & downloads the updated main portfolio excel sheet
containing all original columns + newly added analysis columns
+ summary sheets inside the workbook.
"""
import streamlit as st
from reports.export import export_portfolio_with_summaries


def render_maharah_download_button(
    label: str = "📥 تحميل التقرير النهائي (Excel Styled)",
    key_prefix: str = "main",
    df = None,
    col_map = None,
    errors_df = None,
    neglect_df = None,
    payment_df = None,
    page_key: str = None
):
    """
    Renders the official Maharah purple-styled download button
    for the updated main portfolio Excel workbook containing Sheet 1 (original + new columns)
    and summary sheets.
    """
    if df is None and page_key:
        df = st.session_state.get(f"{page_key}_clean_df")
        if col_map is None:
            col_map = st.session_state.get(f"{page_key}_col_map", {})
        if payment_df is None:
            payment_df = st.session_state.get(f"{page_key}_payment_df")

    if df is None or df.empty:
        df = st.session_state.get('clean_data')

    if df is None or df.empty:
        return

    if col_map is None:
        col_map = st.session_state.get('column_map', {})
    if errors_df is None:
        errors_df = st.session_state.get('errors_result', {}).get('data')
    if neglect_df is None:
        neglect_df = st.session_state.get('neglect_result', {}).get('data')
    if payment_df is None:
        payment_df = st.session_state.get('payment_df')

    excel_bytes = export_portfolio_with_summaries(
        clean_df=df,
        col_map=col_map,
        errors_df=errors_df,
        neglect_df=neglect_df,
        payment_df=payment_df
    )

    st.markdown("<div style='height: 3px; background: linear-gradient(90deg, transparent, #1F6F2B, #2E7D32, transparent); border-radius: 3px; margin: 16px 0;'></div>", unsafe_allow_html=True)
    st.download_button(
        label=label,
        data=excel_bytes,
        file_name="المحفظة_الأساسية_المعدلة_بالتقارير.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        key=f"dl_maharah_{key_prefix}",
        use_container_width=True
    )

# Alias for backwards compatibility across all pages
show_download_bar = render_maharah_download_button

