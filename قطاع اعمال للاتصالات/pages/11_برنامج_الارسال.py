# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import io
import re
from pathlib import Path
import sys

# ══════════════════════════════════════════════════════
#  CSS احترافي وثيم كلاسيكي فاتح عالي التباين
# ══════════════════════════════════════════════════════
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

.sender-header {
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
    padding: 18px;
    margin-bottom: 16px;
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
    margin: 18px 0 12px 0;
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

.badge-channel {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 6px;
}
.badge-sms { background: #f1f5f9; color: #1e293b; border: 1px solid #cbd5e1; }
.badge-email { background: #f8fafc; color: #475569; border: 1px solid #cbd5e1; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  الترويسة الرئيسية
# ══════════════════════════════════════════════════════
st.markdown("""
<div class="sender-header">
    <div style="font-size:44px; margin-bottom:8px;">📢</div>
    <h2 style="color:#0f172a; font-weight:900; margin:0 0 6px 0;">برنامج الإرسال الذكي — حملات الرسائل والإيميلات</h2>
    <p style="color:#475569; font-size:14px; margin:0; font-weight:600;">
        فلترة المحفظة وتحديد أنسب العملاء تحصيلاً، تجميع المديونيات برقم الهوية، وتعبئة شيت فورمة الإرسال فورياً
    </p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  الدوال المساعدة
# ══════════════════════════════════════════════════════
def clean_id(val):
    if pd.isna(val): return ""
    s = str(val).strip()
    if s.endswith('.0'): s = s[:-2]
    return s

def to_clean_num(series):
    if series is None: return pd.Series(dtype=float)
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors='coerce').fillna(0.0)
    return pd.to_numeric(
        series.astype(str).str.replace(',', '', regex=False).str.replace(' ', '', regex=False).str.replace('﷼', '', regex=False),
        errors='coerce'
    ).fillna(0.0)

def detect_col(df, candidates):
    if df is None or df.empty: return None
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
    t_clean = re.sub(r'[_\-\s\(\)\[\]]', '', str(target_col)).lower()
    for s in source_cols:
        s_clean = re.sub(r'[_\-\s\(\)\[\]]', '', str(s)).lower()
        if t_clean == s_clean: return s
    for s in source_cols:
        s_clean = re.sub(r'[_\-\s\(\)\[\]]', '', str(s)).lower()
        if t_clean in s_clean or s_clean in t_clean: return s
    synonyms = {
        'هوية': ['رقم الهوية', 'الهوية', 'هوية العميل', 'السجل المدني', 'الاقامة'],
        'مديونية': ['رقم المديونية', 'رقم المديوني', 'المديونية', 'حساب العميل'],
        'متبقي': ['متبقي سداد موثق', 'المتبقي الموثق', 'المتبقي', 'مبلغ المديونية'],
        'مبلغ': ['مبلغ المديونية', 'مبلغ الميدونية', 'متبقي سداد موثق'],
        'محفظ': ['المحافظ', 'المحفظة', 'اسم المحفظة'],
        'مشرف': ['المشرف', 'اسم المشرف'],
        'حصل': ['المحصل', 'اسم المحصل'],
        'جوال': ['رقم الجوال', 'الجوال', 'الهاتف', 'رقم التواصل', 'الموبايل', 'mobile', 'phone'],
        'ايميل': ['البريد الالكتروني', 'البريد الإلكتروني', 'الايميل', 'الإيميل', 'email'],
        'حالة': ['الحالة الرئيسية', 'الحالة الفرعية', 'حالة الحساب'],
        'اجمالي': ['إجمالي مديونيات الهوية', 'إجمالي متبقي العميل', 'إجمالي متبقي السداد'],
        'إجمالي': ['إجمالي مديونيات الهوية', 'إجمالي متبقي العميل', 'إجمالي متبقي السداد'],
        'مجموع': ['إجمالي مديونيات الهوية', 'إجمالي متبقي العميل'],
        'رئيسي': ['الرقم الرئيسي', 'ارقام العميل'],
    }
    for syn_key, cand_list in synonyms.items():
        if syn_key in t_clean:
            for s in source_cols:
                s_l = str(s).lower()
                if any(c in s_l for c in cand_list): return s
    return None

# ══════════════════════════════════════════════════════
#  1. تحديد نوع قناة الإرسال
# ══════════════════════════════════════════════════════
st.markdown('<div class="section-header">📡 1. حدد نوع قناة الإرسال المستهدفة</div>', unsafe_allow_html=True)

channel_choice = st.radio(
    "اختر القناة المطلوبة للحملة:",
    [
        "📱 إرسال رسائل نصية / واتساب (SMS / WhatsApp)",
        "📧 إرسال بريد إلكتروني رسمي (Email Campaign)"
    ],
    horizontal=True,
    key="rad_channel"
)
is_sms_mode = ("SMS" in channel_choice)

if is_sms_mode:
    st.markdown('<span class="badge-channel badge-sms">📱 وضع حملات الرسائل النصية والواتساب</span> — يركز على كسر عدم التوصل، وعود السداد، والمبالغ المناسبة للدفع الفوري برابط.', unsafe_allow_html=True)
else:
    st.markdown('<span class="badge-channel badge-email">📧 وضع حملات البريد الإلكتروني</span> — يركز على قطاع الأعمال، المبالغ الكبيرة، عروض التسوية، والإخطارات الرسمية.', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  2. رفع الملفين (المحفظة + شيت الفورمة)
# ══════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<div class="section-header">📁 2. رفع شيت المحفظة المصدر وشيت فورمة الإرسال</div>', unsafe_allow_html=True)

c_up1, c_up2 = st.columns(2)

with c_up1:
    st.markdown("**📂 1️⃣ شيت المحفظة (البيانات الكاملة):**")
    source_file = st.file_uploader("رفع ملف المحفظة", type=["xlsx", "xls", "csv"], key="sender_src_file")

with c_up2:
    st.markdown("**📑 2️⃣ شيت فورمة الإرسال (القالب المراد تعبئته):**")
    form_file = st.file_uploader("رفع شيت الفورمة / القالب المطلوب تعبئته", type=["xlsx", "xls", "csv"], key="sender_form_file")

if not source_file or not form_file:
    st.info("💡 يرجى رفع الملفين معاً لمتابعة الفلترة وتحديد المستهدفين ومطابقة الأعمدة.")
    st.stop()

@st.cache_data(show_spinner="⏳ جارٍ قراءة الملفين...")
def load_data_file(file_bytes, file_name, smart_header=False):
    buf = io.BytesIO(file_bytes)
    if file_name.endswith('.csv'):
        try: return pd.read_csv(buf, dtype=str, encoding='utf-8-sig')
        except:
            buf.seek(0)
            return pd.read_csv(buf, dtype=str, encoding='cp1256')
    else:
        header_row = 0
        if smart_header:
            # الكشف الذكي عن صف الأعمدة الفعلي
            try:
                import openpyxl
                wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True, read_only=True)
                ws = wb.active
                for idx, row in enumerate(ws.iter_rows(values_only=True), start=0):
                    non_empty = [v for v in row if v is not None and str(v).strip() not in ('', 'None')]
                    if len(non_empty) >= 2:
                        header_row = idx
                        break
                wb.close()
            except Exception:
                header_row = 0
        buf.seek(0)
        try: return pd.read_excel(buf, dtype=str, engine='openpyxl', header=header_row)
        except:
            buf.seek(0)
            return pd.read_excel(buf, dtype=str, engine='xlrd', header=header_row)

try:
    df_src  = load_data_file(source_file.getvalue(), source_file.name)
    df_form = load_data_file(form_file.getvalue(), form_file.name, smart_header=True)
except Exception as e:
    st.error(f"❌ خطأ في قراءة الملفات: {e}")
    st.stop()

# ══════════════════════════════════════════════════════
#  3. اكتشاف الأعمدة وتطبيق الفلاتر الشاملة
# ══════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<div class="section-header">🎛️ 3. الفلاتر المسبقة لتحديد شريحة العملاء</div>', unsafe_allow_html=True)

# كشف الأعمدة الحيوية في شيت المحفظة
COL_CID      = detect_col(df_src, ["رقم الهوية", "الهوية", "هوية العميل", "السجل المدني", "customer_id"])
COL_DEBT_ID  = detect_col(df_src, ["رقم المديونية", "رقم المديوني", "debt_id"])
COL_REM_DOC  = detect_col(df_src, ["متبقي سداد موثق", "المتبقي الموثق", "المتبقي", "مبلغ المديونية", "مبلغ الميدونية"])
COL_PORT     = detect_col(df_src, ["المحافظ", "المحفظة", "اسم المحفظة", "portfolio"])
COL_SUP      = detect_col(df_src, ["المشرف", "اسم المشرف", "supervisor"])
COL_COLLECT  = detect_col(df_src, ["المحصل", "اسم المحصل", "collector"])
COL_MAIN_ST  = detect_col(df_src, ["الحالة الرئيسية", "الحالة", "main_status"])
COL_SUB_ST   = detect_col(df_src, ["الحالة الفرعية", "sub_status"])
COL_SERVICE  = detect_col(df_src, ["حالة الخدمة", "حالة الخط", "حالة الرقم", "الخدمة", "service_status"])
COL_BRANCH   = detect_col(df_src, ["الفرع", "اسم الفرع", "branch"])
COL_PHONE    = detect_col(df_src, ["رقم الجوال", "الجوال", "الهاتف", "رقم التواصل", "أرقام العميل", "phone", "mobile"])
COL_EMAIL    = detect_col(df_src, ["ايميل الشركة", "ايميل الشركه", "البريد الالكتروني", "البريد الإلكتروني", "الايميل", "الإيميل", "email"])
COL_SERVICE_TYPE = detect_col(df_src, ["نوع الخدمة", "نوع الخدمه", "service_type"])
COL_MAIN_PHONE   = detect_col(df_src, ["الرقم الرئيسي", "رقم رئيسي", "main_phone"])
COL_COMPANY_EMAIL= detect_col(df_src, ["ايميل الشركة", "ايميل الشركه", "company_email"])
COL_FOLLOWUP     = detect_col(df_src, ["المتابعة", "المتابعه", "تفاصيل المتابعة", "نتيجة المتابعة", "followup", "follow_up"])

# التحقق من الأعمدة
with st.expander("🔍 فحص وضبط أعمدة المحفظة المكتشفة", expanded=False):
    e1, e2, e3 = st.columns(3)
    with e1:
        COL_CID     = st.selectbox("عمود رقم الهوية *", df_src.columns.tolist(), index=df_src.columns.tolist().index(COL_CID) if COL_CID else 0, key="sel_c_cid")
        COL_DEBT_ID = st.selectbox("عمود رقم المديونية", df_src.columns.tolist(), index=df_src.columns.tolist().index(COL_DEBT_ID) if COL_DEBT_ID else 0, key="sel_c_debt")
        COL_REM_DOC = st.selectbox("عمود متبقي السداد", df_src.columns.tolist(), index=df_src.columns.tolist().index(COL_REM_DOC) if COL_REM_DOC else 0, key="sel_c_rem")
    with e2:
        COL_SUP     = st.selectbox("عمود المشرف", ["(غير متوفر)"] + df_src.columns.tolist(), index=df_src.columns.tolist().index(COL_SUP)+1 if COL_SUP else 0, key="sel_c_sup")
        COL_PORT    = st.selectbox("عمود المحفظة", ["(غير متوفر)"] + df_src.columns.tolist(), index=df_src.columns.tolist().index(COL_PORT)+1 if COL_PORT else 0, key="sel_c_port")
        COL_MAIN_ST = st.selectbox("عمود الحالة الرئيسية", ["(غير متوفر)"] + df_src.columns.tolist(), index=df_src.columns.tolist().index(COL_MAIN_ST)+1 if COL_MAIN_ST else 0, key="sel_c_main")
    with e3:
        COL_SUB_ST  = st.selectbox("عمود الحالة الفرعية", ["(غير متوفر)"] + df_src.columns.tolist(), index=df_src.columns.tolist().index(COL_SUB_ST)+1 if COL_SUB_ST else 0, key="sel_c_sub")
        COL_PHONE   = st.selectbox("عمود الجوال", ["(غير متوفر)"] + df_src.columns.tolist(), index=df_src.columns.tolist().index(COL_PHONE)+1 if COL_PHONE else 0, key="sel_c_phone")
        COL_EMAIL   = st.selectbox("عمود الإيميل", ["(غير متوفر)"] + df_src.columns.tolist(), index=df_src.columns.tolist().index(COL_EMAIL)+1 if COL_EMAIL else 0, key="sel_c_email")

# ── حساب كولوم "إجمالي مديونيات الهوية" على المحفظة كاملة (SUMIF بالضبط) ──
# = مجموع كل متبقي السداد لنفس رقم الهوية عبر كل المحفظة
_COL_TOTAL_KEY = 'إجمالي مديونيات الهوية'
if COL_CID and COL_CID in df_src.columns and COL_REM_DOC and COL_REM_DOC in df_src.columns:
    _rem_numeric = to_clean_num(df_src[COL_REM_DOC])
    _cid_clean_tmp = df_src[COL_CID].apply(clean_id)
    _total_map = _rem_numeric.groupby(_cid_clean_tmp).transform('sum')
    df_src[_COL_TOTAL_KEY] = _total_map.round(2)
else:
    df_src[_COL_TOTAL_KEY] = 0.0

# ── شاشة الفلاتر التفاعلية ──

f_c1, f_c2 = st.columns(2)

with f_c1:
    # فلتر المشرفين
    sups_list = sorted([str(s).strip() for s in df_src[COL_SUP].dropna().unique() if str(s).strip() not in ('', 'nan', 'None')]) if COL_SUP != "(غير متوفر)" else []
    sel_sups = st.multiselect("👥 اختيار المشرفين (اختياري - اتركه فارغاً لاختيار الكل):", options=sups_list, key="f_sups")

    # فلتر المحافظ
    ports_list = sorted([str(p).strip() for p in df_src[COL_PORT].dropna().unique() if str(p).strip() not in ('', 'nan', 'None')]) if COL_PORT != "(غير متوفر)" else []
    sel_ports = st.multiselect("📂 اختيار المحافظ (اختياري - اتركه فارغاً لاختيار الكل):", options=ports_list, key="f_ports")

    # فلتر الحالة الرئيسية
    main_st_list = sorted([str(m).strip() for m in df_src[COL_MAIN_ST].dropna().unique() if str(m).strip() not in ('', 'nan', 'None')]) if COL_MAIN_ST != "(غير متوفر)" else []
    sel_main_st = st.multiselect("📌 الحالة الرئيسية (اختياري):", options=main_st_list, key="f_main_st")

with f_c2:
    # فلتر الحالة الفرعية
    sub_st_list = sorted([str(s).strip() for s in df_src[COL_SUB_ST].dropna().unique() if str(s).strip() not in ('', 'nan', 'None')]) if COL_SUB_ST != "(غير متوفر)" else []
    sel_sub_st = st.multiselect("🔖 الحالة الفرعية (اختياري):", options=sub_st_list, key="f_sub_st")

    # فلتر حالة الخدمة
    serv_list = sorted([str(s).strip() for s in df_src[COL_SERVICE].dropna().unique() if str(s).strip() not in ('', 'nan', 'None')]) if COL_SERVICE and COL_SERVICE in df_src.columns else []
    sel_serv = st.multiselect("⚡ حالة الخدمة (اختياري):", options=serv_list, key="f_serv") if serv_list else []

    # فلتر الفرع
    branch_list = sorted([str(b).strip() for b in df_src[COL_BRANCH].dropna().unique() if str(b).strip() not in ('', 'nan', 'None')]) if COL_BRANCH and COL_BRANCH in df_src.columns else []
    sel_branch = st.multiselect("🏢 الفرع (اختياري):", options=branch_list, key="f_branch") if branch_list else []

    # فلتر نوع الخدمة
    serv_type_list = sorted([str(s).strip() for s in df_src[COL_SERVICE_TYPE].dropna().unique() if str(s).strip() not in ('', 'nan', 'None')]) if COL_SERVICE_TYPE and COL_SERVICE_TYPE in df_src.columns else []
    sel_serv_type = st.multiselect("📡 نوع الخدمة (اختياري):", options=serv_type_list, key="f_serv_type") if serv_type_list else []


# فلتر متبقي السداد الموثق
min_balance = st.number_input(
    "💰 متبقي سداد موثق أكبر من (ريال):",
    min_value=0.0,
    value=100.0 if is_sms_mode else 500.0,
    step=50.0,
    help="سيتم استبعاد المديونيات الأقل من هذا المبلغ لتركيز الحملة على المبالغ المستحقة فعلياً."
)

# ══════════════════════════════════════════════════════
#  4. تصفية البيانات وتجميعها برقم الهوية لمنع التكرار
# ══════════════════════════════════════════════════════
df_filtered = df_src.copy()

# تنظيف المبالغ
if COL_REM_DOC and COL_REM_DOC in df_filtered.columns:
    df_filtered['_rem_num'] = to_clean_num(df_filtered[COL_REM_DOC])
else:
    df_filtered['_rem_num'] = 0.0

# ── [وضع Email — أول خطوة]: استبعاد كل صف ملوش إيميل شركة صالح ──
if not is_sms_mode and COL_COMPANY_EMAIL and COL_COMPANY_EMAIL in df_filtered.columns:
    _ce = df_filtered[COL_COMPANY_EMAIL].astype(str).str.strip()
    _email_valid = _ce.str.contains('@', na=False) & ~_ce.isin(['', 'nan', 'None', 'NaN', 'none', '-', '#N/A', '#VALUE!'])
    _email_dropped = int((~_email_valid).sum())
    df_filtered = df_filtered[_email_valid]
    if _email_dropped > 0:
        st.info(f"📧 تم استبعاد **{_email_dropped:,} صف** لا يوجد لهم إيميل شركة صالح.")

# تطبيق الفلاتر
if sel_sups and COL_SUP != "(غير متوفر)":
    df_filtered = df_filtered[df_filtered[COL_SUP].astype(str).str.strip().isin(sel_sups)]

if sel_ports and COL_PORT != "(غير متوفر)":
    df_filtered = df_filtered[df_filtered[COL_PORT].astype(str).str.strip().isin(sel_ports)]

if sel_main_st and COL_MAIN_ST != "(غير متوفر)":
    df_filtered = df_filtered[df_filtered[COL_MAIN_ST].astype(str).str.strip().isin(sel_main_st)]

if sel_sub_st and COL_SUB_ST != "(غير متوفر)":
    df_filtered = df_filtered[df_filtered[COL_SUB_ST].astype(str).str.strip().isin(sel_sub_st)]

if sel_serv and COL_SERVICE and COL_SERVICE in df_filtered.columns:
    df_filtered = df_filtered[df_filtered[COL_SERVICE].astype(str).str.strip().isin(sel_serv)]

if sel_branch and COL_BRANCH and COL_BRANCH in df_filtered.columns:
    df_filtered = df_filtered[df_filtered[COL_BRANCH].astype(str).str.strip().isin(sel_branch)]

# فلتر نوع الخدمة
if sel_serv_type and COL_SERVICE_TYPE and COL_SERVICE_TYPE in df_filtered.columns:
    df_filtered = df_filtered[df_filtered[COL_SERVICE_TYPE].astype(str).str.strip().isin(sel_serv_type)]

if min_balance > 0:
    df_filtered = df_filtered[df_filtered['_rem_num'] >= min_balance]

# ── فلترة الرقم الرئيسي (وضع SMS فقط): لازم يبقى موجود وغير مكرر بين العملاء ──
if is_sms_mode and COL_MAIN_PHONE and COL_MAIN_PHONE in df_filtered.columns:
    _mp = df_filtered[COL_MAIN_PHONE].astype(str).str.strip()
    df_filtered = df_filtered[~_mp.isin(['', 'nan', 'None', 'NaN', 'none'])]
    # في حال تكرار الرقم الرئيسي بين عملاء مختلفين نحتفظ بصاحب أعلى مديونية
    df_filtered = df_filtered.sort_values('_rem_num', ascending=False).drop_duplicates(
        subset=[COL_MAIN_PHONE], keep='first'
    )


# ── استبعاد تلقائي للعملاء غير الصالحين (لا يخص / مقطوع / غير مستعمل) ──
# يبص في كولوم المتابعة + الحالة الرئيسية + الفرعية ويحذف أي سطر يحتوي على هذه الكلمات
_EXCLUDED_KEYWORDS = [
    'لا يخص', 'لايخص',
    'غير مستعمل', 'غيرمستعمل',
    'مقطوع',
    'لا يعمل', 'لايعمل',
    'خارج الخدمة', 'خارج خدمة',
    'رقم خاطئ', 'رقم مختلف',
    'لا يخدم',
]

def _contains_excluded(val):
    v = str(val).strip().lower()
    return any(kw.lower() in v for kw in _EXCLUDED_KEYWORDS)

_excl_mask = pd.Series([False] * len(df_filtered), index=df_filtered.index)
# كولوم المتابعة (الأهم — هنا بالضبط بتتكتب الملاحظات)
if COL_FOLLOWUP and COL_FOLLOWUP in df_filtered.columns:
    _excl_mask |= df_filtered[COL_FOLLOWUP].apply(_contains_excluded)
# الحالة الفرعية
if COL_SUB_ST and COL_SUB_ST in df_filtered.columns and COL_SUB_ST != "(غير متوفر)":
    _excl_mask |= df_filtered[COL_SUB_ST].apply(_contains_excluded)
# الحالة الرئيسية
if COL_MAIN_ST and COL_MAIN_ST in df_filtered.columns and COL_MAIN_ST != "(غير متوفر)":
    _excl_mask |= df_filtered[COL_MAIN_ST].apply(_contains_excluded)

_excluded_count = _excl_mask.sum()
df_filtered = df_filtered[~_excl_mask]
if _excluded_count > 0:
    st.info(f"🚫 تم استبعاد **{_excluded_count:,} صف** تلقائياً (لا يخص / مقطوع / غير مستعمل).")

# تنظيف الهوية
df_filtered['_cid_clean'] = df_filtered[COL_CID].apply(clean_id)
df_filtered = df_filtered[df_filtered['_cid_clean'] != ""]



# ── تجميع المديونيات على مستوى رقم الهوية (منع تكرار العميل) ──
def aggregate_customers(df):
    records = []
    for cid, grp in df.groupby('_cid_clean'):
        first_row = grp.iloc[0].to_dict()
        debt_count = len(grp)
        tot_rem = grp['_rem_num'].sum()
        
        # تجميع أرقام المديونيات إذا كانت متعددة
        all_debts = [clean_id(d) for d in grp[COL_DEBT_ID].dropna().tolist()] if COL_DEBT_ID else []
        debts_str = " | ".join(dict.fromkeys(all_debts)) if all_debts else str(first_row.get(COL_DEBT_ID, ''))

        record = first_row.copy()
        record['عدد المديونيات'] = debt_count
        record['إجمالي متبقي السداد'] = tot_rem
        if COL_DEBT_ID:
            record[COL_DEBT_ID] = debts_str
            
        records.append(record)
    return pd.DataFrame(records)

df_customers = aggregate_customers(df_filtered)

# ══════════════════════════════════════════════════════
#  5. خوارزمية الذكاء الاصطناعي لاختيار وترتيب أنسب العملاء
# ══════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<div class="section-header">⭐ 4. الترتيب الذكي واختيار أنسب العملاء تحصيلاً</div>', unsafe_allow_html=True)

use_smart_scoring = st.checkbox(
    "🎯 تفعيل محرك الذكاء الاصطناعي لترتيب العملاء بالأعلى تحصيلاً (AI Smart Prioritization)",
    value=True,
    help="يرتب العملاء تلقائياً بناءً على احتمالية السداد السريع وفق القناة المحددة (SMS أو Email)."
)

def calculate_smart_score(row, is_sms):
    score = 0.0
    main_st = str(row.get(COL_MAIN_ST, '')).lower() if COL_MAIN_ST != "(غير متوفر)" else ""
    sub_st  = str(row.get(COL_SUB_ST, '')).lower() if COL_SUB_ST != "(غير متوفر)" else ""
    rem     = float(row.get('إجمالي متبقي السداد', 0.0))

    if is_sms:
        # 1. وعود السداد (PTP)
        if any(k in main_st or k in sub_st for k in ['واعد بالسداد', 'طلب مهلة', 'مهلة للسداد']):
            score += 60
        # 2. كسر حاجز عدم التوصل (لا يرد / مغلق)
        elif any(k in sub_st for k in ['لايرد', 'لا يرد', 'لا برد', 'لابرد', 'مغلق', 'مغلق مؤقتا']):
            score += 45
        # 3. سداد جزئي
        elif 'سداد جزئي' in main_st or 'سداد جزئي' in sub_st:
            score += 40
        # 4. متابعة ومتجاوب
        elif 'متجاوب' in sub_st or 'متابعة' in main_st:
            score += 30
        
        # استبعاد أو خفض الأرقام التالفة
        if any(k in sub_st for k in ['مقطوع', 'غير مستعمل', 'لا يخص', 'خارج الخدمة']):
            score -= 100
        if 'تم السداد' in main_st or 'تم السداد' in sub_st:
            score -= 200

        # أولوية للمبالغ المتوسطة السريعة
        if 200 <= rem <= 3000:
            score += 20
        elif rem > 3000:
            score += 10

    else:
        # 📧 وضع الإيميل: أولوية المبالغ الكبيرة والشركات
        if rem >= 5000:
            score += 60
        elif rem >= 2000:
            score += 40
        elif rem >= 500:
            score += 20

        # وجود إيميل صالح
        email_val = str(row.get(COL_EMAIL, '')) if COL_EMAIL != "(غير متوفر)" else ""
        if '@' in email_val and '.' in email_val:
            score += 50
        else:
            score -= 40  # بدون إيميل يخفض جداً في حملة الإيميل

        # تسويات وإنذارات
        if any(k in sub_st or k in main_st for k in ['تسوية', 'اعتراض', 'طلب مهلة', 'انذار']):
            score += 30

        if 'تم السداد' in main_st:
            score -= 200

    return score

if not df_customers.empty and use_smart_scoring:
    df_customers['_smart_score'] = df_customers.apply(lambda r: calculate_smart_score(r, is_sms_mode), axis=1)
    df_customers = df_customers.sort_values(by=['_smart_score', 'إجمالي متبقي السداد'], ascending=[False, False]).reset_index(drop=True)
elif not df_customers.empty:
    df_customers = df_customers.sort_values(by='إجمالي متبقي السداد', ascending=False).reset_index(drop=True)

# ── مؤشرات الشريحة المستهدفة ──
tot_avail_cust = len(df_customers)
tot_avail_debt = df_customers['إجمالي متبقي السداد'].sum() if not df_customers.empty else 0.0

k1, k2, k3 = st.columns(3)
k1.metric("👥 إجمالي العملاء المؤهلين (بدون تكرار)", f"{tot_avail_cust:,}")
k2.metric("💰 إجمالي المتبقي المستهدف", f"{tot_avail_debt:,.0f} ﷼")
k3.metric("📊 إجمالي السجلات الأصلية بالمحفظة", f"{len(df_filtered):,}")

# ── تحديد الكوتة (كم عميل تريد أن ترسل له؟) ──
st.markdown("##### 🎯 تحديد عدد العملاء المطلوب إرسال الحملة لهم:")

c_q1, c_q2 = st.columns([1.5, 2.5])

with c_q1:
    quota_type = st.radio(
        "نطاق الإرسال:",
        ["اختيار عدد محدد (أفضل N عميل)", "إرسال لكافة العملاء المؤهلين"],
        key="rad_quota"
    )

with c_q2:
    if quota_type == "اختيار عدد محدد (أفضل N عميل)":
        target_count = st.number_input(
            "أدخل عدد العملاء المطلوب استهدافهم:",
            min_value=1,
            max_value=max(tot_avail_cust, 1),
            value=min(1000, tot_avail_cust) if tot_avail_cust > 0 else 1,
            step=100,
            key="num_target_count"
        )
    else:
        target_count = tot_avail_cust
        st.info(f"سيتم إرسال الحملة لكافة العملاء المؤهلين: **{tot_avail_cust:,} عميل**.")

# اقتطاع العدد المحدد من العملاء الفريدين
df_top_customers = df_customers.head(int(target_count)).copy() if not df_customers.empty else pd.DataFrame()

# ── اختيار أسلوب تفصيل المديونيات وتكرار الهوية ──
st.markdown("##### 📄 خيارات تكرار رقم الهوية وتفصيل المديونيات:")
debt_layout_mode = st.radio(
    "حدد الطريقة المطلوبة للتعامل مع رقم الهوية والمديونيات:",
    [
        "👑 رقم الهوية فريد تماماً (بدون أي تكرار - سطر واحد لكل هوية بأكبر مديونية وعدد العملاء = 1)",
        "📑 كل مديونية في سطر مستقل مع تقسيم العميل (0.5 و 0.5) ليكون إجمالي عدد العملاء صحيحاً",
        "📄 سطر واحد لكل عميل مع دمج أرقام المديونيات في نفس الخلية بفاصل ( | )"
    ],
    index=0,
    key="rad_debt_layout",
    help="الخيار الأول: يضمن لك أن رقم الهوية لن يتكرر نهائياً في الشيت، ويأخذ المديونية الأكبر للعميل برقمها المستقل ويكون عدد العملاء = 1. الخيار الثاني: يفصل كل مديونية في سطر ويقسم العميل (0.5 و 0.5). الخيار الثالث: يدمج أرقام المديونيات بفاصل."
)

if "رقم الهوية فريد تماماً" in debt_layout_mode and not df_top_customers.empty:
    # النمط 1: رقم الهوية فريد تماماً بدون أي تكرار
    target_cids = df_top_customers['_cid_clean'].unique()
    df_cand = df_filtered[df_filtered['_cid_clean'].isin(target_cids)].copy()
    
    # اختيار المديونية الأكبر للعميل
    idx_max = df_cand.groupby('_cid_clean')['_rem_num'].idxmax()
    df_export_ready = df_cand.loc[idx_max].copy()
    
    # حساب إجمالي المديونيات والمتبقي الكلي
    counts_map = df_cand.groupby('_cid_clean')['_cid_clean'].count()
    tot_rem_map = df_cand.groupby('_cid_clean')['_rem_num'].sum()
    
    df_export_ready['عدد العملاء'] = 1
    df_export_ready['عدد مديونيات العميل'] = df_export_ready['_cid_clean'].map(counts_map)
    df_export_ready['إجمالي متبقي العميل'] = df_export_ready['_cid_clean'].map(tot_rem_map)
    # ← SUMIF: إجمالي متبقي السداد لكل رقم هوية (مفيد لحقل الفورمة)
    df_export_ready['إجمالي مديونيات الهوية'] = df_export_ready['_cid_clean'].map(tot_rem_map)
    
    # الحفاظ على ترتيب الأولوية
    cid_order = {cid: idx for idx, cid in enumerate(df_top_customers['_cid_clean'])}
    df_export_ready['_sort_order'] = df_export_ready['_cid_clean'].map(cid_order)
    df_export_ready = df_export_ready.sort_values(by='_sort_order').drop(columns=['_sort_order']).reset_index(drop=True)

elif "كل مديونية في سطر" in debt_layout_mode and not df_top_customers.empty:
    # النمط 2: كل مديونية في سطر مستقل مع وزن كسري (0.5 و 0.5)
    target_cids = df_top_customers['_cid_clean'].unique()
    df_expanded = df_filtered[df_filtered['_cid_clean'].isin(target_cids)].copy()
    
    counts_series = df_expanded.groupby('_cid_clean')['_cid_clean'].transform('count')
    tot_rem_series = df_expanded.groupby('_cid_clean')['_rem_num'].transform('sum')
    df_expanded['عدد مديونيات العميل'] = counts_series
    df_expanded['عدد العملاء'] = (1.0 / counts_series).apply(lambda v: 1 if v == 1.0 else round(v, 2))
    df_expanded['إجمالي متبقي العميل'] = tot_rem_series
    # ← SUMIF: إجمالي متبقي السداد لكل رقم هوية (مفيد لحقل الفورمة)
    df_expanded['إجمالي مديونيات الهوية'] = tot_rem_series
    
    cid_order = {cid: idx for idx, cid in enumerate(df_top_customers['_cid_clean'])}
    df_expanded['_sort_order'] = df_expanded['_cid_clean'].map(cid_order)
    df_export_ready = df_expanded.sort_values(by=['_sort_order', '_rem_num'], ascending=[True, False]).drop(columns=['_sort_order']).reset_index(drop=True)

else:
    # النمط 3: سطر واحد مدمج بـ |
    df_top_customers['عدد العملاء'] = 1
    df_top_customers['عدد مديونيات العميل'] = df_top_customers.get('عدد المديونيات', 1)
    df_top_customers['إجمالي متبقي العميل'] = df_top_customers.get('إجمالي متبقي السداد', 0.0)
    # ← SUMIF: إجمالي متبقي السداد لكل رقم هوية (مفيد لحقل الفورمة)
    df_top_customers['إجمالي مديونيات الهوية'] = df_top_customers.get('إجمالي متبقي السداد', 0.0)
    df_export_ready = df_top_customers.copy()

# ══════════════════════════════════════════════════════
#  6. مطابقة أعمدة الفورمة (Column Mapping)
# ══════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<div class="section-header">🔄 5. مطابقة أعمدة الفورمة مع أعمدة المحفظة</div>', unsafe_allow_html=True)
st.caption("اختر لكل عمود في الفورمة ما يقابله من بيانات العملاء، أو اختر [تجاهل / تركه فارغاً].")

form_cols   = list(df_form.columns)
avail_cols  = list(df_export_ready.columns)

col_map = {}
col_grid_1, col_grid_2 = st.columns(2)

for i, f_col in enumerate(form_cols):
    container = col_grid_1 if (i % 2 == 0) else col_grid_2
    guess = find_best_match(f_col, avail_cols)
    opts = ["(تجاهل / تركه فارغاً)"] + avail_cols
    def_idx = opts.index(guess) if guess in opts else 0

    with container:
        chosen = st.selectbox(
            f"🏷️ عمود الفورمة: [{f_col}]",
            options=opts,
            index=def_idx,
            key=f"send_map_{i}_{f_col}"
        )
        col_map[f_col] = chosen if chosen != "(تجاهل / تركه فارغاً)" else None

mapped_count = len([v for v in col_map.values() if v is not None])
st.success(f"✅ تم ربط **{mapped_count}** من أصل **{len(form_cols)}** عمود في شيت الفورمة.")

# ══════════════════════════════════════════════════════
#  7. التنفيذ والتصدير الفوري
# ══════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<div class="section-header">🚀 6. توليد شيت الإرسال والتحميل الفوري</div>', unsafe_allow_html=True)

if st.button("⚡ ملء وتجهيز شيت الإرسال الآن", type="primary", use_container_width=True):
    if df_export_ready.empty:
        st.warning("⚠️ لا توجد بيانات مطابقة للفلاتر المحددة.")
    else:
        with st.spinner("⏳ جاري تسكين بيانات العملاء في شيت الفورمة..."):
            df_out_form = pd.DataFrame(index=range(len(df_export_ready)))
            for f_col in form_cols:
                src_field = col_map.get(f_col)
                if src_field and src_field in df_export_ready.columns:
                    df_out_form[f_col] = df_export_ready[src_field].values
                else:
                    df_out_form[f_col] = ""

            st.session_state['sender_result_df'] = df_out_form

            # توليد الإكسيل وحفظه مسبقاً
            def export_sender_excel(df):
                try:
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
                        df.to_excel(wr, index=False, sheet_name='حملة_الإرسال')
                        wb = wr.book
                        ws = wr.sheets['حملة_الإرسال']
                        ws.right_to_left()
                        
                        hdr_bg = '#1E3A8A' if is_sms_mode else '#4C1D95'
                        hdr_fmt = wb.add_format({
                            'bold': True, 'font_name': 'Segoe UI', 'font_size': 11,
                            'font_color': '#FFFFFF', 'bg_color': hdr_bg,
                            'align': 'center', 'valign': 'vcenter', 'border': 1
                        })
                        cell_fmt = wb.add_format({
                            'font_name': 'Segoe UI', 'font_size': 10, 'font_color': '#0F172A',
                            'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#CBD5E1'
                        })
                        ws.set_row(0, 26, hdr_fmt)
                        for col_idx, col_name in enumerate(df.columns):
                            ws.write(0, col_idx, str(col_name), hdr_fmt)
                            sample_len = df[col_name].astype(str).str.len().head(50).max() if len(df) > 0 else 10
                            col_w = max(min(max(len(str(col_name)), sample_len if pd.notna(sample_len) else 10) + 4, 35), 12)
                            ws.set_column(col_idx, col_idx, col_w, cell_fmt)
                    return buf.getvalue()
                except Exception:
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine='openpyxl') as wr:
                        df.to_excel(wr, index=False, sheet_name='حملة_الإرسال')
                    return buf.getvalue()

            st.session_state['sender_excel_bytes'] = export_sender_excel(df_out_form)
            st.session_state['sender_csv_bytes']   = df_out_form.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            channel_name = "رسائل_SMS" if is_sms_mode else "ايميلات_Email"
            st.session_state['sender_file_name']   = f"حملة_{channel_name}_{len(df_out_form)}_عميل"

# عرض النتيجة وزر التحميل الفوري
if 'sender_result_df' in st.session_state and 'sender_excel_bytes' in st.session_state:
    df_res      = st.session_state['sender_result_df']
    excel_bytes = st.session_state['sender_excel_bytes']
    csv_bytes   = st.session_state['sender_csv_bytes']
    file_name   = st.session_state.get('sender_file_name', 'حملة_إرسال')

    st.success(f"🎉 تم تجهيز شيت الحملة بنجاح! جاهز للإرسال لعدد: **{len(df_res):,} عميل فريد**.")

    st.markdown('<div class="section-box" style="text-align:center;">', unsafe_allow_html=True)
    st.markdown("### 📥 اضغط أدناه لتحميل شيت الحملة المعبأ فوراً:")
    
    cd1, cd2 = st.columns(2)
    with cd1:
        st.download_button(
            label=f"📥 تحميل شيت الإرسال Excel ({len(df_res):,} عميل)",
            data=excel_bytes,
            file_name=f"{file_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
            key="dl_sender_excel"
        )
    with cd2:
        st.download_button(
            label=f"📊 تحميل شيت الإرسال CSV ({len(df_res):,} عميل)",
            data=csv_bytes,
            file_name=f"{file_name}.csv",
            mime="text/csv",
            use_container_width=True,
            key="dl_sender_csv"
        )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("#### 📋 معاينة الشيت المجهز للإرسال (أول 50 عميل):")
    st.dataframe(df_res.head(50), use_container_width=True)
