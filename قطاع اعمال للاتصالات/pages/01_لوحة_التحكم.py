import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import sys

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="لوحة التحكم", page_icon="📊", layout="wide")
st.markdown("<style>body { direction: rtl; text-align: right; } .stApp { direction: rtl; }</style>", unsafe_allow_html=True)

st.title("📊 لوحة التحكم التنفيذية")

from utils.page_upload import page_portfolio_uploader, render_supervisor_filter

df_full, col_map, raw_df = page_portfolio_uploader("page_01_dashboard", label="📂 ارفع ملف المحفظة للوحة التحكم (Excel)")

if df_full is None or df_full.empty:
    st.stop()

df = render_supervisor_filter(df_full, col_map, "page_01_dashboard")

# Extract mapped columns safely
cust_col = col_map.get('customer_id', '_customer_id') if '_customer_id' in df.columns else 'رقم الهوية'
debt_col = col_map.get('debt_amount') or ('مبلغ المديونية' if 'مبلغ المديونية' in df.columns else 'مبلغ الميدونية')
paid_col = col_map.get('paid_doc', 'السدادات الموثقة')
rem_col = col_map.get('remaining_doc', 'متبقي سداد موثق')
port_col = col_map.get('portfolio', 'المحافظ')
coll_col = col_map.get('collector', 'المحصل')
sup_col = col_map.get('supervisor', 'المشرف')
status_col = col_map.get('main_status', 'الحالة الرئيسية')

# Ensure numeric types for calculation
total_records = len(df)
total_customers = df[cust_col].nunique() if cust_col in df.columns else df['_customer_id'].nunique()

total_debt = pd.to_numeric(df[debt_col], errors='coerce').fillna(0.0).sum() if debt_col in df.columns else 0.0
total_paid = pd.to_numeric(df[paid_col], errors='coerce').fillna(0.0).sum() if paid_col in df.columns else 0.0
total_remaining = pd.to_numeric(df[rem_col], errors='coerce').fillna(0.0).sum() if rem_col in df.columns else 0.0

# If payments file is uploaded, include its total
payment_df = st.session_state.get('payment_df')
if payment_df is not None and not payment_df.empty:
    pay_file_total = pd.to_numeric(payment_df['_payment_amount'], errors='coerce').fillna(0.0).sum()
else:
    pay_file_total = 0.0

pay_rate = (total_paid / total_debt * 100.0) if total_debt > 0 else 0.0

st.markdown("### 📈 مؤشرات الأداء الرئيسية (KPIs)")
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("إجمالي السجلات", f"{total_records:,}")
col2.metric("إجمالي العملاء", f"{total_customers:,}")
col3.metric("إجمالي المديونية", f"{total_debt:,.2f} ريال")
col4.metric("السدادات الموثقة", f"{total_paid:,.2f} ريال")
col5.metric("إجمالي المتبقي", f"{total_remaining:,.2f} ريال")
col6.metric("نسبة السداد الموثق", f"{pay_rate:.2f}%")

st.markdown("---")

portfolios_count = df[port_col].nunique() if port_col in df.columns else 0
collectors_count = df[coll_col].nunique() if coll_col in df.columns else 0
supervisors_count = df[sup_col].nunique() if sup_col in df.columns else 0
errors_count = st.session_state.get('total_errors', 0)
neglect_count = st.session_state.get('total_neglected', 0)

cc1, cc2, cc3, cc4, cc5, cc6 = st.columns(6)
cc1.metric("عدد المحافظ", f"{portfolios_count:,}")
cc2.metric("عدد المحصلين", f"{collectors_count:,}")
cc3.metric("عدد المشرفين", f"{supervisors_count:,}")
cc4.metric("سدادات الشيت المرفوع", f"{pay_file_total:,.2f} ريال")
cc5.metric("أخطاء النظام", f"{errors_count:,}")
cc6.metric("الحالات المهملة", f"{neglect_count:,}")

st.markdown("---")
from utils.shared_download import render_maharah_download_button
render_maharah_download_button("📥 تحميل التقرير النهائي الشامل (Excel Styled)", key_prefix="dashboard_top", page_key="page_01_dashboard")
st.markdown("---")

col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    if status_col in df.columns:
        status_counts = df[status_col].value_counts().reset_index()
        status_counts.columns = ['الحالة', 'العدد']
        fig_pie = px.pie(status_counts, values='العدد', names='الحالة', title='توزيع الحالة الرئيسية', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

with col_chart2:
    if port_col in df.columns and debt_col in df.columns:
        portfolio_debt = df.groupby(port_col)[debt_col].sum().reset_index()
        portfolio_debt.columns = ['المحفظة', 'المديونية']
        fig_bar1 = px.bar(portfolio_debt, x='المحفظة', y='المديونية', title='إجمالي المديونية حسب المحفظة', text_auto=',.2f')
        st.plotly_chart(fig_bar1, use_container_width=True)

st.markdown("### 🏆 أعلى 10 محصلين حسب الرصيد المتبقي")
if coll_col in df.columns and rem_col in df.columns:
    collector_rem = df.groupby(coll_col)[rem_col].sum().reset_index()
    collector_rem.columns = ['المحصل', 'المتبقي']
    collector_rem = collector_rem.sort_values('المتبقي', ascending=False).head(10)
    fig_bar2 = px.bar(collector_rem, x='المحصل', y='المتبقي', text_auto=',.2f', color='المتبقي')
    st.plotly_chart(fig_bar2, use_container_width=True)

st.markdown("### 📊 توزيع العملاء والمديونيات حسب المحافظ")
if port_col in df.columns:
    port_summary = df.groupby(port_col).agg(
        عدد_العملاء=(cust_col, 'nunique') if cust_col in df.columns else ('_customer_id', 'nunique'),
        عدد_المديونيات=(rem_col, 'count'),
        إجمالي_المديونية=(debt_col, 'sum') if debt_col in df.columns else (rem_col, 'sum'),
        إجمالي_المتبقي=(rem_col, 'sum')
    ).reset_index()
    port_summary.columns = ['المحفظة', 'عدد العملاء', 'عدد المديونيات', 'إجمالي المديونية (ريال)', 'إجمالي المتبقي (ريال)']
    
    # Format currency display nicely
    st.dataframe(port_summary.style.format({
        'عدد العملاء': '{:,}',
        'عدد المديونيات': '{:,}',
        'إجمالي المديونية (ريال)': '{:,.2f}',
        'إجمالي المتبقي (ريال)': '{:,.2f}'
    }), use_container_width=True)

# ─── زرار تحميل الشيت الأساسي + التقارير ───
st.markdown("---")
from utils.shared_download import render_maharah_download_button
render_maharah_download_button("📥 تحميل التقرير النهائي (Excel Styled)", key_prefix="dashboard_bottom", page_key="page_01_dashboard")
