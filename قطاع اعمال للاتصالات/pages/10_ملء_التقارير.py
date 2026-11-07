# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import io
import re
from pathlib import Path
import sys

# Styling & RTL
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Cairo', sans-serif !important;
    direction: rtl !important;
    text-align: right !important;
    background-color: #f8fafc !important;
    color: #0f172a !important;
}

.stApp { background-color: #f8fafc !important; }

[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-left: 1px solid #e2e8f0 !important;
}

.tool-header {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 14px;
    padding: 24px;
    text-align: center;
    margin-bottom: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.section-box {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 18px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.section-header {
    background: #f1f5f9;
    border-right: 4px solid #1e293b;
    padding: 8px 14px;
    border-radius: 6px;
    color: #0f172a;
    font-size: 17px;
    font-weight: 800;
    margin: 16px 0 12px 0;
    border: 1px solid #e2e8f0;
}

[data-testid="metric-container"] {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 12px !important;
    padding: 16px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
[data-testid="stMetricValue"] { color: #0f172a !important; font-weight: 900 !important; font-size: 24px !important; }
[data-testid="stMetricLabel"] { color: #475569 !important; font-size: 13px !important; font-weight: 700 !important; }

.stDownloadButton > button {
    background: #059669 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    padding: 10px 24px !important;
    box-shadow: 0 2px 6px rgba(5, 150, 105, 0.2) !important;
}
.stDownloadButton > button:hover {
    background: #047857 !important;
}

.stButton > button {
    background: #ffffff !important;
    color: #1e293b !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
    border: 1px solid #cbd5e1 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.stButton > button:hover {
    background: #f1f5f9 !important;
    border-color: #94a3b8 !important;
}

.map-badge {
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    color: #1e293b;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  العنوان والترويسة
# ══════════════════════════════════════════════════════
st.markdown("""
<div class="tool-header">
    <div style="font-size:42px; margin-bottom:8px;">📝</div>
    <h2 style="color:#0f172a; font-weight:900; margin:0 0 6px 0;">برنامج ملء التقارير والقوالب</h2>
    <p style="color:#475569; font-size:14px; margin:0; font-weight:600;">
        تعبئة القوالب والشيتات الفارغة تلقائياً من شيت المحفظة مع إمكانية التصفية بالمشرفين والمحافظ ومطابقة الأعمدة بمرونة تامة
    </p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  الدوال المساعدة
# ══════════════════════════════════════════════════════
def clean_str(val):
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s

def detect_col(df, candidates):
    if df is None or df.empty:
        return None
    cols_map = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        if cand.strip().lower() in cols_map:
            return cols_map[cand.strip().lower()]
    for cand in candidates:
        for c in df.columns:
            if cand.strip().lower() in str(c).strip().lower():
                return c
    return None

def find_best_match(target_col, source_cols):
    """اقتراح أفضل عمود مطابق تلقائياً بناءً على تشابه الأسماء"""
    t_clean = re.sub(r'[_\-\s\(\)\[\]]', '', str(target_col)).lower()
    
    # تطابق تام بعد التنظيف
    for s in source_cols:
        s_clean = re.sub(r'[_\-\s\(\)\[\]]', '', str(s)).lower()
        if t_clean == s_clean:
            return s
            
    # تطابق جزئي
    for s in source_cols:
        s_clean = re.sub(r'[_\-\s\(\)\[\]]', '', str(s)).lower()
        if t_clean in s_clean or s_clean in t_clean:
            return s
            
    # قواميس مرادفات شائعة في قطاع التحصيل
    synonyms = {
        'هوية': ['رقم الهوية', 'الهوية', 'هوية العميل', 'السجل المدني', 'الاقامة', 'رقم هوية'],
        'مديونية': ['رقم المديونية', 'رقم المديوني', 'المديونية', 'حساب العميل', 'رقم الفاتورة'],
        'مبلغ': ['مبلغ المديونية', 'مبلغ الميدونية', 'مبلغ الميدونيه', 'الرصيد', 'المتبقي', 'مبلغ السداد'],
        'محفظ': ['المحافظ', 'المحفظة', 'اسم المحفظة', 'محفظه'],
        'مشرف': ['المشرف', 'اسم المشرف', 'مشرف الفريق'],
        'حصل': ['المحصل', 'اسم المحصل', 'الموظف', 'جامع الديون'],
        'تاريخ': ['تاريخ المتابعة', 'تاريخ السداد', 'تاريخ الاسناد', 'تاريخ الإسناد', 'تاريخ فصل الخدمة'],
        'حالة': ['الحالة الرئيسية', 'الحالة الفرعية', 'حالة الحساب', 'الوضع']
    }
    for syn_key, cand_list in synonyms.items():
        if syn_key in t_clean:
            for s in source_cols:
                s_l = str(s).lower()
                if any(c in s_l for c in cand_list):
                    return s
    return None

# ══════════════════════════════════════════════════════
#  الخطوة 1: رفع الشيتين
# ══════════════════════════════════════════════════════
st.markdown('<div class="section-header">📁 الخطوة الأولى: رفع ملف القالب وملف المحفظة</div>', unsafe_allow_html=True)

col_u1, col_u2 = st.columns(2)

with col_u1:
    st.markdown("**1️⃣ شيت القالب (الشيت المراد ملؤه):**")
    template_file = st.file_uploader(
        "رفع شيت القالب / التقرير المطلوب تعبئته",
        type=["xlsx", "xls", "csv"],
        key="uploader_template",
        help="ملف يحتوي على أسماء الأعمدة المراد ملؤها (سواء كان فارغاً تماماً أو فيه بيانات مسبقة كأرقام هويات)"
    )

with col_u2:
    st.markdown("**2️⃣ شيت المحفظة المصدر (البيانات الكاملة):**")
    source_file = st.file_uploader(
        "رفع شيت المحفظة المصدر",
        type=["xlsx", "xls", "csv"],
        key="uploader_source",
        help="الملف الأصلي الذي يحتوي على كافة بيانات العملاء والمديونيات والتفاصيل"
    )

if not template_file or not source_file:
    st.info("💡 يرجى رفع الملفين معاً للبدء في فحص الأعمدة وتحديد الفلاتر والمطابقة.")
    st.stop()

# قراءة الملفين
@st.cache_data(show_spinner="⏳ جاري قراءة الملفين وتحليل الأعمدة...")
def read_uploaded_file(file_bytes, file_name):
    buf = io.BytesIO(file_bytes)
    if file_name.endswith('.csv'):
        try:
            return pd.read_csv(buf, dtype=str, encoding='utf-8-sig')
        except:
            buf.seek(0)
            return pd.read_csv(buf, dtype=str, encoding='cp1256')
    else:
        try:
            return pd.read_excel(buf, dtype=str, engine='openpyxl')
        except:
            buf.seek(0)
            return pd.read_excel(buf, dtype=str, engine='xlrd')

try:
    df_template = read_uploaded_file(template_file.getvalue(), template_file.name)
    df_source   = read_uploaded_file(source_file.getvalue(), source_file.name)
except Exception as e:
    st.error(f"❌ حدث خطأ أثناء قراءة الملفات: {e}")
    st.stop()

# ══════════════════════════════════════════════════════
#  الخطوة 2: الفلاتر الاختيارية (المشرفين والمحافظ)
# ══════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<div class="section-header">🎛️ الخطوة الثانية: فلاتر اختيارية من شيت المحفظة</div>', unsafe_allow_html=True)
st.caption("✨ يمكنك تصفية البيانات بأخذ مشرفين أو محافظ معينة قبل ملء القالب (إذا تركتها فارغة سيتم أخذ كافة البيانات).")

# كشف أعمدة المشرف والمحفظة في شيت المحفظة
src_sup_col  = detect_col(df_source, ["المشرف", "اسم المشرف", "supervisor", "المشرف المباشر"])
src_port_col = detect_col(df_source, ["المحافظ", "المحفظة", "اسم المحفظة", "portfolio", "محفظه"])

c_f1, c_f2 = st.columns(2)

with c_f1:
    col_sup_chosen = st.selectbox(
        "👤 عمود المشرف في المحفظة:",
        options=["(لا يوجد / تخطي)"] + list(df_source.columns),
        index=(list(df_source.columns).index(src_sup_col) + 1) if src_sup_col in df_source.columns else 0,
        key="sel_src_sup_col"
    )

with c_f2:
    col_port_chosen = st.selectbox(
        "📂 عمود المحفظة في المحفظة:",
        options=["(لا يوجد / تخطي)"] + list(df_source.columns),
        index=(list(df_source.columns).index(src_port_col) + 1) if src_port_col in df_source.columns else 0,
        key="sel_src_port_col"
    )

# قوائم الاختيار للمشرفين والمحافظ
c_flt1, c_flt2 = st.columns(2)

selected_sups = []
if col_sup_chosen != "(لا يوجد / تخطي)":
    raw_sups = sorted([str(s).strip() for s in df_source[col_sup_chosen].dropna().unique() if str(s).strip() not in ('', 'nan', 'None')])
    with c_flt1:
        selected_sups = st.multiselect(
            f"👥 اختر المشرفين من عمود [{col_sup_chosen}] (اختياري - اتركه فارغاً للكل):",
            options=raw_sups,
            default=[],
            key="ms_sups"
        )

selected_ports = []
if col_port_chosen != "(لا يوجد / تخطي)":
    raw_ports = sorted([str(p).strip() for p in df_source[col_port_chosen].dropna().unique() if str(p).strip() not in ('', 'nan', 'None')])
    with c_flt2:
        selected_ports = st.multiselect(
            f"📂 اختر المحافظ من عمود [{col_port_chosen}] (اختياري - اتركه فارغاً للكل):",
            options=raw_ports,
            default=[],
            key="ms_ports"
        )

# تطبيق التصفية على شيت المحفظة
df_source_filtered = df_source.copy()

if selected_sups and col_sup_chosen != "(لا يوجد / تخطي)":
    df_source_filtered = df_source_filtered[df_source_filtered[col_sup_chosen].astype(str).str.strip().isin(selected_sups)]

if selected_ports and col_port_chosen != "(لا يوجد / تخطي)":
    df_source_filtered = df_source_filtered[df_source_filtered[col_port_chosen].astype(str).str.strip().isin(selected_ports)]

# إحصائيات سريعة بعد التصفية
k1, k2, k3 = st.columns(3)
k1.metric("📄 صفوف المحفظة بعد الفلترة", f"{len(df_source_filtered):,}", delta=f"{len(df_source_filtered) - len(df_source):,} من الإجمالي" if (selected_sups or selected_ports) else None)
k2.metric("📋 أعمدة القالب المطلوب ملؤها", f"{len(df_template.columns):,}")
k3.metric("📑 صفوف القالب المرفوع مسبقاً", f"{len(df_template):,}")

# ══════════════════════════════════════════════════════
#  الخطوة 3: تحديد طريقة الملء (Mode)
# ══════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<div class="section-header">⚙️ الخطوة الثالثة: طريقة ملء الشيت الفاضي / القالب</div>', unsafe_allow_html=True)

template_has_rows = len(df_template) > 0

mode_options = [
    "📥 تعبئة قالب فارغ (ترحيل كافة صفوف المحفظة المفلترة إلى القالب)",
    "🔗 مطابقة وتعبئة صفوف القالب الحالية بناءً على عمود ربط (مثل رقم الهوية / رقم المديونية)"
]

# اقتراح النمط الافتراضي بناءً على حالة القالب
default_mode_idx = 1 if template_has_rows else 0

fill_mode = st.radio(
    "اختر أسلوب التعبئة المناسب للقالب:",
    options=mode_options,
    index=default_mode_idx,
    key="radio_fill_mode"
)

is_lookup_mode = (fill_mode == mode_options[1])

key_template_col = None
key_source_col   = None

if is_lookup_mode:
    st.info("ℹ️ في هذا النمط: سيحتفظ القالب بصفوفه الحالية، ويتم جلب البيانات من المحفظة لكل صف يطابق عمود الربط المحدد.")
    c_k1, c_k2 = st.columns(2)
    with c_k1:
        key_template_col = st.selectbox(
            "🔑 عمود الربط الأساسي في شيت القالب:",
            options=list(df_template.columns),
            index=0,
            key="sel_key_template"
        )
    with c_k2:
        suggested_src_key = find_best_match(key_template_col, list(df_source.columns)) or list(df_source.columns)[0]
        key_source_col = st.selectbox(
            "🔑 عمود الربط المقابل له في شيت المحفظة:",
            options=list(df_source.columns),
            index=list(df_source.columns).index(suggested_src_key) if suggested_src_key in df_source.columns else 0,
            key="sel_key_source"
        )

# ══════════════════════════════════════════════════════
#  الخطوة 4: مطابقة الأعمدة (Column Mapping)
# ══════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<div class="section-header">🔄 الخطوة الرابعة: مطابقة أعمدة القالب مع أعمدة المحفظة</div>', unsafe_allow_html=True)
st.caption("قام النظام بمطابقة الأعمدة المتشابهة تلقائياً. يمكنك تعديل أي عمود أو اختيار [تجاهل / تركه فارغاً].")

# جدول أو قوائم اختيار لكل عمود بالقالب
template_cols = list(df_template.columns)
source_cols   = list(df_source.columns)

column_mapping = {}

col_grid_left, col_grid_right = st.columns(2)

for i, t_col in enumerate(template_cols):
    target_container = col_grid_left if (i % 2 == 0) else col_grid_right
    best_guess = find_best_match(t_col, source_cols)
    
    options = ["(تجاهل / تركه فارغاً)"] + source_cols
    default_idx = (options.index(best_guess)) if best_guess in options else 0

    with target_container:
        chosen_src = st.selectbox(
            f"🏷️ عمود القالب: [{t_col}]",
            options=options,
            index=default_idx,
            key=f"map_col_{i}_{t_col}"
        )
        if chosen_src != "(تجاهل / تركه فارغاً)":
            column_mapping[t_col] = chosen_src
        else:
            column_mapping[t_col] = None

# ملخص سريع للمطابقات
active_maps = {k: v for k, v in column_mapping.items() if v is not None}
st.success(f"✅ تم ربط **{len(active_maps)}** عموداً من أصل **{len(template_cols)}** عمود في القالب.")

# ══════════════════════════════════════════════════════
#  الخطوة 5: تنفيذ الملء وتوليد النتيجة
# ══════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<div class="section-header">⚡ الخطوة الخامسة: تنفيذ الملء والمعاينة</div>', unsafe_allow_html=True)

if st.button("🚀 ملء الشيت الآن وتوليد التقرير", type="primary", use_container_width=True):
    with st.spinner("⏳ جاري سحب وتسكين البيانات وفق المطابقة المحددة..."):
        if not is_lookup_mode:
            # ── النمط 1: ترحيل صفوف المحفظة المفلترة بالكامل إلى القالب ──
            df_result = pd.DataFrame(index=range(len(df_source_filtered)))
            for t_col in template_cols:
                s_col = column_mapping.get(t_col)
                if s_col and s_col in df_source_filtered.columns:
                    df_result[t_col] = df_source_filtered[s_col].values
                else:
                    df_result[t_col] = ""
        else:
            # ── النمط 2: مطابقة صفوف القالب بناءً على عمود الربط ──
            df_result = df_template.copy()
            src_clean_key = df_source_filtered[key_source_col].apply(clean_str)
            
            for t_col in template_cols:
                if t_col == key_template_col:
                    continue  # عمود المفتاح موجود مسبقاً
                s_col = column_mapping.get(t_col)
                if s_col and s_col in df_source_filtered.columns:
                    lookup_dict = dict(zip(src_clean_key, df_source_filtered[s_col]))
                    mapped_series = df_result[key_template_col].apply(clean_str).map(lookup_dict)
                    df_result[t_col] = mapped_series.fillna("")

        # حفظ النتيجة في session_state
        st.session_state['filled_result_df'] = df_result

        # دالة تصدير سريعة جداً باستخدام xlsxwriter
        def export_fast_styled_excel(df):
            try:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
                    df.to_excel(wr, index=False, sheet_name='الشيت المعبأ')
                    wb = wr.book
                    ws = wr.sheets['الشيت المعبأ']
                    ws.right_to_left()
                    
                    hdr_fmt = wb.add_format({
                        'bold': True, 'font_name': 'Segoe UI', 'font_size': 11,
                        'font_color': '#FFFFFF', 'bg_color': '#1E3A8A',
                        'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#93C5FD'
                    })
                    cell_fmt = wb.add_format({
                        'font_name': 'Segoe UI', 'font_size': 10, 'font_color': '#0F172A',
                        'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#CBD5E1'
                    })
                    ws.set_row(0, 26, hdr_fmt)
                    for col_idx, col_name in enumerate(df.columns):
                        ws.write(0, col_idx, str(col_name), hdr_fmt)
                        # حساب العرض التقريبي
                        sample_len = df[col_name].astype(str).str.len().head(50).max() if len(df) > 0 else 10
                        col_w = max(min(max(len(str(col_name)), sample_len if pd.notna(sample_len) else 10) + 4, 35), 12)
                        ws.set_column(col_idx, col_idx, col_w, cell_fmt)
                return buf.getvalue()
            except Exception:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as wr:
                    df.to_excel(wr, index=False, sheet_name='الشيت المعبأ')
                return buf.getvalue()

        # توليد الملفات وتخزينها مسبقاً في الذاكرة ليكون التنزيل فورياً
        st.session_state['filled_excel_bytes'] = export_fast_styled_excel(df_result)
        st.session_state['filled_csv_bytes']   = df_result.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.session_state['filled_base_name']   = Path(template_file.name).stem if template_file else "تقرير_معبأ"

# ══════════════════════════════════════════════════════
#  عرض النتيجة وزر التحميل الفوري
# ══════════════════════════════════════════════════════
if 'filled_result_df' in st.session_state and 'filled_excel_bytes' in st.session_state:
    df_out      = st.session_state['filled_result_df']
    excel_bytes = st.session_state['filled_excel_bytes']
    csv_bytes   = st.session_state['filled_csv_bytes']
    base_name   = st.session_state.get('filled_base_name', 'تقرير_معبأ')

    st.success(f"🎉 تم ملء الشيت بنجاح! الإجمالي: **{len(df_out):,}** صف و **{len(df_out.columns)}** عمود.")

    # صندوق أزرار التحميل
    st.markdown('<div class="section-box" style="text-align:center;">', unsafe_allow_html=True)
    st.markdown("### 📥 اضغط على الزر أدناه لتحميل الملف فوراً:")
    
    c_dl1, c_dl2 = st.columns(2)
    with c_dl1:
        st.download_button(
            label=f"📥 تحميل الشيت المعبأ كاملاً ({len(df_out):,} صف) - Excel",
            data=excel_bytes,
            file_name=f"تقرير_معبأ_{base_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
            key="dl_btn_filled_excel"
        )
    with c_dl2:
        st.download_button(
            label=f"📊 تحميل الشيت بصيغة CSV ({len(df_out):,} صف)",
            data=csv_bytes,
            file_name=f"تقرير_معبأ_{base_name}.csv",
            mime="text/csv",
            use_container_width=True,
            key="dl_btn_filled_csv"
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # جدول المعاينة
    st.markdown("---")
    st.markdown(f"#### 📋 معاينة البيانات المعبأة (أول 50 صف):")
    st.dataframe(df_out.head(50), use_container_width=True)

