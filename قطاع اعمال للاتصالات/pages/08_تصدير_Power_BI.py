import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="تصدير Power BI", page_icon="📊", layout="wide")
st.markdown("<style>body { direction: rtl; text-align: right; } .stApp { direction: rtl; }</style>", unsafe_allow_html=True)

st.title("📊 تصدير Power BI — Power BI Ready Package")
st.markdown("##### تجهيز وتصدير حزمة البيانات المتكاملة لبناء دشبوردات تنفيدية احترافية")

from utils.page_upload import page_portfolio_uploader, page_payment_uploader, render_supervisor_filter
from powerbi_exporter.packager import create_powerbi_zip_package, create_combined_excel_workbook
from powerbi_exporter.dax_generator import generate_dax_measures
from powerbi_exporter.theme_generator import generate_theme_json
from powerbi_exporter.doc_generator import (
    generate_relationships_df,
    generate_data_dictionary_df,
    generate_data_model_doc_df
)

# 1. Self-contained Per-Page Uploaders
df_full, col_map, raw_df = page_portfolio_uploader("page_08_pbi", label="📂 ارفع ملف المحفظة لتجهيز حزمة Power BI (Excel)")

if df_full is None or df_full.empty:
    st.stop()

# Supervisor filter
df = render_supervisor_filter(df_full, col_map, "page_08_pbi")

# Optional Payment File Uploader
payment_df, payment_map = page_payment_uploader("page_08_pbi", label="📂 ارفع ملف السدادات (اختياري لدمج حركات التحصيل والمطابقة في Power BI)")

st.markdown("---")

# 2. Build & Validate Power BI Package
with st.spinner("جاري بناء Star Schema والتحقق من العلاقات وجودة البيانات لـ Power BI..."):
    zip_bytes, val_report = create_powerbi_zip_package(
        clean_df=df,
        col_map=col_map,
        payment_df=payment_df,
        payment_map=payment_map
    )
    combined_excel_bytes = create_combined_excel_workbook(
        clean_df=df,
        col_map=col_map,
        payment_df=payment_df,
        payment_map=payment_map
    )

# 3. Display Executive Validation Metrics
st.markdown("### 📊 ملخص حزمة Power BI والتحقق من جودة البيانات:")

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("👥 إجمالي العملاء", f"{val_report['total_customers']:,}")
k2.metric("📋 عدد المديونيات", f"{val_report['total_debts']:,}")
k3.metric("💳 عدد السدادات", f"{val_report['total_payments']:,}")
k4.metric("💰 إجمالي المديونية", f"{val_report['total_debt_amount']:,.0f} ﷼")
k5.metric("💵 إجمالي التحصيل", f"{val_report['total_payment_amount']:,.0f} ﷼")
k6.metric("📈 نسبة التحصيل", f"{val_report['collection_rate_pct']:.1f}%")

if val_report['is_valid']:
    st.success("✅ **الحزمة جاهزة تماماً للاستيراد في Power BI (اجتازت كافة فحوصات السلامة والمفاتيح الرئيسية 100%)**")
else:
    st.warning("⚠️ **توجد بعض ملاحظات جودة البيانات، ولكن الحزمة جاهزة للتحميل والتصدير.**")

if val_report['data_quality_issues_count'] > 0:
    with st.expander("🔍 عرض تفاصيل جودة البيانات والتحذيرات (Data Quality Audit)"):
        st.dataframe(val_report['issues_df'], use_container_width=True)

st.markdown("---")

# 4. Power BI Export Buttons (Direct Combined Excel OR ZIP Package)
st.markdown("### 📥 التحميل والاستيراد المباشر لـ Power BI (Power BI Data Package):")

st.success("""
🟢 **الخيار الموصى به للاستيراد السريع الفوري (1-Click Import):**
قم بتحميل **`شيت Excel الموحد المباشر`**، ثم افتح Power BI واضغط **`Get Data` ➔ `Excel Workbook`** واختر الملف.
سيظهر لك جميع جداول الـ Star Schema كعلامات صح جاهزة للتحميل المباشر (`DimCustomer`, `FactDebt`, `FactPayment`, `DimCollector`...)!
""")

c_btn1, c_btn2 = st.columns(2)

with c_btn1:
    st.download_button(
        label="📗 🚀 تحميل شيت Excel الموحد المباشر لـ Power BI",
        data=combined_excel_bytes,
        file_name="PowerBI_Star_Schema_Combined.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="secondary",
        use_container_width=True,
        key="btn_dl_pbi_combined"
    )
    st.caption("✨ ملف إكسيل موحد فيه كل جداول Star Schema كشيتات منفصلة تجلبها بـ 1 Click من Power BI!")

with c_btn2:
    st.download_button(
        label="📦 🚀 تحميل الحزمة المضغوطة (ZIP Package)",
        data=zip_bytes,
        file_name="PowerBI_Export_Package.zip",
        mime="application/zip",
        type="secondary",
        use_container_width=True,
        key="btn_dl_pbi_zip"
    )
    st.caption("📦 مجلد مضغوط فيه ملفات Excel، صيغ DAX، ثيم الألوان، والتعليمات.")

st.markdown("---")
from utils.shared_download import render_maharah_download_button
render_maharah_download_button("📥 تحميل التقرير النهائي الشامل (Excel Styled)", key_prefix="pbi_page_top", page_key="page_08_pbi")
st.markdown("---")

# 5. Interactive Tabs Preview
tabs = st.tabs([
    "📐 مخطط النماذج والعلاقات (Star Schema)",
    "🧮 صيغ ومقاييس DAX (DAX Measures)",
    "🎨 ثيم وألوان Power BI (Theme JSON)",
    "📑 دليل صفحات الداشبورد الـ 11",
    "📖 دليل الاستيراد والتطبيق (README)"
])

with tabs[0]:
    st.markdown("### 📐 مخطط نموذج البيانات (Star Schema Data Model)")
    st.info("تم تجميع وتنظيف البيانات في النموذج النجمي (Star Schema) للحصول على أعلى أداء وسرعة في Power BI بدون Many-to-Many.")

    st.markdown("#### 1️⃣ العلاقات بين الجداول (Relationships):")
    st.dataframe(generate_relationships_df(), use_container_width=True)

    st.markdown("#### 2️⃣ وصف الجداول (Data Dictionary):")
    st.dataframe(generate_data_dictionary_df(), use_container_width=True)

with tabs[1]:
    st.markdown("### 🧮 صيغ ومقاييس DAX المجهزة (DAX Measures Library)")
    dax_dict = generate_dax_measures()

    for file_name, dax_code in dax_dict.items():
        with st.expander(f"📜 {file_name}"):
            st.code(dax_code, language="sql")

with tabs[2]:
    st.markdown("### 🎨 ملف الثيم والألوان الخاص بهوية الشركة (PowerBI_Theme.json)")
    st.markdown("احفظ هذا الكود في ملف `PowerBI_Theme.json` وتطبيقه في Power BI للحصول على ثيم احترافي مريح للعين بالألوان القياسية:")
    st.code(generate_theme_json(), language="json")

with tabs[3]:
    st.markdown("### 📑 تصميم صفحات الداشبورد الـ 11 الموصى بها في Power BI:")
    pages_info = [
        ("Page 1 — Executive Overview", "نظرة تنفيذية شاملة: KPIs العملاء والديون والتحصيل، اتجاه التحصيل، مقارنة المحافظ، أعلى المحصلين والحالات."),
        ("Page 2 — Portfolio Analysis", "تحليل المحافظ الـ 6: أداء كل محفظة، توزيع المديونيات والمتبقي، ونسبة التغطية."),
        ("Page 3 — Collection Performance", "أداء التحصيل اليومي والشهرى: المبالغ المحصلة، عدد العمليات، ومقارنة الفترات."),
        ("Page 4 — Collector Performance", "جدول رانك المحصلين، عدد العملاء المغطين، مبالغ التحصيل، ومؤشرات التدوير."),
        ("Page 5 — Supervisor Performance", "مقارنة أداء المشرفين وفرق العمل التابعة لهم."),
        ("Page 6 — Case Analysis", "تحليل الحالات الرئيسية والفرعية ومعدل السداد وتأثير الأخطاء والإهمال."),
        ("Page 7 — Customer 360", "شاشة البحث برقم الهوية لعرض الملف الكامل للعميل وتوقعات السداد."),
        ("Page 8 — Debt & Aging", "أعمار المديونيات وفئات التأخير والعملاء الراكدين."),
        ("Page 9 — Payment Behavior", "سلوك العملاء، التكرارية، ومتوسط أيام السداد واحتمالية السداد."),
        ("Page 10 — Data Quality", "شاشة جودة البيانات، المديونيات المكررة، والسدادات غير المطابقة."),
        ("Page 11 — Historical Trends", "اللاتجاهات التاريخية والنمو الشهري والسنوي (MoM & YoY).")
    ]
    for p_title, p_desc in pages_info:
        st.markdown(f"- **{p_title}:** {p_desc}")

with tabs[4]:
    st.markdown("### 📖 كراسة التعليمات الكاملة (README.txt)")
    from powerbi_exporter.doc_generator import generate_readme_text
    st.text_area("محتويات README.txt", generate_readme_text(val_report), height=400)
