import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="تحليل المحافظ", page_icon="📂", layout="wide")
st.markdown("<style>body { direction: rtl; text-align: right; } .stApp { direction: rtl; }</style>", unsafe_allow_html=True)

st.title("📂 تحليل المحافظ والتفاصيل التشغيلية")

from utils.page_upload import page_portfolio_uploader, render_supervisor_filter

df_full, col_map, raw_df = page_portfolio_uploader("page_02_portfolio", label="📂 ارفع ملف المحفظة لتحليل المحافظ (Excel)")

if df_full is None or df_full.empty:
    st.stop()

df = render_supervisor_filter(df_full, col_map, "page_02_portfolio")

from utils.shared_download import render_maharah_download_button
render_maharah_download_button("📥 تحميل التقرير النهائي الشامل (Excel Styled)", key_prefix="portfolio_analysis_top", page_key="page_02_portfolio")
st.markdown("---")

cust_col = col_map.get('customer_id') or ('_customer_id' if '_customer_id' in df.columns else 'رقم الهوية')
debt_col = col_map.get('debt_amount') or ('مبلغ المديونية' if 'مبلغ المديونية' in df.columns else 'مبلغ الميدونية')
paid_col = col_map.get('paid_doc') or ('السدادات الموثقة' if 'السدادات الموثقة' in df.columns else '_paid_doc')
rem_col = col_map.get('remaining_doc') or ('متبقي سداد موثق' if 'متبقي سداد موثق' in df.columns else '_remaining_doc')
port_col = col_map.get('portfolio') or ('المحافظ' if 'المحافظ' in df.columns else '_portfolio')
coll_col = col_map.get('collector') or ('المحصل' if 'المحصل' in df.columns else '_collector')

# Ensure numeric columns are cast to float cleanly
for c in [debt_col, paid_col, rem_col]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)

tabs = st.tabs(['📊 نظرة عامة على المحافظ', '🔍 تفاصيل المحفظة والمحصلين', '👤 بحث وتحليل العملاء', '⚖️ مقارنة المحافظ'])

with tabs[0]:
    st.subheader("📊 نظرة عامة وإحصائيات المحافظ")
    if port_col in df.columns:
        overview = df.groupby(port_col).agg(
            عدد_السجلات=(cust_col, 'count'),
            عدد_العملاء=(cust_col, 'nunique'),
            إجمالي_المديونية=(debt_col, 'sum') if debt_col in df.columns else (rem_col, 'sum'),
            السدادات=(paid_col, 'sum') if paid_col in df.columns else (rem_col, 'sum'),
            المتبقي=(rem_col, 'sum') if rem_col in df.columns else (debt_col, 'sum')
        ).reset_index()
        
        overview.columns = ['المحفظة', 'عدد السجلات', 'عدد العملاء', 'إجمالي المديونية', 'السدادات الموثقة', 'إجمالي المتبقي']
        
        st.dataframe(overview.style.format({
            'عدد السجلات': '{:,}',
            'عدد العملاء': '{:,}',
            'إجمالي المديونية': '{:,.2f}',
            'السدادات الموثقة': '{:,.2f}',
            'إجمالي المتبقي': '{:,.2f}'
        }), use_container_width=True)

with tabs[1]:
    st.subheader("🔍 تفاصيل أداء المحصلين حسب المحفظة")
    if port_col in df.columns:
        unique_ports = [p for p in df[port_col].unique() if pd.notna(p) and str(p).strip()]
        selected_port = st.selectbox("اختر المحفظة المراد استعراضها:", unique_ports)
        port_df = df[df[port_col] == selected_port]
        
        st.markdown(f"#### إحصائيات المحصلين في محفظة **{selected_port}**:")
        if coll_col in port_df.columns:
            coll_stats = port_df.groupby(coll_col).agg(
                عدد_العملاء=(cust_col, 'nunique'),
                عدد_المديونيات=(cust_col, 'count'),
                إجمالي_المديونية=(debt_col, 'sum') if debt_col in port_df.columns else (rem_col, 'sum'),
                إجمالي_المتبقي=(rem_col, 'sum') if rem_col in port_df.columns else (debt_col, 'sum')
            ).reset_index()
            coll_stats.columns = ['المحصل', 'عدد العملاء', 'عدد المديونيات', 'إجمالي المديونية', 'إجمالي المتبقي']
            coll_stats = coll_stats.sort_values('إجمالي المتبقي', ascending=False)
            
            st.dataframe(coll_stats.style.format({
                'عدد العملاء': '{:,}',
                'عدد المديونيات': '{:,}',
                'إجمالي المديونية': '{:,.2f}',
                'إجمالي المتبقي': '{:,.2f}'
            }), use_container_width=True)

with tabs[2]:
    st.subheader("👤 بحث واستعلام عن سجلات عميل")
    search_id = st.text_input("أدخل رقم الهوية أو كلمة من اسم العميل للبحث:")
    if search_id:
        search_str = str(search_id).strip()
        matched_mask = df[cust_col].astype(str).str.contains(search_str, case=False, na=False)
        if 'اسم العميل' in df.columns:
            matched_mask = matched_mask | df['اسم العميل'].astype(str).str.contains(search_str, case=False, na=False)
        
        cust_df = df[matched_mask]
        if not cust_df.empty:
            st.success(f"✅ تم العثور على {len(cust_df)} مديونيات تابعة للبحث!")
            st.dataframe(cust_df, use_container_width=True)
        else:
            st.warning("⚠️ لم يتم العثور على أي نتائج مطابقة.")

with tabs[3]:
    st.subheader("⚖️ مقارنة بين محفظتين")
    if port_col in df.columns:
        ports = [p for p in df[port_col].unique() if pd.notna(p) and str(p).strip()]
        if len(ports) >= 2:
            p1, p2 = st.columns(2)
            with p1:
                port1 = st.selectbox("اختر المحفظة الأولى:", ports, index=0, key='p1')
            with p2:
                port2 = st.selectbox("اختر المحفظة الثانية:", ports, index=1 if len(ports)>1 else 0, key='p2')
                
            if port1 and port2:
                df1 = df[df[port_col] == port1]
                df2 = df[df[port_col] == port2]
                
                comp_data = {
                    "المؤشر التشغيلي": ["عدد السجلات", "عدد العملاء الفريدين", "إجمالي المديونية (ريال)", "إجمالي المتبقي (ريال)"],
                    f"محفظة ({port1})": [
                        f"{len(df1):,}",
                        f"{df1[cust_col].nunique():,}",
                        f"{df1[debt_col].sum():,.2f}" if debt_col in df1.columns else "0.00",
                        f"{df1[rem_col].sum():,.2f}" if rem_col in df1.columns else "0.00"
                    ],
                    f"محفظة ({port2})": [
                        f"{len(df2):,}",
                        f"{df2[cust_col].nunique():,}",
                        f"{df2[debt_col].sum():,.2f}" if debt_col in df2.columns else "0.00",
                        f"{df2[rem_col].sum():,.2f}" if rem_col in df2.columns else "0.00"
                    ]
                }
                comp_df = pd.DataFrame(comp_data)
                st.dataframe(comp_df, use_container_width=True)
        else:
            st.info("تتطلب المقارنة وجود محفظتين على الأقل في البيانات.")

# ─── زرار تحميل الشيت الأساسي + التقارير ───
st.markdown("---")
from utils.shared_download import render_maharah_download_button
render_maharah_download_button("📥 تحميل التقرير النهائي (Excel Styled)", key_prefix="portfolio_analysis_bottom", page_key="page_02_portfolio")
