import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="أخطاء النظام", page_icon="⚠️", layout="wide")
st.markdown("<style>body{direction:rtl;text-align:right;}.stApp{direction:rtl;}</style>", unsafe_allow_html=True)

st.title("⚠️ فحص واكتشاف أخطاء النظام (17 قاعدة)")
st.markdown("##### نموذج تقييم أخطاء النظام — مهاره لتحصيل الديون")

from utils.page_upload import page_portfolio_uploader, render_supervisor_filter

df_full, column_map, raw_df = page_portfolio_uploader("page_03_errors", label="📂 ارفع ملف المحفظة لفحص أخطاء النظام (Excel)")

if df_full is None or df_full.empty:
    st.stop()

df = render_supervisor_filter(df_full, column_map, "page_03_errors")

try:
    from business_rules.system_errors import SystemErrorsEngine
    from reports.export import export_errors_report, export_errors, export_portfolio_with_summaries
except ImportError:
    SystemErrorsEngine = None

# ─────────────────────────────────────────────────────────────
# شيت وعود السداد (اختياري)
# ─────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📋 شيت وعود السداد (اختياري)")
st.caption("🔗 سيتم ربطه بالمحفظة عن طريق رقم المديونية — وعد بتاريخ قديم = خطأ **عدم تحديث تاريخ الوعد**")

col_upld, col_cfg = st.columns([3, 2])

with col_upld:
    promise_file = st.file_uploader(
        "📁 ارفع شيت وعود السداد (Excel) — اختياري",
        type=["xlsx", "xls"],
        key="promise_uploader_page03"
    )

promise_df = None
promise_date_col = 'تاريخ وعد السداد'

if promise_file is not None:
    try:
        promise_raw = pd.read_excel(promise_file)
        with col_cfg:
            st.success(f"✅ تم تحميل شيت وعود السداد ({len(promise_raw):,} سجل) — أعمدته:")
            date_col_options = [c for c in promise_raw.columns]
            promise_date_col = st.selectbox(
                "📅 اختر عمود تاريخ الوعد في الشيت:",
                options=date_col_options,
                index=next(
                    (i for i, c in enumerate(date_col_options) if 'وعد' in str(c) or 'تاريخ' in str(c)),
                    0
                ),
                key="promise_date_col_select"
            )
        promise_df = promise_raw
        st.caption(f"📌 العمود المحدد لتاريخ الوعد: **{promise_date_col}**")
    except Exception as e:
        st.error(f"❌ خطأ في قراءة شيت وعود السداد: {e}")

if promise_df is None:
    st.info("💡 لم يتم رفع شيت وعود السداد — سيعمل النظام بدونه (16 قاعدة فقط).")

st.markdown("---")
st.info("💡 اضغط على الزر أدناه لبدء فحص أخطاء النظام:")

# ─────────────────────────────────────────────────────────────
# 1. فحص الأخطاء التلقائي مع إمكانية إعادتها
# ─────────────────────────────────────────────────────────────
if 'errors_result' not in st.session_state or st.button("🔄 إعادة فحص أخطاء النظام الآن", type="primary", use_container_width=True):
    num_rules = 17 if promise_df is not None else 16
    with st.spinner(f"جاري فحص {num_rules} قاعدة للأخطاء..."):
        if SystemErrorsEngine:
            engine = SystemErrorsEngine()
            result = engine.detect(
                df=df,
                column_map=column_map,
                promise_df=promise_df,
                promise_date_col=promise_date_col
            )
            st.session_state['errors_result'] = result
            st.session_state['total_errors'] = result.get('total_errors', 0)
        else:
            result = None

result = st.session_state.get('errors_result')
if result:
    df_errors = result['data']
    summary = result['summary']
    severity = result.get('error_counts_by_severity', {})
    total_errs = result['total_errors']

    st.markdown("---")
    st.markdown(f"### 📊 نتائج الفحص: تم اكتشاف **{total_errs:,}** خطأ تشغيلي")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("إجمالي الأخطاء", f"{total_errs:,}")
    m2.metric("Critical 🔴", f"{severity.get('Critical', 0):,}")
    m3.metric("High 🟠", f"{severity.get('High', 0):,}")
    m4.metric("Medium 🟡", f"{severity.get('Medium', 0):,}")
    m5.metric("Low 🟢", f"{severity.get('Low', 0):,}")

    # ─────────────────────────────────────────────────────────────
    # ملخص حالات وعود السداد (لو تم رفع الشيت)
    # ─────────────────────────────────────────────────────────────
    if promise_df is not None and '_promise_date' in df_errors.columns:
        st.markdown("---")
        st.markdown("### 📋 ملخص وعود السداد")

        has_promise = df_errors['_promise_date'].notna()
        total_promises = int(has_promise.sum())
        prom_dates = pd.to_datetime(df_errors.loc[has_promise, '_promise_date'], errors='coerce')
        today = pd.Timestamp.today().normalize()

        expired_count = int((prom_dates < today).sum())
        future_count  = int((prom_dates >= today).sum())

        pc1, pc2, pc3 = st.columns(3)
        pc1.metric("📋 إجمالي العملاء بوعد سداد", f"{total_promises:,}")
        pc2.metric("🔴 وعود منتهية (تاريخ قديم)", f"{expired_count:,}", delta=f"⚠️ يحتاج تحديث" if expired_count > 0 else None, delta_color="inverse")
        pc3.metric("🟢 وعود مستقبلية (لا خطأ)", f"{future_count:,}")

        if expired_count > 0:
            st.warning(f"⚠️ يوجد **{expired_count:,}** عميل بوعد سداد منتهي — يجب تحديث تاريخ الوعد أو إغلاق الحالة.")
        if future_count > 0:
            st.success(f"✅ يوجد **{future_count:,}** عميل بوعد سداد مستقبلي — لا يُعدّ خطأً.")

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────
    # 2. أزرار تنزيل علوية (مباشرة وإبرازية)
    # ─────────────────────────────────────────────────────────────
    st.markdown("### 📥 تنزيل شيت البيانات المعدل والتقارير (علوي):")
    c_dl1, c_dl2, c_dl3 = st.columns(3)

    with c_dl1:
        st.download_button(
            label="📥 تحميل التقرير النهائي (أخطاء النظام) — Excel Styled",
            data=export_portfolio_with_summaries(
                clean_df=df,
                col_map=column_map,
                errors_df=df_errors
            ),
            file_name="المحفظة_الأساسية_المعدلة_أخطاء_النظام.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
            key="dl_err_full_styled_top"
        )

    with c_dl2:
        st.download_button(
            label="📊 تنزيل التقرير الاحترافي (نموذج مهاره)",
            data=export_errors_report(df_errors, summary, column_map),
            file_name="نموذج_تقييم_أخطاء_النظام.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="dl_err_pro_fast_top"
        )

    with c_dl3:
        st.download_button(
            label="📋 تنزيل تفاصيل الأخطاء فقط (Excel)",
            data=export_errors(df_errors),
            file_name="تفاصيل_أخطاء_النظام.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="dl_err_raw_fast_top"
        )

    st.markdown("---")

    tabs = st.tabs(['📋 جدول الأخطاء التفصيلي', '📊 ملخص الأخطاء حسب النوع', '📅 جدول وعود السداد'])

    with tabs[0]:
        error_rows = df_errors[df_errors['نوع الخطأ'].astype(str).str.strip() != ''].copy()
        if not error_rows.empty:
            # Show _promise_date if available
            display_cols = [c for c in error_rows.columns if not c.startswith('_') or c == '_promise_date']
            renamed = error_rows[display_cols].rename(columns={'_promise_date': 'تاريخ وعد السداد'})
            st.dataframe(renamed, use_container_width=True, height=500)
        else:
            st.success("🎉 لم يتم العثور على أي أخطاء في المحفظة!")

    with tabs[1]:
        if summary:
            sum_df = pd.DataFrame(list(summary.items()), columns=['نوع الخطأ', 'عدد الحالات'])
            sum_df = sum_df.sort_values('عدد الحالات', ascending=False)
            sum_df['النسبة من إجمالي السجلات'] = (sum_df['عدد الحالات'] / len(df) * 100).round(1).astype(str) + '%'
            st.dataframe(sum_df.style.format({'عدد الحالات': '{:,}'}), use_container_width=True)

    with tabs[2]:
        if promise_df is not None and '_promise_date' in df_errors.columns:
            prom_detail = df_errors[df_errors['_promise_date'].notna()].copy()
            if not prom_detail.empty:
                today_ts = pd.Timestamp.today().normalize()
                prom_detail['حالة الوعد'] = prom_detail['_promise_date'].apply(
                    lambda d: '🔴 منتهي — يجب التحديث' if pd.notna(d) and d < today_ts else ('🟢 مستقبلي — لا خطأ' if pd.notna(d) else '—')
                )
                display_prom = prom_detail[[c for c in prom_detail.columns if not c.startswith('_') or c == '_promise_date']].copy()
                display_prom = display_prom.rename(columns={'_promise_date': 'تاريخ وعد السداد'})
                st.dataframe(display_prom, use_container_width=True, height=450)
            else:
                st.info("لا توجد مديونيات مرتبطة بوعود سداد في شيت الوعود.")
        else:
            st.info("📂 لم يتم رفع شيت وعود السداد أو لا توجد بيانات وعود.")

    # ─────────────────────────────────────────────────────────────
    # 3. أزرار تنزيل سفلية
    # ─────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📥 تنزيل شيت البيانات المعدل والتقارير (سفلي):")
    b_dl1, b_dl2, b_dl3 = st.columns(3)

    with b_dl1:
        st.download_button(
            label="📥 تحميل التقرير النهائي (أخطاء النظام) — Excel Styled",
            data=export_portfolio_with_summaries(
                clean_df=df,
                col_map=column_map,
                errors_df=df_errors
            ),
            file_name="المحفظة_الأساسية_المعدلة_أخطاء_النظام.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
            key="dl_err_full_styled_bottom"
        )

    with b_dl2:
        st.download_button(
            label="📊 تنزيل التقرير الاحترافي (نموذج مهاره)",
            data=export_errors_report(df_errors, summary, column_map),
            file_name="نموذج_تقييم_أخطاء_النظام.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="dl_err_pro_fast_bottom"
        )

    with b_dl3:
        st.download_button(
            label="📋 تنزيل تفاصيل الأخطاء فقط (Excel)",
            data=export_errors(df_errors),
            file_name="تفاصيل_أخطاء_النظام.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="dl_err_raw_fast_bottom"
        )
