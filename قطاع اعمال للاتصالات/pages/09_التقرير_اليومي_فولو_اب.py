import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import sys
from datetime import date, timedelta
import io

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="التقرير اليومي - فولو اب", page_icon="📈", layout="wide")

# ══════════════════════════════════════════════════════
#  CSS احترافي وثيم كحلي غامق فخم
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

[data-testid="metric-container"] {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: transform 0.2s, box-shadow 0.2s;
}
[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
}
[data-testid="stMetricValue"] { color: #0f172a !important; font-weight: 900 !important; font-size: 24px !important; }
[data-testid="stMetricLabel"] { color: #475569 !important; font-size: 13px !important; font-weight: 700 !important; }
[data-testid="stMetricDelta"] { font-size: 13px !important; }

.stDownloadButton > button {
    background: #059669 !important;
    color: #ffffff !important; border: none !important;
    border-radius: 8px !important; font-weight: 700 !important;
    font-size: 14px !important; padding: 10px 24px !important;
    box-shadow: 0 2px 6px rgba(5, 150, 105, 0.2) !important;
    transition: all 0.2s !important;
}
.stDownloadButton > button:hover { background: #047857 !important; }

.section-header {
    background: #f1f5f9;
    border-right: 4px solid #1e293b;
    padding: 10px 16px;
    border-radius: 6px;
    color: #0f172a;
    font-size: 17px;
    font-weight: 800;
    margin: 20px 0 12px 0;
    border: 1px solid #e2e8f0;
}
.badge-portfolio {
    display: inline-block;
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    color: #1e293b;
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 13px;
    font-weight: 700;
    margin: 3px;
}
hr { border-color: #e2e8f0 !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  Header
# ══════════════════════════════════════════════════════
st.markdown("""
<div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 14px; padding: 24px; text-align: center; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
    <div style="font-size:42px; margin-bottom: 6px;">📈</div>
    <h1 style="color:#0f172a; font-weight:900; margin:0 0 6px 0; font-size:28px;">
        التقرير اليومي — فولو اب
    </h1>
    <p style="color:#475569; font-size:15px; margin:0; font-weight:600;">
        ربط المحفظة المجمعة + المحفظة الموزعة + شيت السدادات — تحليل المحافظ وأشهر الإسناد
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ══════════════════════════════════════════════════════
#  رفع الملفات الثلاثة
# ══════════════════════════════════════════════════════
st.markdown('<div class="section-header">📂 رفع ملفات البيانات الثلاثة المطلوبة</div>', unsafe_allow_html=True)

col_u1, col_u2, col_u3 = st.columns(3)

with col_u1:
    st.markdown("**1️⃣ المحفظة المجمعة (الرئيسية)**")
    master_file = st.file_uploader(
        "رفع المحفظة المجمعة",
        type=["xlsx", "xls"],
        key="master_upload",
        help="الملف الأصلي المجمع الذي يحتوي على ربط كل رقم مديونية بالمحفظة واسم المشرف وتاريخ الإسناد وفصل الخدمة"
    )

with col_u2:
    st.markdown("**2️⃣ المحفظة الموزعة**")
    dist_file = st.file_uploader(
        "رفع المحفظة الموزعة",
        type=["xlsx", "xls"],
        key="dist_upload",
        help="الملف الموزع على المحصلين والمشرفين والذي يحتوي على مبالغ المديونيات وتواريخ فصل الخدمة"
    )

with col_u3:
    st.markdown("**3️⃣ شيت السدادات**")
    pay_file = st.file_uploader(
        "رفع شيت السدادات",
        type=["xlsx", "xls"],
        key="pay_upload",
        help="شيت السدادات اليومية أو الشهرية لمطابقة المبالغ المحصلة"
    )

if not master_file or not dist_file or not pay_file:
    st.info("💡 يرجى رفع الملفات الثلاثة أعلاه لبدء التحليل الفوري وتوليد التقرير المنسق.")
    st.stop()

# ── قراءة الملفات مع تحسين للملفات الكبيرة ──────────────────────────────────
@st.cache_data(show_spinner="⏳ جاري قراءة الملفات وتحميل البيانات، قد يستغرق الأمر لحظة للملفات الكبيرة...")
def read_excel_file(file_bytes, file_name=""):
    """
    Reads Excel files efficiently. For large files (> 20MB) it avoids dtype=str
    on all columns (which is slow) and instead converts only after loading.
    """
    buf = io.BytesIO(file_bytes)
    file_size_mb = len(file_bytes) / (1024 * 1024)
    
    try:
        if file_size_mb > 20:
            # للملفات الكبيرة: قراءة بدون dtype محدد ثم تحويل
            df = pd.read_excel(buf, engine='openpyxl')
            # تحويل كل الأعمدة لـ string للتوافق مع باقي الكود
            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].replace('nan', pd.NA)
        else:
            df = pd.read_excel(buf, dtype=str)
    except Exception:
        # fallback للملفات بصيغة xls القديمة
        buf.seek(0)
        try:
            df = pd.read_excel(buf, engine='xlrd')
            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].replace('nan', pd.NA)
        except Exception as e2:
            st.error(f"❌ فشل في قراءة الملف {file_name}: {e2}")
            st.stop()
    
    return df

file_size_master = len(master_file.getvalue()) / (1024 * 1024)
file_size_dist   = len(dist_file.getvalue()) / (1024 * 1024)
file_size_pay    = len(pay_file.getvalue()) / (1024 * 1024)

if max(file_size_master, file_size_dist, file_size_pay) > 50:
    st.info(f"📦 تم اكتشاف ملفات كبيرة الحجم — المجمعة: {file_size_master:.1f} MB | الموزعة: {file_size_dist:.1f} MB | السدادات: {file_size_pay:.1f} MB\n\nقد تستغرق المعالجة دقيقة أو أكثر، يرجى الانتظار...")

df_master = read_excel_file(master_file.getvalue(), master_file.name)
df_dist   = read_excel_file(dist_file.getvalue(),   dist_file.name)
df_pay    = read_excel_file(pay_file.getvalue(),     pay_file.name)

# ══════════════════════════════════════════════════════
#  اكتشاف الأعمدة الأساسية تلقائياً
# ══════════════════════════════════════════════════════
def detect_col(df, candidates):
    cols_lower = {c.strip().lower(): c for c in df.columns}
    for c in candidates:
        if c.strip().lower() in cols_lower:
            return cols_lower[c.strip().lower()]
    # partial match
    for c in candidates:
        for col in df.columns:
            if c.strip() in col:
                return col
    return None

# المحفظة المجمعة
MASTER_DEBT_ID     = detect_col(df_master, ["رقم المديونية","رقم المديوني","debt_id"])
MASTER_CID         = detect_col(df_master, ["رقم الهوية","رقم هوية","الهوية","customer_id"])
MASTER_DEBT_AMT    = detect_col(df_master, ["مبلغ المديونية","مبلغ الميدونيه","مبلغ الميدونية","debt_amount"])
MASTER_PORTFOLIO   = detect_col(df_master, ["المحفظة","المحافظ","محفظه","portfolio"])
MASTER_ASSIGN_DATE = detect_col(df_master, ["تاريخ الاسناد","تاريخ الإسناد","تاريخ التوزيع","assignment_date"])
MASTER_SUP         = detect_col(df_master, ["المشرف","اسم المشرف","supervisor"])
MASTER_COL         = detect_col(df_master, ["المحصل","اسم المحصل","collector"])

# المحفظة الموزعة
DIST_DEBT_ID     = detect_col(df_dist, ["رقم المديونية","رقم المديوني","debt_id"])
DIST_CID         = detect_col(df_dist, ["رقم الهوية","رقم هوية","الهوية","customer_id"])
DIST_DEBT_AMT    = detect_col(df_dist, ["مبلغ المديونية","مبلغ الميدونيه","مبلغ الميدونية","debt_amount"])
DIST_PORTFOLIO   = detect_col(df_dist, ["المحفظة","المحافظ","محفظه","portfolio"])
DIST_ASSIGN_DATE = detect_col(df_dist, ["تاريخ الاسناد","تاريخ الإسناد","تاريخ التوزيع","assignment_date"])
DIST_SUP         = detect_col(df_dist, ["المشرف","اسم المشرف","supervisor"])
DIST_COL         = detect_col(df_dist, ["المحصل","اسم المحصل","collector"])

# السدادات
PAY_DEBT_ID     = detect_col(df_pay, ["رقم المديونية","رقم المديوني","debt_id"])
PAY_CID         = detect_col(df_pay, ["رقم الهوية","رقم هوية","الهوية","customer_id"])
PAY_AMOUNT      = detect_col(df_pay, ["مبلغ السداد","مبلغ الدفع","payment_amount","المبلغ"])
PAY_DATE        = detect_col(df_pay, ["تاريخ السداد","تاريخ الدفع","payment_date","التاريخ"])
PAY_ASSIGN_DATE = detect_col(df_pay, ["تاريخ الاسناد","تاريخ الإسناد","تاريخ التوزيع","assignment_date"])
PAY_SUP         = detect_col(df_pay, ["المشرف","اسم المشرف","supervisor"])
PAY_COL         = detect_col(df_pay, ["اسم المحصل","المحصل","collector"])

# ── عرض الأعمدة المكتشفة ──
with st.expander("🔍 الأعمدة المكتشفة تلقائياً (انقر للتحقق أو التعديل)", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**📋 المحفظة المجمعة:**")
        MASTER_DEBT_ID     = st.selectbox("رقم المديونية", df_master.columns.tolist(), index=df_master.columns.tolist().index(MASTER_DEBT_ID) if MASTER_DEBT_ID else 0, key="m_debt_id")
        MASTER_CID         = st.selectbox("رقم الهوية",    df_master.columns.tolist(), index=df_master.columns.tolist().index(MASTER_CID) if MASTER_CID else 0,     key="m_cid")
        MASTER_PORTFOLIO   = st.selectbox("المحفظة",       df_master.columns.tolist(), index=df_master.columns.tolist().index(MASTER_PORTFOLIO) if MASTER_PORTFOLIO else 0, key="m_port")
        MASTER_ASSIGN_DATE = st.selectbox("تاريخ الإسناد", df_master.columns.tolist(), index=df_master.columns.tolist().index(MASTER_ASSIGN_DATE) if MASTER_ASSIGN_DATE else 0, key="m_assign_dt")
    with c2:
        st.markdown("**📊 المحفظة الموزعة:**")
        DIST_DEBT_ID     = st.selectbox("رقم المديونية",  df_dist.columns.tolist(), index=df_dist.columns.tolist().index(DIST_DEBT_ID) if DIST_DEBT_ID else 0,  key="d_debt_id")
        DIST_CID         = st.selectbox("رقم الهوية",     df_dist.columns.tolist(), index=df_dist.columns.tolist().index(DIST_CID) if DIST_CID else 0,       key="d_cid")
        DIST_PORTFOLIO   = st.selectbox("المحفظة",        df_dist.columns.tolist(), index=df_dist.columns.tolist().index(DIST_PORTFOLIO) if DIST_PORTFOLIO else 0,  key="d_port")
        DIST_ASSIGN_DATE = st.selectbox("تاريخ الإسناد",  df_dist.columns.tolist(), index=df_dist.columns.tolist().index(DIST_ASSIGN_DATE) if DIST_ASSIGN_DATE else 0,  key="d_assign_dt")
        DIST_DEBT_AMT    = st.selectbox("مبلغ المديونية", df_dist.columns.tolist(), index=df_dist.columns.tolist().index(DIST_DEBT_AMT) if DIST_DEBT_AMT else 0,  key="d_debt_amt")
        DIST_SUP         = st.selectbox("المشرف",         df_dist.columns.tolist(), index=df_dist.columns.tolist().index(DIST_SUP) if DIST_SUP else 0,        key="d_sup")
        DIST_COL         = st.selectbox("المحصل",         df_dist.columns.tolist(), index=df_dist.columns.tolist().index(DIST_COL) if DIST_COL else 0,        key="d_col")
    with c3:
        st.markdown("**💳 السدادات:**")
        PAY_DEBT_ID     = st.selectbox("رقم المديونية",  df_pay.columns.tolist(), index=df_pay.columns.tolist().index(PAY_DEBT_ID) if PAY_DEBT_ID else 0,  key="p_debt_id")
        PAY_AMOUNT      = st.selectbox("مبلغ السداد",    df_pay.columns.tolist(), index=df_pay.columns.tolist().index(PAY_AMOUNT) if PAY_AMOUNT else 0,   key="p_amount")
        PAY_DATE        = st.selectbox("تاريخ السداد",   df_pay.columns.tolist(), index=df_pay.columns.tolist().index(PAY_DATE) if PAY_DATE else 0,     key="p_date")
        PAY_ASSIGN_DATE = st.selectbox("تاريخ الإسناد",  df_pay.columns.tolist(), index=df_pay.columns.tolist().index(PAY_ASSIGN_DATE) if PAY_ASSIGN_DATE else 0, key="p_assign_dt")
        PAY_SUP         = st.selectbox("المشرف",         df_pay.columns.tolist(), index=df_pay.columns.tolist().index(PAY_SUP) if PAY_SUP else 0,      key="p_sup")
        PAY_COL         = st.selectbox("اسم المحصل",     df_pay.columns.tolist(), index=df_pay.columns.tolist().index(PAY_COL) if PAY_COL else 0,      key="p_col")

st.markdown("---")

# ══════════════════════════════════════════════════════
#  دوال مساعدة لتنظيف الأرقام والمعرفات وتواريخ الفصل والإسناد
# ══════════════════════════════════════════════════════
def to_clean_num(series):
    if series is None:
        return pd.Series(dtype=float)
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors='coerce').fillna(0.0)
    return pd.to_numeric(
        series.astype(str).str.replace(',', '', regex=False).str.replace(' ', '', regex=False).str.replace('﷼', '', regex=False),
        errors='coerce'
    ).fillna(0.0)

def clean_id(val):
    if pd.isna(val):
        return ''
    s = str(val).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s

def extract_assignment_month_series(series):
    """يستخرج رقم الشهر من عمود تاريخ الإسناد بصيغة 'شهر 1', 'شهر 2', ..."""
    if series is None or series.empty:
        return pd.Series(dtype=str)
    parsed = pd.to_datetime(series, errors='coerce', dayfirst=False)
    if parsed.isna().mean() > 0.4:
        parsed = pd.to_datetime(series, errors='coerce', dayfirst=True)
    months = parsed.dt.month
    return months.apply(lambda m: f"شهر {int(m)}" if pd.notna(m) and m > 0 else "غير محدد")

def month_sort_key(m_str):
    try:
        if 'شهر' in str(m_str):
            return int(str(m_str).replace('شهر', '').strip())
        return 999
    except:
        return 999

# ══════════════════════════════════════════════════════
#  معالجة البيانات والربط الشامل
# ══════════════════════════════════════════════════════
with st.spinner("🔄 جاري ربط الملفات الثلاثة وتجهيز المحافظ وأشهر الإسناد..."):

    # ── 1. تنظيف السدادات ──
    df_pay_clean = df_pay.copy()
    df_pay_clean[PAY_AMOUNT] = to_clean_num(df_pay_clean[PAY_AMOUNT])
    if PAY_DATE:
        df_pay_clean['_pay_date'] = pd.to_datetime(df_pay_clean[PAY_DATE], errors='coerce', dayfirst=False)
        bad = df_pay_clean['_pay_date'].isna()
        if bad.sum() > len(df_pay_clean) * 0.3:
            df_pay_clean['_pay_date'] = pd.to_datetime(df_pay_clean[PAY_DATE], errors='coerce', dayfirst=True)
    else:
        df_pay_clean['_pay_date'] = pd.NaT

    # ── 2. استخراج شهر الإسناد في المجمعة والموزعة ──
    if MASTER_ASSIGN_DATE and MASTER_ASSIGN_DATE in df_master.columns:
        df_master['_assign_month'] = extract_assignment_month_series(df_master[MASTER_ASSIGN_DATE])
    else:
        df_master['_assign_month'] = 'غير محدد'

    if DIST_ASSIGN_DATE and DIST_ASSIGN_DATE in df_dist.columns:
        df_dist['_assign_month'] = extract_assignment_month_series(df_dist[DIST_ASSIGN_DATE])
    else:
        df_dist['_assign_month'] = 'غير محدد'



    # ── 3. ربط السدادات بالمحفظة وشهر الإسناد عبر رقم المديونية ثم رقم الهوية ──
    debt_to_portfolio = {}
    debt_to_month     = {}
    cid_to_portfolio  = {}
    cid_to_month      = {}

    if MASTER_DEBT_ID and MASTER_DEBT_ID in df_master.columns:
        for _, row in df_master.iterrows():
            k_debt = clean_id(row[MASTER_DEBT_ID])
            k_cid  = clean_id(row[MASTER_CID]) if MASTER_CID and MASTER_CID in df_master.columns else ''
            
            if MASTER_PORTFOLIO and MASTER_PORTFOLIO in df_master.columns:
                v_port = str(row[MASTER_PORTFOLIO]).strip()
                if pd.notna(v_port) and v_port not in ('', 'nan', 'None'):
                    if k_debt: debt_to_portfolio[k_debt] = v_port
                    if k_cid and k_cid not in cid_to_portfolio: cid_to_portfolio[k_cid] = v_port
            
            v_m = str(row.get('_assign_month', '')).strip()
            if v_m and v_m != 'غير محدد':
                if k_debt: debt_to_month[k_debt] = v_m
                if k_cid and k_cid not in cid_to_month: cid_to_month[k_cid] = v_m
            


    if DIST_DEBT_ID and DIST_DEBT_ID in df_dist.columns:
        for _, row in df_dist.iterrows():
            k_debt = clean_id(row[DIST_DEBT_ID])
            k_cid  = clean_id(row[DIST_CID]) if DIST_CID and DIST_CID in df_dist.columns else ''
            
            if DIST_PORTFOLIO and DIST_PORTFOLIO in df_dist.columns:
                v_port = str(row[DIST_PORTFOLIO]).strip()
                if pd.notna(v_port) and v_port not in ('', 'nan', 'None'):
                    if k_debt and k_debt not in debt_to_portfolio: debt_to_portfolio[k_debt] = v_port
                    if k_cid and k_cid not in cid_to_portfolio: cid_to_portfolio[k_cid] = v_port
            
            v_m = str(row.get('_assign_month', '')).strip()
            if v_m and v_m != 'غير محدد':
                if k_debt and k_debt not in debt_to_month: debt_to_month[k_debt] = v_m
                if k_cid and k_cid not in cid_to_month: cid_to_month[k_cid] = v_m
            


    # ربط السدادات الأساسي برقم المديونية مع fallback برقم الهوية
    df_pay_clean['_portfolio']    = df_pay_clean[PAY_DEBT_ID].apply(clean_id).map(debt_to_portfolio)
    if PAY_CID and PAY_CID in df_pay_clean.columns:
        df_pay_clean['_portfolio'] = df_pay_clean['_portfolio'].fillna(df_pay_clean[PAY_CID].apply(clean_id).map(cid_to_portfolio))
    df_pay_clean['_portfolio']    = df_pay_clean['_portfolio'].fillna('غير محدد')

    df_pay_clean['_assign_month'] = df_pay_clean[PAY_DEBT_ID].apply(clean_id).map(debt_to_month)
    if PAY_CID and PAY_CID in df_pay_clean.columns:
        df_pay_clean['_assign_month'] = df_pay_clean['_assign_month'].fillna(df_pay_clean[PAY_CID].apply(clean_id).map(cid_to_month))
    if PAY_ASSIGN_DATE and PAY_ASSIGN_DATE in df_pay_clean.columns:
        df_pay_clean['_assign_month'] = df_pay_clean['_assign_month'].fillna(extract_assignment_month_series(df_pay_clean[PAY_ASSIGN_DATE]))
    df_pay_clean['_assign_month'] = df_pay_clean['_assign_month'].fillna('غير محدد')



    # ── 4. تنظيف المحفظة الموزعة وملء المحفظة وبالربط بالمديونية ثم الهوية ──
    df_dist_clean = df_dist.copy()
    if DIST_DEBT_AMT:
        df_dist_clean[DIST_DEBT_AMT] = to_clean_num(df_dist_clean[DIST_DEBT_AMT])
    if DIST_CID:
        df_dist_clean[DIST_CID] = df_dist_clean[DIST_CID].apply(clean_id)
    if DIST_DEBT_ID:
        df_dist_clean[DIST_DEBT_ID] = df_dist_clean[DIST_DEBT_ID].apply(clean_id)

    if DIST_PORTFOLIO and DIST_PORTFOLIO in df_dist_clean.columns:
        # كشف الصفوف التي ليس لها محفظة (فارغة أو nan)
        is_missing_port = (
            df_dist_clean[DIST_PORTFOLIO].isna() |
            df_dist_clean[DIST_PORTFOLIO].astype(str).str.strip().str.lower().isin(['', 'nan', 'none', 'null', 'غير محدد'])
        )
        if is_missing_port.any():
            # 1. الربط برقم المديونية من المجمعة
            if DIST_DEBT_ID:
                fill_debt = df_dist_clean.loc[is_missing_port, DIST_DEBT_ID].map(debt_to_portfolio)
                df_dist_clean.loc[is_missing_port, DIST_PORTFOLIO] = fill_debt

            # 2. الربط برقم الهوية (لأن العميل له مديونيات أخرى بمحفظة معروفة)
            still_missing = (
                df_dist_clean[DIST_PORTFOLIO].isna() |
                df_dist_clean[DIST_PORTFOLIO].astype(str).str.strip().str.lower().isin(['', 'nan', 'none', 'null', 'غير محدد'])
            )
            if still_missing.any() and DIST_CID:
                fill_cid = df_dist_clean.loc[still_missing, DIST_CID].map(cid_to_portfolio)
                df_dist_clean.loc[still_missing, DIST_PORTFOLIO] = fill_cid

            # إن تبقت أي قيمة غير معروفة تحول لـ 'غير محدد' بدلاً من nan
            df_dist_clean[DIST_PORTFOLIO] = df_dist_clean[DIST_PORTFOLIO].replace(['nan', 'None', 'NaN', '', None], np.nan).fillna('غير محدد')

        df_dist_clean[DIST_PORTFOLIO] = df_dist_clean[DIST_PORTFOLIO].astype(str).str.strip()



    # ── 5. قائمة المحافظ الموجودة في المحفظة الموزعة ──
    raw_ports = df_dist_clean[DIST_PORTFOLIO].dropna().unique().tolist() if DIST_PORTFOLIO else []
    portfolios_in_dist = sorted([str(p).strip() for p in raw_ports if str(p).strip() and str(p).strip().lower() not in ('nan', 'none', '')])

    # ── 6. تاريخ اليوم ──
    today = pd.Timestamp.today().normalize()
    yesterday = today - timedelta(days=1)

# ══════════════════════════════════════════════════════
#  خيار السياسة: حسب المحافظ أم حسب شهر الإسناد
# ══════════════════════════════════════════════════════
st.markdown('<div class="section-header">⚙️ سياسة وتصنيف التقرير الأساسي</div>', unsafe_allow_html=True)

group_mode = st.radio(
    "📊 اختر أساس تقسيم وتجميع التقرير:",
    [
        "📂 حسب المحافظ (الافتراضي)",
        "📅 حسب شهر تاريخ الإسناد (شهر 1، شهر 2، ...)",
    ],
    horizontal=True,
    key="group_mode_radio"
)

is_month_mode   = (group_mode == "📅 حسب شهر تاريخ الإسناد (شهر 1، شهر 2، ...)")

if is_month_mode:
    GROUP_LABEL = "شهر الإسناد"
else:
    GROUP_LABEL = "المحفظة"

# ══════════════════════════════════════════════════════
#  سلايسر التصفية (المحافظ / أشهر الإسناد / سنوات الفصل والمشرفين)
# ══════════════════════════════════════════════════════
st.markdown(f'<div class="section-header">🎛️ سلايسر — تصفية حسب {GROUP_LABEL} والمشرفين</div>', unsafe_allow_html=True)

if is_month_mode:
    DIST_ACTIVE_COL = '_assign_month'
    PAY_ACTIVE_COL  = '_assign_month'
    unique_months = sorted(list(set(df_dist_clean['_assign_month'].dropna().unique().tolist() + df_pay_clean['_assign_month'].dropna().unique().tolist())), key=month_sort_key)
    all_group_options = [m for m in unique_months if m and m != 'غير محدد']
    if 'غير محدد' in unique_months:
        all_group_options.append('غير محدد')
    slicer_box_label = "📅 اختر شهر/أشهر الإسناد (اتركه فارغاً للكل):"
    badge_icon = "📅 "
else:
    DIST_ACTIVE_COL = DIST_PORTFOLIO if DIST_PORTFOLIO and DIST_PORTFOLIO in df_dist_clean.columns else '_portfolio'
    PAY_ACTIVE_COL  = '_portfolio'
    all_group_options = portfolios_in_dist if portfolios_in_dist else sorted(df_pay_clean['_portfolio'].unique().tolist())
    slicer_box_label = "📂 اختر المحفظة/المحافظ (اتركه فارغاً للكل):"
    badge_icon = "📂 "

# قائمة المشرفين في كلا الملفين
dist_sups = df_dist_clean[DIST_SUP].dropna().unique().tolist() if DIST_SUP and DIST_SUP in df_dist_clean.columns else []
pay_sups  = df_pay_clean[PAY_SUP].dropna().unique().tolist() if PAY_SUP and PAY_SUP in df_pay_clean.columns else []
all_sups  = sorted(list(set([str(s).strip() for s in (dist_sups + pay_sups) if str(s).strip() and str(s).strip() not in ['nan', 'None']])))

col_sl1, col_sl2, col_date = st.columns([2, 2, 1])
with col_sl1:
    selected_groups = st.multiselect(
        slicer_box_label,
        options=all_group_options,
        default=[],
        key="main_group_slicer"
    )
with col_sl2:
    selected_sups = st.multiselect(
        "👥 اختر المشرف/المشرفين (اتركه فارغاً للكل):",
        options=all_sups,
        default=[],
        key="sup_slicer"
    )
with col_date:
    report_date = st.date_input("📅 تاريخ التقرير:", value=date.today(), key="report_date")
    today = pd.Timestamp(report_date)
    yesterday = today - timedelta(days=1)

# تطبيق الفلاتر
df_pay_filtered  = df_pay_clean.copy()
df_dist_filtered = df_dist_clean.copy()

if selected_groups:
    df_pay_filtered = df_pay_filtered[df_pay_filtered[PAY_ACTIVE_COL].isin(selected_groups)]
    if DIST_ACTIVE_COL in df_dist_filtered.columns:
        df_dist_filtered = df_dist_filtered[df_dist_filtered[DIST_ACTIVE_COL].isin(selected_groups)]

if selected_sups:
    if PAY_SUP and PAY_SUP in df_pay_filtered.columns:
        df_pay_filtered = df_pay_filtered[df_pay_filtered[PAY_SUP].astype(str).str.strip().isin(selected_sups)]
    if DIST_SUP and DIST_SUP in df_dist_filtered.columns:
        df_dist_filtered = df_dist_filtered[df_dist_filtered[DIST_SUP].astype(str).str.strip().isin(selected_sups)]

# عرض الـ badges
groups_to_show = selected_groups if selected_groups else all_group_options[:10]
sups_to_show   = selected_sups if selected_sups else all_sups[:10]
g_badges = " ".join([f'<span class="badge-portfolio">{badge_icon}{g}</span>' for g in groups_to_show])
s_badges = " ".join([f'<span class="badge-portfolio" style="border-color:#38bdf8; color:#38bdf8;">👥 {s}</span>' for s in sups_to_show])
st.markdown(f'<div style="margin:8px 0;">{g_badges} {s_badges}</div>', unsafe_allow_html=True)

st.markdown("---")

# ══════════════════════════════════════════════════════
#  حساب وحالات التوصل وعدم التوصل (لا يرد ومغلق)
# ══════════════════════════════════════════════════════
try:
    from core.daily_followup_engine import classify_contact_status_series
except Exception:
    try:
        from STC_System.core.daily_followup_engine import classify_contact_status_series
    except Exception:
        import sys as _sys, os as _os
        _root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", ".."))
        if _root not in _sys.path:
            _sys.path.insert(0, _root)
        from core.daily_followup_engine import classify_contact_status_series

main_status_col = detect_col(df_dist_filtered, ["الحالة الرئيسية", "الحالة المتبعة", "main_status"])
sub_status_col  = detect_col(df_dist_filtered, ["الحالة الفرعية", "sub_status"])
note_status_col = detect_col(df_dist_filtered, ["المتابعة", "الملاحظات", "الملاحظة", "ملاحظة", "followup"])

df_dist_filtered['حالة_التوصل'] = classify_contact_status_series(
    df_dist_filtered, main_col=main_status_col, sub_col=sub_status_col, note_col=note_status_col
)

# تعيين أولويات حالات التوصل عند تكرار العميل (تم التوصل > لا يرد ومغلق > عدم توصل)
prio_map = {'تم التوصل': 1, 'لا يرد ومغلق': 2, 'عدم توصل - أخرى': 3, 'عدم توصل': 3}
inv_map  = {1: 'تم التوصل', 2: 'لا يرد ومغلق', 3: 'عدم توصل'}

if DIST_CID and DIST_CID in df_dist_filtered.columns:
    df_dist_filtered['_prio'] = df_dist_filtered['حالة_التوصل'].map(prio_map).fillna(3)
    cust_overall = df_dist_filtered.groupby(DIST_CID)['_prio'].min()
    cnt_contacted     = int((cust_overall == 1).sum())
    cnt_no_ans_closed = int((cust_overall == 2).sum())
    cnt_other         = int((cust_overall == 3).sum())
    cnt_total         = len(cust_overall)
else:
    cnt_contacted     = int((df_dist_filtered['حالة_التوصل'] == 'تم التوصل').sum())
    cnt_no_ans_closed = int((df_dist_filtered['حالة_التوصل'] == 'لا يرد ومغلق').sum())
    cnt_other         = int((df_dist_filtered['حالة_التوصل'].isin(['عدم توصل - أخرى', 'عدم توصل'])).sum())
    cnt_total         = len(df_dist_filtered)

cnt_rate          = round(cnt_contacted / cnt_total * 100, 1) if cnt_total > 0 else 0.0
cnt_no_ans_pct    = round(cnt_no_ans_closed / cnt_total * 100, 1) if cnt_total > 0 else 0.0
cnt_other_pct     = round(cnt_other / cnt_total * 100, 1) if cnt_total > 0 else 0.0

# جدول تحليل التوصل حسب التصنيف النشط (المحفظة / شهر الإسناد / سنة الفصل)
if DIST_ACTIVE_COL and DIST_ACTIVE_COL in df_dist_filtered.columns:
    if DIST_CID and DIST_CID in df_dist_filtered.columns:
        cust_status_df = df_dist_filtered.groupby([DIST_ACTIVE_COL, DIST_CID])['_prio'].min().reset_index()
        cust_status_df['حالة_العميل'] = cust_status_df['_prio'].map(inv_map)
        contact_by_grp = cust_status_df.groupby([DIST_ACTIVE_COL, 'حالة_العميل']).size().unstack(fill_value=0).reset_index()
    else:
        contact_by_grp = df_dist_filtered.groupby([DIST_ACTIVE_COL, 'حالة_التوصل']).size().unstack(fill_value=0).reset_index()

    contact_by_grp.columns.name = None

    for req_col in ['تم التوصل', 'لا يرد ومغلق', 'عدم توصل']:
        if req_col not in contact_by_grp.columns:
            if req_col == 'عدم توصل' and 'عدم توصل - أخرى' in contact_by_grp.columns:
                contact_by_grp['عدم توصل'] = contact_by_grp['عدم توصل - أخرى']
            else:
                contact_by_grp[req_col] = 0

    contact_by_grp.rename(columns={DIST_ACTIVE_COL: GROUP_LABEL}, inplace=True)
    contact_by_grp['إجمالي العملاء'] = contact_by_grp['تم التوصل'] + contact_by_grp['لا يرد ومغلق'] + contact_by_grp['عدم توصل']

    contact_by_grp['نسبة تم التوصل %'] = contact_by_grp.apply(
        lambda r: round(r['تم التوصل'] / r['إجمالي العملاء'] * 100, 1) if r['إجمالي العملاء'] > 0 else 0.0, axis=1
    )
    contact_by_grp['نسبة لا يرد ومغلق %'] = contact_by_grp.apply(
        lambda r: round(r['لا يرد ومغلق'] / r['إجمالي العملاء'] * 100, 1) if r['إجمالي العملاء'] > 0 else 0.0, axis=1
    )
    contact_by_grp['نسبة عدم التوصل %'] = contact_by_grp.apply(
        lambda r: round(r['عدم توصل'] / r['إجمالي العملاء'] * 100, 1) if r['إجمالي العملاء'] > 0 else 0.0, axis=1
    )

    contact_cols_order = [
        GROUP_LABEL, 'إجمالي العملاء',
        'تم التوصل', 'نسبة تم التوصل %',
        'لا يرد ومغلق', 'نسبة لا يرد ومغلق %',
        'عدم توصل', 'نسبة عدم التوصل %'
    ]
    contact_by_grp = contact_by_grp[[c for c in contact_cols_order if c in contact_by_grp.columns]]

    if is_month_mode:
        contact_by_grp['sort_k'] = contact_by_grp[GROUP_LABEL].apply(month_sort_key)
        contact_by_grp = contact_by_grp.sort_values('sort_k').drop(columns=['sort_k']).reset_index(drop=True)

    else:
        contact_by_grp = contact_by_grp.sort_values('تم التوصل', ascending=False).reset_index(drop=True)

    _c_tot_contacted = int(contact_by_grp['تم التوصل'].sum())
    _c_tot_noans     = int(contact_by_grp['لا يرد ومغلق'].sum())
    _c_tot_nocont    = int(contact_by_grp['عدم توصل'].sum())
    _c_tot_all       = _c_tot_contacted + _c_tot_noans + _c_tot_nocont
    cnt_tot_row = {
        GROUP_LABEL:           '📊 الإجمالي',
        'إجمالي العملاء':     int(_c_tot_all),
        'تم التوصل':          int(_c_tot_contacted),
        'نسبة تم التوصل %':   round(_c_tot_contacted / _c_tot_all * 100, 1) if _c_tot_all > 0 else 0.0,
        'لا يرد ومغلق':       int(_c_tot_noans),
        'نسبة لا يرد ومغلق %': round(_c_tot_noans / _c_tot_all * 100, 1) if _c_tot_all > 0 else 0.0,
        'عدم توصل':          int(_c_tot_nocont),
        'نسبة عدم التوصل %':  round(_c_tot_nocont / _c_tot_all * 100, 1) if _c_tot_all > 0 else 0.0,
    }
    contact_table_display = pd.concat([contact_by_grp, pd.DataFrame([cnt_tot_row])], ignore_index=True)
else:
    contact_table_display = pd.DataFrame()

# ══════════════════════════════════════════════════════
#  حساب ملخص الأداء الرئيسي ونسب التوصل (المحافظ / أشهر الإسناد)
# ══════════════════════════════════════════════════════
if DIST_ACTIVE_COL and DIST_DEBT_AMT and DIST_ACTIVE_COL in df_dist_filtered.columns:
    # 1. إجمالي المديونية من صفوف المديونيات
    debt_by_grp = df_dist_filtered.groupby(DIST_ACTIVE_COL)[DIST_DEBT_AMT].sum().reset_index()
    debt_by_grp.columns = [GROUP_LABEL, 'إجمالي المديونية']

    # 2. حالات وتوزيع العملاء على مستوى الهويات الفريدة
    if DIST_CID and DIST_CID in df_dist_filtered.columns:
        cust_status_df = df_dist_filtered.groupby([DIST_ACTIVE_COL, DIST_CID])['_prio'].min().reset_index()
        cust_status_df['حالة_العميل'] = cust_status_df['_prio'].map(inv_map)
        cust_summary = cust_status_df.groupby([DIST_ACTIVE_COL, 'حالة_العميل']).size().unstack(fill_value=0).reset_index()
    else:
        cust_summary = df_dist_filtered.groupby([DIST_ACTIVE_COL, 'حالة_التوصل']).size().unstack(fill_value=0).reset_index()

    cust_summary.columns.name = None
    for req_col in ['تم التوصل', 'لا يرد ومغلق', 'عدم توصل']:
        if req_col not in cust_summary.columns:
            if req_col == 'عدم توصل' and 'عدم توصل - أخرى' in cust_summary.columns:
                cust_summary['عدم توصل'] = cust_summary['عدم توصل - أخرى']
            else:
                cust_summary[req_col] = 0

    cust_summary.rename(columns={DIST_ACTIVE_COL: GROUP_LABEL}, inplace=True)
    cust_summary['عدد العملاء'] = cust_summary['تم التوصل'] + cust_summary['لا يرد ومغلق'] + cust_summary['عدم توصل']

    # حساب النسب الثلاث المستقلة المتكاملة (مجموعها 100.0% دائماً)
    _tot_cust = cust_summary['عدد العملاء'].replace(0, float('nan'))
    cust_summary['نسبة تم التوصل %']   = (cust_summary['تم التوصل'] / _tot_cust * 100).round(1).fillna(0.0)
    cust_summary['نسبة لا يرد ومغلق %'] = (cust_summary['لا يرد ومغلق'] / _tot_cust * 100).round(1).fillna(0.0)
    cust_summary['نسبة عدم التوصل %']  = (cust_summary['عدم توصل'] / _tot_cust * 100).round(1).fillna(0.0)

    dist_summary = debt_by_grp.merge(cust_summary, on=GROUP_LABEL, how='outer').fillna(0)
else:
    dist_summary = pd.DataFrame(columns=[
        GROUP_LABEL, 'عدد العملاء', 'إجمالي المديونية',
        'تم التوصل', 'نسبة تم التوصل %',
        'لا يرد ومغلق', 'نسبة لا يرد ومغلق %',
        'عدم توصل', 'نسبة عدم التوصل %'
    ])

pay_by_grp = df_pay_filtered.groupby(PAY_ACTIVE_COL).agg(
    اجمالي_التحصيل=(PAY_AMOUNT, 'sum')
).reset_index()
pay_by_grp.columns = [GROUP_LABEL, 'إجمالي التحصيل']

if PAY_DATE and '_pay_date' in df_pay_filtered.columns:
    today_pay = df_pay_filtered[df_pay_filtered['_pay_date'].dt.normalize() == today].groupby(PAY_ACTIVE_COL)[PAY_AMOUNT].sum().reset_index()
    today_pay.columns = [GROUP_LABEL, 'التحصيل اليومي (اليوم)']
    yest_pay = df_pay_filtered[df_pay_filtered['_pay_date'].dt.normalize() == yesterday].groupby(PAY_ACTIVE_COL)[PAY_AMOUNT].sum().reset_index()
    yest_pay.columns = [GROUP_LABEL, 'التحصيل اليومي (أمس)']
else:
    today_pay = pd.DataFrame(columns=[GROUP_LABEL, 'التحصيل اليومي (اليوم)'])
    yest_pay  = pd.DataFrame(columns=[GROUP_LABEL, 'التحصيل اليومي (أمس)'])

port_table = dist_summary.merge(pay_by_grp, on=GROUP_LABEL, how='outer')
port_table = port_table.merge(today_pay, on=GROUP_LABEL, how='left')
port_table = port_table.merge(yest_pay,  on=GROUP_LABEL, how='left')
port_table = port_table.fillna(0)

# تنظيف أي قيمة nan أو فارغة في عمود التصنيف
port_table[GROUP_LABEL] = port_table[GROUP_LABEL].astype(str).str.strip().replace(['nan', 'None', 'NaN', '', 'null'], 'غير محدد')
if (port_table[GROUP_LABEL] == 'غير محدد').any():
    # إذا تكرر 'غير محدد' نتيجة الدمج نقوم بتجميعه
    num_cols = [c for c in port_table.columns if c != GROUP_LABEL]
    port_table = port_table.groupby(GROUP_LABEL, as_index=False)[num_cols].sum()

port_table['نسبة التحصيل %'] = port_table.apply(
    lambda r: round(r['إجمالي التحصيل'] / r['إجمالي المديونية'] * 100, 1) if r.get('إجمالي المديونية', 0) > 0 else 0.0, axis=1
)

cols_order = [
    GROUP_LABEL, 'عدد العملاء', 'إجمالي المديونية', 'إجمالي التحصيل', 'نسبة التحصيل %',
    'تم التوصل', 'نسبة تم التوصل %',
    'لا يرد ومغلق', 'نسبة لا يرد ومغلق %',
    'عدم توصل', 'نسبة عدم التوصل %',
    'التحصيل اليومي (اليوم)', 'التحصيل اليومي (أمس)'
]
cols_order = [c for c in cols_order if c in port_table.columns]

if is_month_mode:
    port_table['sort_k'] = port_table[GROUP_LABEL].apply(month_sort_key)
    port_table = port_table.sort_values('sort_k').drop(columns=['sort_k']).reset_index(drop=True)

else:
    port_table = port_table[cols_order].sort_values('إجمالي التحصيل', ascending=False).reset_index(drop=True)

total_row = {}
tot_cust_all   = port_table['عدد العملاء'].sum() if 'عدد العملاء' in port_table.columns else 0
tot_debt_all   = port_table['إجمالي المديونية'].sum() if 'إجمالي المديونية' in port_table.columns else 0
tot_coll_all   = port_table['إجمالي التحصيل'].sum() if 'إجمالي التحصيل' in port_table.columns else 0
tot_cnt_all    = port_table['تم التوصل'].sum() if 'تم التوصل' in port_table.columns else 0
tot_noans_all  = port_table['لا يرد ومغلق'].sum() if 'لا يرد ومغلق' in port_table.columns else 0
tot_nocont_all = port_table['عدم توصل'].sum() if 'عدم توصل' in port_table.columns else 0

for col in cols_order:
    if col == GROUP_LABEL:
        total_row[col] = '📊 الإجمالي'
    elif col == 'نسبة التحصيل %':
        total_row[col] = round(tot_coll_all / tot_debt_all * 100, 1) if tot_debt_all > 0 else 0.0
    elif col in ('نسبة تم التوصل %', 'نسبة التوصل %'):
        total_row[col] = round(tot_cnt_all / tot_cust_all * 100, 1) if tot_cust_all > 0 else 0.0
    elif col == 'نسبة لا يرد ومغلق %':
        total_row[col] = round(tot_noans_all / tot_cust_all * 100, 1) if tot_cust_all > 0 else 0.0
    elif col == 'نسبة عدم التوصل %':
        total_row[col] = round(tot_nocont_all / tot_cust_all * 100, 1) if tot_cust_all > 0 else 0.0
    else:
        total_row[col] = port_table[col].sum() if pd.api.types.is_numeric_dtype(port_table[col]) else ''

port_table_display = pd.concat([port_table, pd.DataFrame([total_row])], ignore_index=True)

vintage_table_display = pd.DataFrame()

# ── Top Download Button ──
try:
    from core.daily_excel_writer import generate_styled_daily_excel
except Exception:
    try:
        from STC_System.core.daily_excel_writer import generate_styled_daily_excel
    except Exception:
        import sys as _sys, os as _os
        _root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", ".."))
        if _root not in _sys.path:
            _sys.path.insert(0, _root)
        from core.daily_excel_writer import generate_styled_daily_excel

# Preparing DataFrames for Supervisors & Collectors
sup_col = PAY_SUP or DIST_SUP
if sup_col and sup_col in df_pay_filtered.columns:
    sup_df = df_pay_filtered.groupby(sup_col)[PAY_AMOUNT].sum().reset_index()
    sup_df.columns = ['المشرف', 'إجمالي التحصيل']
    sup_df = sup_df.sort_values('إجمالي التحصيل', ascending=False).reset_index(drop=True)
    sup_df.index = sup_df.index + 1
    sup_df['الترتيب'] = sup_df.index
    sup_tot = sup_df['إجمالي التحصيل'].sum()
    sup_df['المعدل %'] = (sup_df['إجمالي التحصيل'] / sup_tot * 100) if sup_tot > 0 else 0
    sup_df['#'] = sup_df['الترتيب'].apply(lambda i: {1: '🥇', 2: '🥈', 3: '🥉'}.get(i, f'#{i}'))
else:
    sup_df = pd.DataFrame()

col_col = PAY_COL or DIST_COL
if col_col and col_col in df_pay_filtered.columns:
    col_df = df_pay_filtered.groupby(col_col)[PAY_AMOUNT].sum().reset_index()
    col_df.columns = ['المحصل', 'إجمالي التحصيل']
    col_df = col_df.sort_values('إجمالي التحصيل', ascending=False).reset_index(drop=True)
    col_df.index = col_df.index + 1
    col_df['الترتيب'] = col_df.index
    col_tot = col_df['إجمالي التحصيل'].sum()
    col_df['المعدل %'] = (col_df['إجمالي التحصيل'] / col_tot * 100) if col_tot > 0 else 0
    col_df['#'] = col_df['الترتيب'].apply(lambda i: {1: '🥇', 2: '🥈', 3: '🥉', 4: '🏅', 5: '🏅'}.get(i, f'#{i}'))
else:
    col_df = pd.DataFrame()

# Build Excel Bytes
try:
    excel_report_bytes = generate_styled_daily_excel(
        port_table_display, sup_df, col_df, df_pay_filtered, report_date,
        contact_table=contact_table_display
    )
except Exception:
    output_buf = io.BytesIO()
    with pd.ExcelWriter(output_buf, engine='xlsxwriter') as wr:
        port_table_display.to_excel(wr, sheet_name=f'ملخص_{GROUP_LABEL}', index=False)
        if not sup_df.empty:
            sup_df.to_excel(wr, sheet_name='أفضل المشرفين', index=False)
        if not col_df.empty:
            col_df.to_excel(wr, sheet_name='أفضل المحصلين', index=False)
        if contact_table_display is not None and not contact_table_display.empty:
            contact_table_display.to_excel(wr, sheet_name='حالات التوصل', index=False)
        df_pay_filtered.to_excel(wr, sheet_name='السدادات التفصيلية', index=False)
    excel_report_bytes = output_buf.getvalue()

st.markdown('<div class="section-header">📥 تحميل التقرير الشامل والشارتس (علوي)</div>', unsafe_allow_html=True)
c_dl_top1, c_dl_top2 = st.columns(2)

with c_dl_top1:
    st.download_button(
        label=f"📥 تحميل التقرير المنسق كاملاً (Excel بثيم كحلي غامق والشارتس مقسم حسب {GROUP_LABEL})",
        data=excel_report_bytes,
        file_name=f"التقرير_اليومي_فولو_اب_{GROUP_LABEL}_{report_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
        key="dl_top_excel_styled"
    )
with c_dl_top2:
    csv_data = port_table_display.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label=f"📊 تحميل ملخص {GROUP_LABEL} (CSV)",
        data=csv_data.encode('utf-8-sig'),
        file_name=f"ملخص_{GROUP_LABEL}_{report_date}.csv",
        mime="text/csv",
        use_container_width=True,
        key="dl_top_csv"
    )

# ══════════════════════════════════════════════════════
#  حساب KPIs الرئيسية
# ══════════════════════════════════════════════════════
total_collection = df_pay_filtered[PAY_AMOUNT].sum() if PAY_AMOUNT and PAY_AMOUNT in df_pay_filtered.columns else 0.0
today_collection = df_pay_filtered[df_pay_filtered['_pay_date'].dt.normalize() == today][PAY_AMOUNT].sum() if PAY_DATE and '_pay_date' in df_pay_filtered.columns else 0.0
yesterday_collection = df_pay_filtered[df_pay_filtered['_pay_date'].dt.normalize() == yesterday][PAY_AMOUNT].sum() if PAY_DATE and '_pay_date' in df_pay_filtered.columns else 0.0
total_debt = df_dist_filtered[DIST_DEBT_AMT].sum() if DIST_DEBT_AMT and DIST_DEBT_AMT in df_dist_filtered.columns else 0.0
total_customers = df_dist_filtered[DIST_CID].nunique() if DIST_CID and DIST_CID in df_dist_filtered.columns else len(df_dist_filtered)
collection_rate = (total_collection / total_debt * 100) if total_debt > 0 else 0.0
daily_delta = today_collection - yesterday_collection

st.markdown('<div class="section-header">📊 مؤشرات الأداء الرئيسية (KPIs)</div>', unsafe_allow_html=True)

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("👥 إجمالي العملاء",      f"{total_customers:,}")
k2.metric("💰 إجمالي المديونية",    f"{total_debt:,.0f} ﷼")
k3.metric("💵 إجمالي التحصيل",     f"{total_collection:,.0f} ﷼")
k4.metric("📅 تحصيل اليوم",        f"{today_collection:,.0f} ﷼", delta=f"{daily_delta:+,.0f} ﷼ عن أمس")
k5.metric("📈 نسبة التحصيل",       f"{collection_rate:.1f}%")
k6.metric("💳 عدد عمليات السداد",  f"{len(df_pay_filtered):,}")

st.markdown("---")

# ── Section: Contact Status KPIs & Summary ──
st.markdown('<div class="section-header">📞 مؤشرات وحالات التوصل وعدم التوصل (لا يرد ومغلق)</div>', unsafe_allow_html=True)

ck1, ck2, ck3 = st.columns(3)
ck1.metric("📞 تم التوصل", f"{cnt_contacted:,}", delta=f"{cnt_rate:.1f}% من إجمالي العملاء")
ck2.metric("📵 لا يرد ومغلق", f"{cnt_no_ans_closed:,}", delta=f"{cnt_no_ans_pct:.1f}% من إجمالي العملاء")
ck3.metric("🚫 عدم توصل", f"{cnt_other:,}", delta=f"{cnt_other_pct:.1f}% من إجمالي العملاء")

if not contact_table_display.empty:
    st.markdown(f"##### 📋 جدول تحليل حالات التوصل وعدم التوصل حسب {GROUP_LABEL}:")
    _contact_fmt = {c: '{:,.0f}' for c in contact_table_display.columns if c != GROUP_LABEL and '%' not in c}
    _contact_fmt.update({c: '{:.1f}%' for c in contact_table_display.columns if '%' in c})
    st.dataframe(
        contact_table_display.style.format(_contact_fmt, na_rep='0'),
        use_container_width=True, hide_index=True
    )

st.markdown("---")

# ══════════════════════════════════════════════════════
#  الجدول الأول: ملخص الأداء (المحافظ أو أشهر الإسناد)
# ══════════════════════════════════════════════════════
st.markdown(f'<div class="section-header">📋 الجدول الأول: ملخص الأداء حسب {GROUP_LABEL}</div>', unsafe_allow_html=True)

def format_summary_table(df):
    fmt = {}
    for c in df.columns:
        if 'مديونية' in c or 'تحصيل' in c:
            fmt[c] = '{:,.0f}'
        elif '%' in c:
            fmt[c] = '{:.1f}%'
        elif 'عملاء' in c:
            fmt[c] = '{:,.0f}'
    return df.style.format(fmt, na_rep='0')

st.dataframe(format_summary_table(port_table_display), use_container_width=True, hide_index=True, height=min(400, (len(port_table_display)+1)*38+40))

st.markdown("---")



# ══════════════════════════════════════════════════════
#  الشارتس البيانية
# ══════════════════════════════════════════════════════
st.markdown('<div class="section-header">📊 شارتس التحليل البياني</div>', unsafe_allow_html=True)

CHART_LAYOUT = dict(
    plot_bgcolor  = '#ffffff',
    paper_bgcolor = '#ffffff',
    font_color    = '#0f172a',
    title_font    = dict(color='#0f172a', size=14, family='Cairo'),
    showlegend    = False,
    height        = 380,
    margin        = dict(t=50, b=30, l=20, r=20),
)
BLUE_SCALE = ['#cbd5e1', '#94a3b8', '#475569', '#1e293b']
PIE_COLORS = ['#1e293b', '#334155', '#475569', '#64748b', '#94a3b8', '#cbd5e1']

try:
    import plotly.express as px
    import plotly.graph_objects as go

    chart_df = port_table[port_table[GROUP_LABEL] != '📊 الإجمالي'].copy()

    ch1, ch2 = st.columns(2)
    with ch1:
        if 'إجمالي التحصيل' in chart_df.columns and not chart_df.empty:
            fig1 = px.bar(
                chart_df.sort_values('إجمالي التحصيل', ascending=True),
                x='إجمالي التحصيل', y=GROUP_LABEL, orientation='h',
                title=f'💰 إجمالي التحصيل حسب {GROUP_LABEL}',
                color='إجمالي التحصيل',
                color_continuous_scale=BLUE_SCALE,
                text='إجمالي التحصيل'
            )
            fig1.update_traces(
                texttemplate='%{text:,.0f}',
                textposition='outside',
                textfont=dict(color='#0f172a', size=11, family='Cairo')
            )
            fig1.update_layout(**CHART_LAYOUT)
            fig1.update_coloraxes(showscale=False)
            st.plotly_chart(fig1, use_container_width=True)

    with ch2:
        if 'نسبة التحصيل %' in chart_df.columns and not chart_df.empty:
            fig2 = px.bar(
                chart_df.sort_values('نسبة التحصيل %', ascending=False),
                x=GROUP_LABEL, y='نسبة التحصيل %',
                title=f'📈 نسبة التحصيل % حسب {GROUP_LABEL}',
                color='نسبة التحصيل %',
                color_continuous_scale=['#cbd5e1', '#64748b', '#1e293b', '#059669'],
                text='نسبة التحصيل %'
            )
            fig2.update_traces(
                texttemplate='%{text:.1f}%',
                textposition='outside',
                textfont=dict(color='#0f172a', size=11, family='Cairo')
            )
            fig2.update_layout(**CHART_LAYOUT)
            fig2.update_coloraxes(showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

    # شارت توزيع العملاء + مديونية vs تحصيل
    ch3, ch4 = st.columns(2)
    with ch3:
        if 'عدد العملاء' in chart_df.columns and chart_df['عدد العملاء'].sum() > 0:
            fig3 = px.pie(
                chart_df[chart_df['عدد العملاء'] > 0],
                names=GROUP_LABEL, values='عدد العملاء',
                title=f'👥 توزيع العملاء حسب {GROUP_LABEL}',
                hole=0.45,
                color_discrete_sequence=PIE_COLORS
            )
            fig3.update_traces(
                textfont=dict(color='#0f172a', size=11, family='Cairo'),
                pull=[0.03] * len(chart_df)
            )
            fig3.update_layout(**{**CHART_LAYOUT, 'showlegend': True,
                                  'legend': dict(font=dict(color='#0f172a', size=11))})
            st.plotly_chart(fig3, use_container_width=True)

    with ch4:
        if 'إجمالي المديونية' in chart_df.columns and 'إجمالي التحصيل' in chart_df.columns:
            fig4 = go.Figure()
            fig4.add_trace(go.Bar(
                name='المديونية', x=chart_df[GROUP_LABEL], y=chart_df['إجمالي المديونية'],
                marker_color='#475569'
            ))
            fig4.add_trace(go.Bar(
                name='التحصيل', x=chart_df[GROUP_LABEL], y=chart_df['إجمالي التحصيل'],
                marker_color='#1e293b'
            ))
            fig4.update_layout(
                **{**CHART_LAYOUT,
                   'barmode': 'group',
                   'title': f'⚖️ المديونية مقابل التحصيل حسب {GROUP_LABEL}',
                   'showlegend': True,
                   'legend': dict(font=dict(color='#0f172a', size=11)),
                   'title_font': dict(color='#0f172a', size=14, family='Cairo')}
            )
            st.plotly_chart(fig4, use_container_width=True)


except ImportError:
    st.warning("⚠️ مكتبة plotly غير مثبتة — سيتم عرض البيانات بدون شارتس بصرية.")

st.markdown("---")

# ══════════════════════════════════════════════════════
#  الجدول الثاني: أفضل المشرفين والمحصلين
# ══════════════════════════════════════════════════════
st.markdown('<div class="section-header">🏆 الجدول الثاني: ترتيب أفضل المشرفين وأفضل 5 محصلين</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["👤 أفضل المشرفين", "⭐ أفضل 5 محصلين (Top 5 Collectors)"])

with tab1:
    if not sup_df.empty:
        sup_df_show = sup_df[['#', 'المشرف', 'إجمالي التحصيل', 'المعدل %']]
        try:
            st.dataframe(
                sup_df_show.style.format({'إجمالي التحصيل': '{:,.0f} ﷼', 'المعدل %': '{:.1f}%'})
                                 .background_gradient(subset=['إجمالي التحصيل'], cmap='Blues'),
                use_container_width=True, hide_index=True
            )
        except Exception:
            st.dataframe(
                sup_df_show.style.format({'إجمالي التحصيل': '{:,.0f} ﷼', 'المعدل %': '{:.1f}%'}),
                use_container_width=True, hide_index=True
            )

        try:
            fig_sup = px.bar(
                sup_df.head(10).sort_values('إجمالي التحصيل'),
                x='إجمالي التحصيل', y='المشرف', orientation='h',
                title='🏅 أفضل المشرفين في التحصيل',
                color='إجمالي التحصيل',
                color_continuous_scale=['#cbd5e1', '#64748b', '#1e293b'],
                text='إجمالي التحصيل'
            )
            fig_sup.update_traces(texttemplate='%{text:,.0f}', textposition='outside', textfont=dict(color='#0f172a', size=11, family='Cairo'))
            fig_sup.update_layout(
                plot_bgcolor='#ffffff', paper_bgcolor='#ffffff',
                font_color='#0f172a', title_font_color='#0f172a',
                showlegend=False, height=min(450, len(sup_df.head(10))*45+80)
            )
            st.plotly_chart(fig_sup, use_container_width=True)
        except:
            pass
    else:
        st.info("⚠️ لم يتم اكتشاف عمود المشرف في السدادات.")

with tab2:
    if not col_df.empty:
        st.markdown("### ⭐ قائمة أفضل 5 محصلين أداءً في التحصيل (Top 5 Collectors):")
        top5_cols_show = col_df[['#', 'المحصل', 'إجمالي التحصيل', 'المعدل %']].head(5)

        try:
            st.dataframe(
                top5_cols_show.style.format({'إجمالي التحصيل': '{:,.0f} ﷼', 'المعدل %': '{:.1f}%'})
                                    .background_gradient(subset=['إجمالي التحصيل'], cmap='Blues'),
                use_container_width=True, hide_index=True
            )
        except Exception:
            st.dataframe(
                top5_cols_show.style.format({'إجمالي التحصيل': '{:,.0f} ﷼', 'المعدل %': '{:.1f}%'}),
                use_container_width=True, hide_index=True
            )

        try:
            fig_col = px.bar(
                col_df.head(5).sort_values('إجمالي التحصيل'),
                x='إجمالي التحصيل', y='المحصل', orientation='h',
                title='⭐ ترتيب أفضل 5 محصلين (Top 5 Collectors)',
                color='إجمالي التحصيل',
                color_continuous_scale=['#cbd5e1', '#64748b', '#1e293b'],
                text='إجمالي التحصيل'
            )
            fig_col.update_traces(texttemplate='%{text:,.0f}', textposition='outside', textfont=dict(color='#0f172a', size=11, family='Cairo'))
            fig_col.update_layout(
                plot_bgcolor='#ffffff', paper_bgcolor='#ffffff',
                font_color='#0f172a', title_font_color='#0f172a',
                showlegend=False, height=320
            )
            st.plotly_chart(fig_col, use_container_width=True)
        except:
            pass
    else:
        st.info("⚠️ لم يتم اكتشاف عمود المحصل في السدادات.")

st.markdown("---")

# ══════════════════════════════════════════════════════
#  تصدير التقرير السفلي
# ══════════════════════════════════════════════════════
st.markdown('<div class="section-header">📥 تصدير التقرير الكامل والشارتس (سفلي)</div>', unsafe_allow_html=True)

c_dl1, c_dl2 = st.columns(2)
with c_dl1:
    st.download_button(
        label=f"📥 تحميل التقرير المنسق كاملاً (Excel بثيم كحلي غامق والشارتس مقسم حسب {GROUP_LABEL})",
        data=excel_report_bytes,
        file_name=f"التقرير_اليومي_فولو_اب_{GROUP_LABEL}_{report_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
        key="dl_bottom_excel_styled"
    )
with c_dl2:
    st.download_button(
        label=f"📊 تحميل ملخص {GROUP_LABEL} (CSV)",
        data=csv_data.encode('utf-8-sig'),
        file_name=f"ملخص_{GROUP_LABEL}_{report_date}.csv",
        mime="text/csv",
        use_container_width=True,
        key="dl_bottom_csv"
    )

st.markdown(f"""
<div style="text-align:center; margin-top:30px; color:#64748b; font-size:12px; font-weight:600;">
    📈 التقرير اليومي — فولو اب | تصنيف: {GROUP_LABEL} | تاريخ التقرير: {report_date} | شركة مهاره للتحصيل
</div>
""", unsafe_allow_html=True)
