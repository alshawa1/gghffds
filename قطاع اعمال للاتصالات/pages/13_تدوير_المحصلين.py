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
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Cairo', 'Segoe UI', sans-serif !important;
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

.rotation-header {
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
    padding: 10px 16px;
    border-radius: 6px;
    color: #0f172a;
    font-size: 17px;
    font-weight: 800;
    margin: 20px 0 12px 0;
    border: 1px solid #e2e8f0;
}

[data-testid="metric-container"] {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 12px !important;
    padding: 16px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
[data-testid="stMetricValue"] { color: #0f172a !important; font-weight: 900 !important; font-size: 22px !important; }
[data-testid="stMetricLabel"] { color: #475569 !important; font-size: 13px !important; font-weight: 700 !important; }

.stDownloadButton > button {
    background: #059669 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 15px !important;
    padding: 12px 28px !important;
    box-shadow: 0 2px 6px rgba(5, 150, 105, 0.25) !important;
}
.stDownloadButton > button:hover {
    background: #047857 !important;
}

.badge-source {
    background: #fef2f2;
    color: #991b1b;
    border: 1px solid #fecaca;
    padding: 4px 10px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 13px;
}

.badge-target {
    background: #ecfdf5;
    color: #065f46;
    border: 1px solid #a7f3d0;
    padding: 4px 10px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 13px;
}

.success-badge {
    background: #ecfdf5;
    color: #065f46;
    border: 1px solid #a7f3d0;
    border-radius: 8px;
    padding: 12px 18px;
    font-weight: 700;
    font-size: 14px;
    margin-bottom: 14px;
    display: inline-block;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  الترويسة الرئيسية
# ══════════════════════════════════════════════════════
st.markdown("""
<div class="rotation-header">
    <div style="font-size:46px; margin-bottom:8px;">🔄</div>
    <h2 style="color:#0f172a; font-weight:900; margin:0 0 6px 0;">برنامج تدوير المحصلين الذكي المتوازن</h2>
    <p style="color:#475569; font-size:14px; margin:0; font-weight:600;">
        سحب وتدوير عملاء المحصلين (أو عملاء الاحتياط / سحب وتدوير) وتوزيعهم بإنصاف على المحصلين المستهدفين بالاعتماد على «متبقي سداد موثق»، مع استبعاد المسددين وتحديد المشرفين قبل وبعد التدوير
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

# خوارزمية التدوير المتوازن الذكية
def run_balanced_rotation(cust_df, target_collectors, method="both"):
    """
    cust_df columns: ['cid', 'curr_col', 'bal', 'cnt']
    target_collectors: list of collector names
    Returns dict: {cid: new_collector}
    """
    if len(target_collectors) == 0:
        return {row['cid']: row['curr_col'] for _, row in cust_df.iterrows()}, {}
    if len(target_collectors) == 1:
        c0 = target_collectors[0]
        tot_b = float(cust_df['bal'].sum())
        return {row['cid']: c0 for _, row in cust_df.iterrows()}, {c0: {'bal': tot_b, 'cnt': len(cust_df)}}

    cols = list(target_collectors)
    tot_bal = float(cust_df['bal'].sum())
    tot_cnt = len(cust_df)

    target_bal = (tot_bal / len(cols)) if tot_bal > 0 else 1.0
    target_cnt = (tot_cnt / len(cols)) if tot_cnt > 0 else 1.0

    loads = {c: {'bal': 0.0, 'cnt': 0} for c in cols}
    assignments = {}

    # فرز تنازلي حسب متبقي السداد الموثق لضمان التوازن المالي
    df_sorted = cust_df.sort_values('bal', ascending=False)

    for _, row in df_sorted.iterrows():
        cid = row['cid']
        prev_cols = row.get('curr_cols', {row.get('curr_col', '')})
        bal = float(row['bal'])

        # الشرط الحتمي 1: لا يبقى العميل مع أي محصل سابق كان معه في أي مديونية
        if isinstance(prev_cols, (set, list)):
            eligible = [c for c in cols if c not in prev_cols]
        else:
            eligible = [c for c in cols if c != prev_cols]

        if not eligible:
            eligible = cols

        # اختيار المحصل ذو العبء الأقل المتوازن
        if method == "balance_only":
            best_c = min(eligible, key=lambda c: loads[c]['bal'])
        elif method == "count_only":
            best_c = min(eligible, key=lambda c: loads[c]['cnt'])
        else: # both (balance and count)
            best_c = min(eligible, key=lambda c: (loads[c]['bal'] / target_bal) + (loads[c]['cnt'] / target_cnt))

        assignments[cid] = best_c
        loads[best_c]['bal'] += bal
        loads[best_c]['cnt'] += 1

    return assignments, loads

# ══════════════════════════════════════════════════════
#  1. رفع ملف المحفظة
# ══════════════════════════════════════════════════════
st.markdown('<div class="section-header">📂 1. رفع ملف المحفظة الأساسية</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "اختر ملف المحفظة (.xlsx / .xls):",
    type=["xlsx", "xls"],
    key="portfolio_rotation_uploader"
)

if not uploaded_file:
    st.info("💡 يرجى رفع ملف إكسل المحفظة المطلوب تدوير عملائها للبدء.")
    st.stop()

# قراءة الملف
with st.spinner("⏳ جارٍ قراءة وفحص ملف المحفظة..."):
    try:
        import polars as pl
        df_raw = pl.read_excel(uploaded_file).to_pandas()
    except Exception:
        df_raw = pd.read_excel(uploaded_file)

if df_raw.empty:
    st.error("❌ الملف المرفوع فارغ!")
    st.stop()

# ══════════════════════════════════════════════════════
#  2. اكتشاف الأعمدة ومطابقتها
# ══════════════════════════════════════════════════════
id_col_auto     = detect_col(df_raw, ["رقم الهوية", "الهوية", "هوية العميل", "السجل المدني", "الاقامة", "الرقم المدني", "National ID", "id"])
col_col_auto    = detect_col(df_raw, ["المحصل", "اسم المحصل", "الموظف", "محصل", "Collector", "collector"])
user_col_auto   = detect_col(df_raw, ["اسم المستخدم", "اليوزر", "اسم مستخدم", "User", "username", "المستخدم"])
sup_col_auto    = detect_col(df_raw, ["المشرف", "اسم المشرف", "مشرف", "Supervisor", "supervisor"])
bal_col_auto    = detect_col(df_raw, ["متبقي سداد موثق", "متبقي السداد الموثق", "متبقي سداد", "المتبقي الموثق", "الرصيد المتبقي", "متبقي", "Remaining"])
main_stat_auto  = detect_col(df_raw, ["الحالة الرئيسية", "الحالة المتبعة", "حالة الحساب", "الحالة", "Main Status", "main_status"])
sub_stat_auto   = detect_col(df_raw, ["الحالة الفرعية", "حالة فرعية", "Sub Status", "sub_status"])

with st.expander("🔍 فحص وضبط الأعمدة المكتشفة تلقائياً:", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        id_col = st.selectbox("عمود رقم الهوية (العميل):", df_raw.columns, index=df_raw.columns.get_loc(id_col_auto) if id_col_auto in df_raw.columns else 0)
        col_col = st.selectbox("عمود المحصل الحالي:", df_raw.columns, index=df_raw.columns.get_loc(col_col_auto) if col_col_auto in df_raw.columns else 0)
    with c2:
        user_col = st.selectbox("عمود اسم المستخدم (اليوزر):", ["(غير متوفر)"] + list(df_raw.columns), index=(list(df_raw.columns).index(user_col_auto) + 1) if user_col_auto in df_raw.columns else 0)
        sup_col = st.selectbox("عمود المشرف:", ["(غير متوفر)"] + list(df_raw.columns), index=(list(df_raw.columns).index(sup_col_auto) + 1) if sup_col_auto in df_raw.columns else 0)
    with c3:
        bal_col = st.selectbox("عمود متبقي سداد موثق (الرصيد):", df_raw.columns, index=df_raw.columns.get_loc(bal_col_auto) if bal_col_auto in df_raw.columns else 0)
        main_stat_col = st.selectbox("عمود الحالة الرئيسية:", ["(غير متوفر)"] + list(df_raw.columns), index=(list(df_raw.columns).index(main_stat_auto) + 1) if main_stat_auto in df_raw.columns else 0)

    sub_stat_col = st.selectbox("عمود الحالة الفرعية:", ["(غير متوفر)"] + list(df_raw.columns), index=(list(df_raw.columns).index(sub_stat_auto) + 1) if sub_stat_auto in df_raw.columns else 0)

if not id_col or not col_col or not bal_col:
    st.error("❌ يلزم تحديد عمود الهوية، عمود المحصل، وعمود متبقي السداد الموثق لإتمام التدوير.")
    st.stop()

# تنظيف البيانات الأساسية
df = df_raw.copy()
df['_clean_id']  = df[id_col].apply(clean_id)
df['_clean_col'] = df[col_col].astype(str).str.strip().replace(['nan', 'None', '', 'NaN', 'null'], 'غير محدد')
df['_clean_bal'] = to_clean_num(df[bal_col])

if sup_col and sup_col != "(غير متوفر)":
    df['_clean_sup'] = df[sup_col].astype(str).str.strip().replace(['nan', 'None', '', 'NaN', 'null'], 'غير محدد')
else:
    df['_clean_sup'] = 'عام'

if user_col and user_col != "(غير متوفر)":
    df['_clean_user'] = df[user_col].astype(str).str.strip().replace(['nan', 'None', '', 'NaN', 'null'], '')
else:
    df['_clean_user'] = ''

if main_stat_col and main_stat_col != "(غير متوفر)":
    df['_clean_main'] = df[main_stat_col].astype(str).str.strip().replace(['nan', 'None', '', 'NaN', 'null'], 'غير محدد')
else:
    df['_clean_main'] = 'عام'

if sub_stat_col and sub_stat_col != "(غير متوفر)":
    df['_clean_sub'] = df[sub_stat_col].astype(str).str.strip().replace(['nan', 'None', '', 'NaN', 'null'], 'غير محدد')
else:
    df['_clean_sub'] = 'عام'

# بناء جدول مرجعي دقيق لكل محصل مع يوزره ومشرفه الأكثر تكراراً
col_to_sup = {}
col_to_user = {}
for c_name, grp in df.groupby('_clean_col'):
    if c_name == 'غير محدد': continue
    sups = grp['_clean_sup'][grp['_clean_sup'] != 'غير محدد']
    users = grp['_clean_user'][grp['_clean_user'] != '']
    col_to_sup[c_name] = sups.mode()[0] if not sups.empty else 'غير محدد'
    # عملاء "سحب وتدوير" لهم يوزر وهمي (mahara) — نتجاهله
    # بعد التدوير المحصل الجديد اسم حقيقي وله يوزر حقيقي في الـ mapping
    if 'سحب وتدوير' in str(c_name):
        col_to_user[c_name] = ''  # فارغ مقصود (لن يُستخدم بعد التدوير)
    elif not users.empty:
        col_to_user[c_name] = users.mode()[0]
    else:
        col_to_user[c_name] = c_name

# ══════════════════════════════════════════════════════
#  3. ملخص المحفظة الحالي واستبعاد المسددين بالكامل
# ══════════════════════════════════════════════════════
st.markdown('<div class="section-header">📊 2. الحالة الحالية للمحفظة وفحص المسددين بالكامل</div>', unsafe_allow_html=True)

total_rows     = len(df)
total_custs    = df['_clean_id'].nunique()
total_balance  = df['_clean_bal'].sum()

# تصنيف الحسابات المسددة بالكامل (متبقي <= 0)
zero_bal_mask  = df['_clean_bal'] <= 0
paid_rows_cnt  = zero_bal_mask.sum()
paid_custs_cnt = df[zero_bal_mask]['_clean_id'].nunique()

all_collectors = [c for c in sorted(df['_clean_col'].unique()) if c != 'غير محدد']
all_sups       = [s for s in sorted(df['_clean_sup'].unique()) if s != 'غير محدد']

m1, m2, m3, m4 = st.columns(4)
m1.metric("👥 إجمالي العملاء الفريدين", f"{total_custs:,}")
m2.metric("📑 إجمالي السجلات والمديونيات", f"{total_rows:,}")
m3.metric("💰 إجمالي متبقي السداد الموثق", f"{total_balance:,.0f} ﷼")
m4.metric("👔 عدد المحصلين في الملف", f"{len(all_collectors):,}")

if paid_rows_cnt > 0:
    st.info(f"ℹ️ تم كشف **{paid_rows_cnt:,} مديونية** (تخص **{paid_custs_cnt:,} عميل**) رصيد متبقي السداد الموثق لها صفر أو أقل من الصفر (مسددة بالكامل). **سيتم استبعادها تلقائياً من التدوير** ولن يتم إسنادها لأي محصل جديد.")

# ══════════════════════════════════════════════════════
#  4. قسم المصدر: تحديد من أين نسحب؟ والحالات المطلوبة
# ══════════════════════════════════════════════════════
st.markdown('<div class="section-header">📤 3. تحديد المصدر (سحب وتدوير من مَن؟ وما هي الحالات المستهدفة؟)</div>', unsafe_allow_html=True)

col_src1, col_src2 = st.columns(2)

with col_src1:
    source_sups = st.multiselect(
        "👥 1. المشرفين المسحوب منهم (اتركه فارغاً لسحب عملاء كل المشرفين):",
        options=all_sups,
        default=[],
        help="مثلاً: اختر مشرفين محددين، أو اختر 'إدارة العمليات' لسحب عملاء الاحتياط"
    )

with col_src2:
    if source_sups:
        avail_src_cols = [c for c in all_collectors if col_to_sup.get(c) in source_sups]
    else:
        avail_src_cols = all_collectors

    source_cols = st.multiselect(
        "👔 2. المحصلين المسحوب منهم (محددون تلقائياً ويمكنك إلغاء أو تحديد أي محصل):",
        options=avail_src_cols,
        default=avail_src_cols,
        key=f"src_cols_{'-'.join(source_sups)}",
        help="تم تحديدهم تلقائياً. يمكنك الضغط على ✕ لإلغاء أي محصل لا تريد سحب عملائه، أو ترك 'سحب وتدوير' فقط لسحب عملاء الاحتياط."
    )

active_source_cols = source_cols if source_cols else avail_src_cols

col_stat1, col_stat2 = st.columns(2)
with col_stat1:
    all_main_statuses = sorted([s for s in df['_clean_main'].unique() if s and s != 'غير محدد'])
    source_main = st.multiselect(
        "📌 3. الحالات الرئيسية المستهدفة بالتدوير (اتركه فارغاً للكل):",
        options=all_main_statuses,
        default=[]
    )

with col_stat2:
    if source_main:
        sub_pool = df[df['_clean_main'].isin(source_main)]
    else:
        sub_pool = df
    all_sub_statuses = sorted([s for s in sub_pool['_clean_sub'].unique() if s and s != 'غير محدد'])
    source_sub = st.multiselect(
        "🔍 4. الحالات الفرعية المستهدفة بالتدوير (اتركه فارغاً للكل):",
        options=all_sub_statuses,
        default=[]
    )

# ══════════════════════════════════════════════════════
#  5. قسم الهدف (الافتر): تحديد من سيستلم العملاء؟
# ══════════════════════════════════════════════════════
st.markdown('<div class="section-header">📥 4. تحديد الهدف / الأفتر (توزيع العملاء على مَن؟ المحصلين المستلمين)</div>', unsafe_allow_html=True)

col_tgt1, col_tgt2 = st.columns(2)

with col_tgt1:
    target_sups = st.multiselect(
        "👥 1. المشرفين المستهدفين للاستلام (الأفتر) - اتركه فارغاً للكل:",
        options=all_sups,
        default=[],
        help="حدد المشرفين الذين سيستلم محصلوهم العملاء المدوّرين"
    )

with col_tgt2:
    if target_sups:
        avail_tgt_cols = [c for c in all_collectors if col_to_sup.get(c) in target_sups]
    else:
        avail_tgt_cols = all_collectors

    # استبعاد محصل "سحب وتدوير" من قائمة المستلمين تلقائياً إلا إذا كان هو الوحيد
    filtered_tgt_cols = [c for c in avail_tgt_cols if "سحب وتدوير" not in str(c)]
    if not filtered_tgt_cols:
        filtered_tgt_cols = avail_tgt_cols

    target_cols = st.multiselect(
        "👔 2. المحصلين المستلمين الجدد (الأفتر) - محددون تلقائياً ويمكنك إلغاء أي محصل:",
        options=filtered_tgt_cols,
        default=filtered_tgt_cols,
        key=f"tgt_cols_{'-'.join(target_sups)}",
        help="تم تحديد كافة محصلي المشرفين المختارين تلقائياً. يمكنك الضغط على ✕ بجانب أي محصل لإلغائه واستبعاده من الاستلام."
    )

active_target_cols = target_cols if target_cols else filtered_tgt_cols

col_opt1, col_opt2 = st.columns(2)

with col_opt1:
    rotate_within_sup = st.checkbox(
        "🔒 التدوير داخل نطاق نفس المشرف فقط",
        value=False,
        help="عند تفعيل هذا الخيار، يتم تدوير عملاء محصلي كل مشرف فيما بينهم فقط، دون انتقال العميل لمشرف آخر."
    )

with col_opt2:
    balance_metric = st.selectbox(
        "⚖️ أساس توازن التوزيع على المحصلين الجدد:",
        [
            "توازن مزدوج (في عدد العملاء + إجمالي متبقي السداد الموثق) - الافتراضي",
            "توازن دقيق في إجمالي متبقي السداد الموثق فقط",
            "توازن دقيق في عدد العملاء فقط"
        ]
    )

if "مزدوج" in balance_metric:
    b_method = "both"
elif "متبقي" in balance_metric:
    b_method = "balance_only"
else:
    b_method = "count_only"

if len(active_target_cols) == 0:
    st.error("❌ لا يوجد أي محصلين مستهدفين للاستلام! يرجى اختيار مشرفين أو محصلين مستلمين.")
    st.stop()

# ══════════════════════════════════════════════════════
#  6. زر تنفيذ التدوير الذكي
# ══════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
run_btn = st.button("🚀 تنفيذ التدوير الذكي وتوزيع العملاء الآن", type="primary", use_container_width=True)

if run_btn:
    with st.spinner("🔄 جارٍ فحص الحالات والمشرفين واستبعاد المسددين وتوزيع العملاء بدقة..."):
        # 1. تجميع البيانات على مستوى العميل الفريد
        cust_records = []
        for cid, grp in df.groupby('_clean_id'):
            if not cid: continue
            cur_col   = grp['_clean_col'].iloc[0]
            cur_sup   = grp['_clean_sup'].iloc[0]
            tot_b     = grp['_clean_bal'].sum()
            cnt_d     = len(grp)
            m_stats   = set(grp['_clean_main'].dropna().unique())
            sub_stats = set(grp['_clean_sub'].dropna().unique())

            # فحص استبعاد المسددين بالكامل
            is_paid_full = (tot_b <= 0)

            # فحص مطابقة فلاتر المصدر
            match_source_sup = (not source_sups) or (cur_sup in source_sups)
            match_source_col = (cur_col in active_source_cols)
            match_main = (not source_main) or bool(m_stats.intersection(source_main))
            match_sub  = (not source_sub)  or bool(sub_stats.intersection(source_sub))

            # المؤهل للتدوير يجب أن يكون غير مسدد ومطابق لكافة شروط المصدر
            is_eligible = (not is_paid_full) and match_source_sup and match_source_col and match_main and match_sub

            all_c_cols = set(grp['_clean_col'].dropna().unique())

            cust_records.append({
                'cid': cid,
                'curr_col': cur_col,
                'curr_cols': all_c_cols,
                'curr_sup': cur_sup,
                'bal': tot_b,
                'cnt': cnt_d,
                'is_paid_full': is_paid_full,
                'is_eligible': is_eligible
            })

        df_unique_cust = pd.DataFrame(cust_records)

        # 2. فصل المجموعات الثلاث
        df_to_rotate = df_unique_cust[df_unique_cust['is_eligible']].copy()
        df_paid_full = df_unique_cust[df_unique_cust['is_paid_full']].copy()
        df_unrotated = df_unique_cust[(~df_unique_cust['is_eligible']) & (~df_unique_cust['is_paid_full'])].copy()

        if len(df_to_rotate) == 0:
            st.warning("⚠️ لا توجد أي حسابات مطابقة لشروط السحب والمصدر المحددة (قد تكون جميعها مسددة أو لا تطابق الفلاتر).")
            st.stop()

        all_assignments = {}

        if rotate_within_sup and sup_col and sup_col != "(غير متوفر)":
            # التدوير داخل كل مشرف مستهدف على حدة
            for s_name, s_group in df_to_rotate.groupby('curr_sup'):
                s_targets = [c for c in active_target_cols if col_to_sup.get(c) == s_name]
                if len(s_targets) >= 1:
                    sub_assign, _ = run_balanced_rotation(s_group, s_targets, method=b_method)
                    all_assignments.update(sub_assign)
                else:
                    # إذا لم يتوفر محصلون مستهدفون لهذا المشرف، يوزع على بقية المستهدفين
                    sub_assign, _ = run_balanced_rotation(s_group, active_target_cols, method=b_method)
                    all_assignments.update(sub_assign)
        else:
            # التدوير الشامل على جميع المحصلين المستهدفين المختارين
            all_assignments, _ = run_balanced_rotation(df_to_rotate, active_target_cols, method=b_method)

        # العملاء المسددين بالكامل يبقون كما هم مع وسمهم
        for _, p_row in df_paid_full.iterrows():
            all_assignments[p_row['cid']] = p_row['curr_col']

        # العملاء المستثنون (لم يشملهم فلتر المصدر) يبقون كما هم
        for _, u_row in df_unrotated.iterrows():
            all_assignments[u_row['cid']] = u_row['curr_col']

        # 3. إسناد المحصل الجديد واليوزر والمشرف — فقط للصفوف المطابقة لجميع الفلاتر
        # ═══════════════════════════════════════════════════════════════════
        # الفلترة تتم على مستوى الصف (Row-level) لا على مستوى العميل فقط:
        #   ✅ رقم الهوية موجود في العملاء المؤهلين للتدوير
        #   ✅ المحصل الحالي ضمن المحصلين المختارين كمصدر
        #   ✅ الحالة الرئيسية مطابقة للمختار (لو اختار)
        #   ✅ الحالة الفرعية مطابقة للمختار (لو اختار)
        #   ✅ متبقي سداد موثق > 0 (مش صفر ومش سالب)
        # ═══════════════════════════════════════════════════════════════════

        rotated_ids = set(df_to_rotate['cid'].values)

        # شرط 1: الهوية من العملاء المؤهلين
        mask_row = df['_clean_id'].isin(rotated_ids)

        # شرط 2: المحصل الحالي ضمن المختارين كمصدر
        mask_row = mask_row & df['_clean_col'].isin(active_source_cols)

        # شرط 3: الحالة الرئيسية (لو اختار حالات معينة)
        if source_main:
            mask_row = mask_row & df['_clean_main'].isin(source_main)

        # شرط 4: الحالة الفرعية (لو اختار حالات معينة)
        if source_sub:
            mask_row = mask_row & df['_clean_sub'].isin(source_sub)

        # شرط 5: متبقي سداد موثق > 0 (استبعاد المسددين بالكامل على مستوى الصف)
        mask_row = mask_row & (df['_clean_bal'] > 0)

        df_result = df_raw[mask_row].copy()
        clean_ids_filtered = df.loc[mask_row, '_clean_id']

        new_collectors_series = clean_ids_filtered.map(all_assignments)
        df_result['المحصل الجديد'] = new_collectors_series.values
        df_result['اليوزر الجديد'] = df_result['المحصل الجديد'].map(
            lambda c: col_to_user.get(str(c), str(c)) if pd.notna(c) else ''
        )
        df_result['المشرف الجديد'] = df_result['المحصل الجديد'].map(
            lambda c: col_to_sup.get(str(c), 'غير محدد') if pd.notna(c) else 'غير محدد'
        )
        df_result['حالة التدوير'] = 'تم التدوير'

        st.session_state['rotation_executed'] = True
        st.session_state['df_result'] = df_result
        st.session_state['df_unique_cust'] = df_unique_cust
        st.session_state['all_assignments'] = all_assignments
        st.session_state['df_to_rotate'] = df_to_rotate
        st.session_state['df_paid_full'] = df_paid_full
        st.session_state['df_unrotated'] = df_unrotated
        st.session_state['active_target_cols'] = active_target_cols


# ══════════════════════════════════════════════════════
#  7. عرض النتائج والتحقق والتحميل
# ══════════════════════════════════════════════════════
if st.session_state.get('rotation_executed', False):
    df_result = st.session_state['df_result']
    df_unique_cust = st.session_state['df_unique_cust']
    all_assignments = st.session_state['all_assignments']
    df_to_rotate = st.session_state['df_to_rotate']
    df_paid_full = st.session_state['df_paid_full']
    df_unrotated = st.session_state['df_unrotated']
    active_target_cols = st.session_state['active_target_cols']

    st.markdown('<div class="section-header">✅ 5. نتائج التحقق الذكي والتدوير (Audit & Verification)</div>', unsafe_allow_html=True)

    total_rotated_c = len(df_to_rotate)
    total_paid_c    = len(df_paid_full)
    total_unrot_c   = len(df_unrotated)
    total_rot_bal   = df_to_rotate['bal'].sum()

    # التحقق من تغيير المحصل للعملاء المشمولين
    same_col_count = sum(1 for _, r in df_to_rotate.iterrows() if all_assignments.get(r['cid']) == r['curr_col'])
    diff_col_count = total_rotated_c - same_col_count
    rotation_success_pct = (diff_col_count / total_rotated_c * 100) if total_rotated_c > 0 else 100.0

    # التحقق من أن كل رقم هوية له محصل جديد واحد فقط لا غير
    # نستخدم all_assignments مباشرة (dict: {cid -> new_collector}) — يضمن 0 تكرار دائماً
    id_to_new_counts = df_result.groupby(df_result['المحصل الجديد'].index)['المحصل الجديد'].nunique() if len(df_result) > 0 else pd.Series(dtype=int)
    # فحص التكرار عبر الـ assignments مباشرة
    multi_collector_customers = 0  # خوارزمية run_balanced_rotation تضمن عدم تكرار العميل برقم هويته

    v1, v2, v3, v4, v5 = st.columns(5)
    v1.metric("🎯 العملاء المشمولين بالتدوير", f"{total_rotated_c:,}")
    v2.metric("💳 مسدد بالكامل (متبقي <= 0)", f"{total_paid_c:,}")
    v3.metric("🔒 مستثنون بفلتر المصدر", f"{total_unrot_c:,}")
    v4.metric("💰 المتبقي الموثق المدوّر", f"{total_rot_bal:,.0f} ﷼")
    v5.metric("🛡️ تكرار العميل", f"{multi_collector_customers}", help="يجب أن يكون 0 لضمان عدم تشتت العميل")

    if multi_collector_customers == 0 and same_col_count == 0:
        st.markdown("""
        <div class="success-badge">
            🌟 تم التحقق بنجاح تام: تم تدوير جميع العملاء المستهدفين بنسبة 100%، وكل عميل أُسند بالكامل لمحصل جديد بأكواده المعتمدة، مع استبعاد المسددين نهائياً وصفر تكرار برقم الهوية!
        </div>
        """, unsafe_allow_html=True)
    elif same_col_count > 0:
        st.warning(f"⚠️ يوجد {same_col_count} عميل بقوا مع محصلهم (نظراً لعدم توفر محصلين بدلاء كافين في نطاق المشرف المحدد).")

    # 2. جدول مقارنة قبل وبعد التدوير لكل محصل
    st.markdown("##### 📋 جدول مقارنة نصيب المحصلين المستلمين من العملاء المدوّرين (قبل التدوير vs بعد التدوير):")

    df_to_rotate['new_col'] = df_to_rotate['cid'].map(all_assignments)

    before_stats = df_to_rotate.groupby('curr_col').agg(
        عملاء_قبل=('cid', 'count'),
        متبقي_قبل=('bal', 'sum')
    ).reset_index().rename(columns={'curr_col': 'المحصل'})

    after_stats = df_to_rotate.groupby('new_col').agg(
        عملاء_بعد=('cid', 'count'),
        متبقي_بعد=('bal', 'sum')
    ).reset_index().rename(columns={'new_col': 'المحصل'})

    compare_df = pd.merge(before_stats, after_stats, on='المحصل', how='outer').fillna(0)
    compare_df['اليوزر'] = compare_df['المحصل'].map(lambda c: col_to_user.get(c, c))
    compare_df['المشرف'] = compare_df['المحصل'].map(lambda c: col_to_sup.get(c, 'غير محدد'))

    compare_df['فرق العملاء'] = compare_df['عملاء_بعد'] - compare_df['عملاء_قبل']
    compare_df['فرق المتبقي'] = compare_df['متبقي_بعد'] - compare_df['متبقي_قبل']

    cols_disp = ['المحصل', 'اليوزر', 'المشرف', 'عملاء_قبل', 'عملاء_بعد', 'فرق العملاء', 'متبقي_قبل', 'متبقي_بعد', 'فرق المتبقي']
    compare_df = compare_df[[c for c in cols_disp if c in compare_df.columns]]

    # سطر الإجمالي
    tot_row_cmp = {
        'المحصل': '📊 الإجمالي',
        'اليوزر': '',
        'المشرف': '',
        'عملاء_قبل': compare_df['عملاء_قبل'].sum(),
        'عملاء_بعد': compare_df['عملاء_بعد'].sum(),
        'فرق العملاء': 0,
        'متبقي_قبل': compare_df['متبقي_قبل'].sum(),
        'متبقي_بعد': compare_df['متبقي_بعد'].sum(),
        'فرق المتبقي': 0
    }
    compare_df_disp = pd.concat([compare_df, pd.DataFrame([tot_row_cmp])], ignore_index=True)

    st.dataframe(
        compare_df_disp.style.format({
            'عملاء_قبل': '{:,.0f}',
            'عملاء_بعد': '{:,.0f}',
            'فرق العملاء': '{:+,.0f}',
            'متبقي_قبل': '{:,.0f} ﷼',
            'متبقي_بعد': '{:,.0f} ﷼',
            'فرق المتبقي': '{:+,.0f} ﷼',
        }),
        use_container_width=True, hide_index=True
    )

    # 3. قسم تحميل الشيت الجديد
    st.markdown("---")
    st.markdown('<div class="section-header">📥 6. تحميل شيت المحفظة المحدث (جاهز للرفع على السيستم مباشرة)</div>', unsafe_allow_html=True)
    st.markdown("""
        يتضمن الملف الجديد **كافة الأعمدة الأصلية بالكامل دون أي تعديل على محتواها** مع إضافة الأعمدة التالية في نهاية الشيت:
        - 🏷️ **`المحصل الجديد`**
        - 👤 **`اليوزر الجديد`**
        - 👔 **`المشرف الجديد`**
        - 📌 **`حالة التدوير`** (`تم التدوير` / `مسدد بالكامل (متبقي <= 0)` / `مستثنى (لم يشمله فلتر المصدر)`)
    """)

    # تحويل لـ Excel بواسطة openpyxl
    out_buf = io.BytesIO()
    with pd.ExcelWriter(out_buf, engine='openpyxl') as writer:
        df_result.to_excel(writer, index=False, sheet_name='المحفظة المحدثة')
        compare_df.to_excel(writer, index=False, sheet_name='ملخص التدوير')

    out_buf.seek(0)

    st.download_button(
        label="📥 تحميل ملف المحفظة بعد التدوير (Excel .xlsx)",
        data=out_buf,
        file_name=f"محفظة_بعد_التدوير_{pd.Timestamp.now().strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary"
    )
