import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="توازن المحافظ", page_icon="⚖️", layout="wide")
st.markdown("<style>body { direction: rtl; text-align: right; } .stApp { direction: rtl; }</style>", unsafe_allow_html=True)

st.title("⚖️ توازن أحمال المحصلين المتقدم (Multi-Portfolio Load Balancer)")

from utils.page_upload import page_portfolio_uploader, render_supervisor_filter

df_full, column_map, raw_df = page_portfolio_uploader("page_06_balance", label="📂 ارفع ملف المحفظة لتوازن المحافظ (Excel)")

if df_full is None or df_full.empty:
    st.stop()

df = render_supervisor_filter(df_full, column_map, "page_06_balance")

from utils.shared_download import render_maharah_download_button
render_maharah_download_button("📥 تحميل التقرير النهائي الشامل (Excel Styled)", key_prefix="balance_page_top", page_key="page_06_balance")
st.markdown("---")

from redistribution.balance import BalanceEngine
from reports.export import export_distribution

cust_col = column_map.get('customer_id', 'رقم الهوية')
if cust_col not in df.columns: cust_col = '_customer_id'
debt_col = column_map.get('debt_amount', 'مبلغ الميدونية')
if debt_col not in df.columns: debt_col = 'مبلغ المديونية' if 'مبلغ المديونية' in df.columns else 'مبلغ الميدونية'
rem_col = column_map.get('remaining_doc', 'متبقي سداد موثق')
if rem_col not in df.columns: rem_col = '_remaining_doc'
port_col = column_map.get('portfolio', 'المحافظ')
if port_col not in df.columns: port_col = '_portfolio'
coll_col = column_map.get('collector', 'المحصل')
if coll_col not in df.columns: coll_col = '_collector'

# Ensure numeric columns are cast to float
for c in [debt_col, rem_col]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)

all_ports = [p for p in df[port_col].unique() if pd.notna(p) and str(p).strip()]

st.markdown("""
> 💡 **محرك التوازن الذكي الأحادي والمزدوج:**
> - يمكن اختيار محفظة واحدة أو **عدة محافظ معاً**.
> - يقوم المحرك بتحليل التفاوت الحالي في (عدد العملاء + الرصيد المتبقي) لكل محصل.
> - يعيد التوزيع الذكي ليحقق أقصى توازن ممكن مع **الالتزام التام بعزل المحافظ** وتجميع مديونيات العميل الواحد معاً.
""")

st.markdown("---")

st.subheader("1️⃣ خطوة 1: اختيار المحافظ المراد فحصها وإعادة توازنها")
selected_ports = st.multiselect("اختر المحافظ (يمكنك اختيار محفظة واحدة أو أكثر):", all_ports, default=all_ports)

if not selected_ports:
    st.info("يرجى اختيار محفظة واحدة على الأقل للاستمرار.")
    st.stop()

sub_df = df[df[port_col].isin(selected_ports)].copy()

st.markdown("### 📊 تحليل الوضع الحالي (قبل التوازن):")

# Overall stats for selected portfolios
coll_summary = sub_df.groupby([port_col, coll_col]).agg(
    عدد_العملاء=(cust_col, 'nunique'),
    عدد_المديونيات=(rem_col, 'count'),
    إجمالي_المديونية=(debt_col, 'sum') if debt_col in sub_df.columns else (rem_col, 'sum'),
    إجمالي_المتبقي=(rem_col, 'sum')
).reset_index()

coll_summary.columns = ['المحفظة', 'المحصل', 'عدد العملاء', 'عدد المديونيات', 'إجمالي المديونية', 'إجمالي المتبقي']

tot_rem = coll_summary['إجمالي المتبقي'].sum()
coll_summary['نسبة المتبقي %'] = (coll_summary['إجمالي المتبقي'] / tot_rem * 100).round(2) if tot_rem > 0 else 0
coll_summary = coll_summary.sort_values(['المحفظة', 'إجمالي المتبقي'], ascending=[True, False])

# Imbalance Metrics
max_rem = coll_summary['إجمالي المتبقي'].max()
min_rem = coll_summary['إجمالي المتبقي'].min()
imb_ratio = (max_rem / min_rem) if min_rem > 0 else 999.0

max_cust = coll_summary['عدد العملاء'].max()
min_cust = coll_summary['عدد العملاء'].min()

b1, b2, b3, b4, b5 = st.columns(5)
b1.metric("المحافظ المختارة", f"{len(selected_ports):,}")
b2.metric("عدد المحصلين", f"{coll_summary['المحصل'].nunique():,}")
b3.metric("تفاوت المتبقي (أقصى/أقل)", f"{max_rem:,.0f} / {min_rem:,.0f}")
b4.metric("تفاوت العملاء (أقصى/أقل)", f"{max_cust:,} / {min_cust:,}")
b5.metric("مؤشر عدم التوازن", f"{imb_ratio:.2f}x")

st.markdown("---")

# Chart current loads
fig_current = px.bar(
    coll_summary, x='المحصل', y='إجمالي المتبقي', color='المحفظة',
    text_auto=',.0f', title='توزيع الرصيد المتبقي الحالي على المحصلين والمحافظ'
)
st.plotly_chart(fig_current, use_container_width=True)

with st.expander("📋 عرض جدول التحليل الحالي بالتفصيل"):
    st.dataframe(coll_summary.style.format({
        'عدد العملاء': '{:,}',
        'عدد المديونيات': '{:,}',
        'إجمالي المديونية': '{:,.2f}',
        'إجمالي المتبقي': '{:,.2f}',
        'نسبة المتبقي %': '{:.2f}%'
    }), use_container_width=True)

st.markdown("---")

st.subheader("2️⃣ خطوة 2: اختيار خوارزمية التوازن وتنفيذ إعادة التوزيع")

strategy_options = {
    "🎯 توازن مزدوج مركب (عدد العملاء + الرصيد المتبقي) [موصى به]": "dual_balance",
    "💰 توازن حسب الرصيد المتبقي فقط": "remaining_balance",
    "👥 توازن حسب عدد العملاء فقط": "customer_count"
}

chosen_label = st.radio("اختر استراتيجية التوازن المطلوبة:", list(strategy_options.keys()))
chosen_strategy = strategy_options[chosen_label]

if st.button("🚀 تشغيل محاكاة التوازن الآن", type="primary"):
    with st.spinner("جاري تطبيق خوارزمية Snake-Draft لإعادة التوازن المقترح..."):
        res = BalanceEngine.calculate_optimal_distribution(
            df, selected_ports, column_map, method=chosen_strategy
        )
        
        if res['success']:
            st.session_state['balance_result'] = res
            st.session_state['page_06_balance_clean_df'] = res['balanced_df'].copy()
            st.success("🎉 تم احتساب خطة التوازن المستهدفة وحفظ البيانات الجديدة بنجاح!")
        else:
            st.error(f"فشل احتساب التوازن: {res.get('message')}")

if 'balance_result' in st.session_state:
    res = st.session_state['balance_result']
    balanced_df = res['balanced_df']
    comparison = res['comparison']

    st.markdown("### 📈 مقارنة الأداء (قبل التوازن VS بعد التوازن المقترح):")

    st.dataframe(comparison.style.format({
        'العملاء (قبل)': '{:,}',
        'العملاء (بعد)': '{:,}',
        'المديونيات (قبل)': '{:,}',
        'المديونيات (بعد)': '{:,}',
        'المتبقي (قبل)': '{:,.2f}',
        'المتبقي (بعد)': '{:,.2f}'
    }), use_container_width=True)

    c_b1, c_b2 = st.columns(2)
    with c_b1:
        fig_before = px.bar(comparison, x='المحصل', y='المتبقي (قبل)', color='المحفظة', title='المتبقي قبل التوازن', text_auto=',.0f')
        st.plotly_chart(fig_before, use_container_width=True)
    with c_b2:
        fig_after = px.bar(comparison, x='المحصل', y='المتبقي (بعد)', color='المحفظة', title='المتبقي بعد التوازن المقترح ✨', text_auto=',.0f')
        st.plotly_chart(fig_after, use_container_width=True)

    # Export Excel
    excel_bytes = export_distribution(balanced_df, comparison, pd.DataFrame())
    st.download_button(
        label="📥 تحميل خطة التوازن التنافسية Excel",
        data=excel_bytes,
        file_name="portfolio_balanced_plan.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ─── زرار تحميل الشيت الأساسي والتقارير ───
from utils.shared_download import render_maharah_download_button
render_maharah_download_button("📥 تحميل التقرير النهائي (Excel Styled)", key_prefix="balance_page", page_key="page_06_balance")
