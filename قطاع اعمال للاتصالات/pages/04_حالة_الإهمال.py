import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="حالة الإهمال", page_icon="⏳", layout="wide")
st.markdown("<style>body { direction: rtl; text-align: right; } .stApp { direction: rtl; }</style>", unsafe_allow_html=True)

st.title("⏳ فحص وتحديد حالات الإهمال")

from utils.page_upload import page_portfolio_uploader, render_supervisor_filter

df_full, column_map, raw_df = page_portfolio_uploader("page_04_neglect", label="📂 ارفع ملف المحفظة لفحص حالات الإهمال (Excel)")

if df_full is None or df_full.empty:
    st.stop()

df = render_supervisor_filter(df_full, column_map, "page_04_neglect")

try:
    from business_rules.neglect_rules import NeglectEngine
    from reports.export import export_neglect, export_portfolio_with_summaries
except ImportError:
    NeglectEngine = None

st.info("💡 اضغط على الزر أدناه لبدء فحص واحتساب حالات الإهمال وفترات السماح:")
# ─────────────────────────────────────────────────────────────
# 1. فحص الإهمال التلقائي مع خيار إعادة الفحص
# ─────────────────────────────────────────────────────────────
if 'neglect_result' not in st.session_state or st.button("🔄 إعادة فحص الإهمال الآن", type="primary", use_container_width=True):
    with st.spinner("جاري احتساب أيام الإهمال..."):
        if NeglectEngine:
            engine = NeglectEngine()
            result = engine.calculate(df, column_map)
            st.session_state['neglect_result'] = result
            st.session_state['total_neglected'] = result['stats'].get('total_neglected', 0)
        else:
            result = None

result = st.session_state.get('neglect_result')
if result:
    df_neg = result['data']
    stats = result['stats']

    tot_neg = stats.get('total_neglected', 0)
    tot_exc = stats.get('total_excluded', 0)
    tot_ok = stats.get('total_ok', 0)
    avg_days = stats.get('avg_days_neglected', 0)

    st.markdown("---")
    st.markdown("### 📊 ملخص نتائج تحليل الإهمال")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("عدد الحالات المهملة ⚠️", f"{tot_neg:,}")
    m2.metric("الحالات المستثناة 🟢", f"{tot_exc:,}")
    m3.metric("الحالات المتابعة بشكل منتظم 🔵", f"{tot_ok:,}")
    m4.metric("متوسط أيام الإهمال ⏳", f"{avg_days:.1f} يوم")

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────
    # 2. أزرار التنزيل العلوية الإبرازية
    # ─────────────────────────────────────────────────────────────
    st.markdown("### 📥 تنزيل شيت البيانات المعدل والتقارير (علوي):")

    neglected_table = df_neg[df_neg['حالة الإهمال'] == 'مهمل'].copy() if 'حالة الإهمال' in df_neg.columns else df_neg

    c_dl1, c_dl2 = st.columns(2)

    with c_dl1:
        st.download_button(
            label="📥 تحميل التقرير النهائي الشامل (Excel Styled)",
            data=export_portfolio_with_summaries(
                clean_df=df,
                col_map=column_map,
                errors_df=st.session_state.get('errors_result', {}).get('data'),
                neglect_df=df_neg,
                payment_df=st.session_state.get('payment_df')
            ),
            file_name="المحفظة_الأساسية_المعدلة_الإهمال.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
            key="dl_neg_full_styled_top"
        )

    with c_dl2:
        st.download_button(
            label="📋 تنزيل تقرير حالات الإهمال فقط (Excel)",
            data=export_neglect(neglected_table),
            file_name="تقرير_حالات_الإهمال.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="dl_neg_raw_fast_top"
        )

    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        if 'حالة الإهمال' in df_neg.columns:
            neg_counts = df_neg['حالة الإهمال'].value_counts().reset_index()
            neg_counts.columns = ['حالة الإهمال', 'العدد']
            fig = px.pie(neg_counts, values='العدد', names='حالة الإهمال', title='توزيع حالات الإهمال', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        if 'حالة الإهمال' in df_neg.columns and '_collector' in df_neg.columns:
            neg_df_only = df_neg[df_neg['حالة الإهمال'] == 'مهمل']
            if not neg_df_only.empty:
                top_coll_neg = neg_df_only.groupby('_collector').size().reset_index(name='عدد الحالات المهملة').sort_values('عدد الحالات المهملة', ascending=False).head(10)
                fig_b = px.bar(top_coll_neg, x='_collector', y='عدد الحالات المهملة', title='أكثر 10 محصلين في الإهمال')
                st.plotly_chart(fig_b, use_container_width=True)

    st.markdown("---")
    st.markdown("#### 📋 تفاصيل الحالات المهملة:")
    if not neglected_table.empty:
        st.dataframe(neglected_table, use_container_width=True)
    else:
        st.success("🎉 لا توجد أي حالات إهمال حالياً!")

    # ─────────────────────────────────────────────────────────────
    # 3. أزرار التنزيل السفلية
    # ─────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📥 تنزيل شيت البيانات المعدل والتقارير (سفلي):")
    b_dl1, b_dl2 = st.columns(2)
    with b_dl1:
        st.download_button(
            label="📥 تحميل التقرير النهائي الشامل (Excel Styled)",
            data=export_portfolio_with_summaries(
                clean_df=df,
                col_map=column_map,
                errors_df=st.session_state.get('errors_result', {}).get('data'),
                neglect_df=df_neg,
                payment_df=st.session_state.get('payment_df')
            ),
            file_name="المحفظة_الأساسية_المعدلة_الإهمال.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
            key="dl_neg_full_styled_bottom"
        )
    with b_dl2:
        st.download_button(
            label="📋 تنزيل تقرير حالات الإهمال فقط (Excel)",
            data=export_neglect(neglected_table),
            file_name="تقرير_حالات_الإهمال.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="dl_neg_raw_fast_bottom"
        )
