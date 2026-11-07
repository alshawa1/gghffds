import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="التقارير الشاملة", page_icon="📝", layout="wide")
st.markdown("<style>body{direction:rtl;text-align:right;}.stApp{direction:rtl;}</style>", unsafe_allow_html=True)

st.title("📝 التقارير الشاملة")
st.markdown("##### مهاره لتحصيل الديون — قطاع أعمال الاتصالات")

from utils.page_upload import page_portfolio_uploader, page_payment_uploader, render_supervisor_filter

df_full, column_map, raw_df = page_portfolio_uploader("page_07_reports", label="📂 ارفع ملف المحفظة للتقارير الشاملة (Excel)")

if df_full is None or df_full.empty:
    st.stop()

df = render_supervisor_filter(df_full, column_map, "page_07_reports")

payment_df, payment_map = page_payment_uploader("page_07_reports", label="📂 ارفع ملف السدادات (اختياري لتقرير التحصيل والسدادات)")

from reports.export import (export_coverage_report, export_payment_comparison,
                             export_errors_report, export_monthly_report,
                             export_portfolio_with_summaries, export_errors, export_neglect)
from reports.coverage_analysis import (build_coverage_report, build_status_payment_report,
                                        build_monthly_report)
try:
    from payment_analysis.matching import PaymentMatcher
    from payment_analysis.aggregation import PaymentAggregator
    from payment_analysis.ranking import rank_collectors, rank_supervisors
except Exception:
    PaymentMatcher = PaymentAggregator = rank_collectors = rank_supervisors = None

def ensure_payment_file():
    curr_pay = st.session_state.get('payment_df', payment_df)
    curr_map = st.session_state.get('payment_map', payment_map)
    if curr_pay is None or (isinstance(curr_pay, pd.DataFrame) and curr_pay.empty):
        st.info("💡 ارفع ملف السدادات لتفعيل هذا التقرير:")
        up = st.file_uploader("ملف السدادات (Excel)", type=['xlsx','xls'], key="rpt_pay_up")
        if up:
            from data.loader import load_payment_file
            from data.cleaner import clean_payment_file
            res = load_payment_file(up)
            if not res.get('error'):
                cp = clean_payment_file(res['raw_df'], res['column_map'])
                st.session_state['payment_df'] = cp
                st.session_state['payment_map'] = res['column_map']
                st.rerun()
        return None, None
    return curr_pay, curr_map or {}

# Column helpers
cust_col = column_map.get('customer_id','رقم الهوية') if column_map.get('customer_id','رقم الهوية') in df.columns else '_customer_id'
sup_col  = column_map.get('supervisor','المشرف') if column_map.get('supervisor','المشرف') in df.columns else '_supervisor'
coll_col = column_map.get('collector','المحصل') if column_map.get('collector','المحصل') in df.columns else '_collector'
port_col = column_map.get('portfolio','المحافظ') if column_map.get('portfolio','المحافظ') in df.columns else '_portfolio'
debt_col = column_map.get('debt_amount','مبلغ الميدونية')
if debt_col not in df.columns: debt_col = 'مبلغ المديونية' if 'مبلغ المديونية' in df.columns else 'مبلغ الميدونية'
rem_col  = column_map.get('remaining_doc','متبقي سداد موثق')
if rem_col not in df.columns: rem_col = '_remaining_doc'
date_col = column_map.get('followup_date','تاريخ المتابعة')
if date_col not in df.columns: date_col = '_followup_date'
main_status_col = column_map.get('main_status','الحالة الرئيسية')
if main_status_col not in df.columns: main_status_col = '_main_status'

for c in [debt_col, rem_col]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)

# ───────────────────────────────────────────────────────────────────
# Report Selector
# ───────────────────────────────────────────────────────────────────
report_options = {
    "📥 تحميل الشيت الأساسي المعالج": "download_portfolio",
    "📊 تقرير التغطية والتحصيل اليومي": "coverage_daily",
    "📞 تقرير التوصل وعدم التوصل": "contact_status",
    "💰 تقرير السداد والتحصيل بالحالات": "payment_by_status",
    "📅 التقرير الشهري (Dashboard)": "monthly_report",
}

selected_rpt = st.selectbox("📑 اختر التقرير المطلوب:", list(report_options.keys()), key="rpt_select")
rpt_key = report_options[selected_rpt]
st.markdown("---")

# ═══════════════════════════════════════════════════════════════════
# 1. Download Portfolio with Summaries
# ═══════════════════════════════════════════════════════════════════
if rpt_key == "download_portfolio":
    st.subheader("📥 تحميل الشيت الأساسي مع الملخصات")
    st.info("""
    يمكنك تحميل ملف Excel شامل يحتوي على:
    - **الشيت الأساسي** (المحفظة الكاملة المعالجة والمنظفة)
    - **ملخص المحافظ** (إجمالي المديونية والمتبقي لكل محفظة)
    - **ملخص المحصلين** (إجمالي أعداد العملاء والمديونيات لكل محصل)
    - **أخطاء النظام** (إن تم تشغيل فحص الأخطاء مسبقاً)
    - **تقرير الإهمال** (إن تم تشغيل فحص الإهمال مسبقاً)
    """)

    errors_data = st.session_state.get('errors_result', {}).get('data')
    neglect_data = st.session_state.get('neglect_result', {}).get('data')

    if st.button("🚀 توليد الملف الشامل الآن", type="primary"):
        with st.spinner("جاري توليد الملف..."):
            excel_bytes = export_portfolio_with_summaries(
                clean_df=df,
                col_map=column_map,
                errors_df=errors_data,
                neglect_df=neglect_data,
                payment_df=payment_df
            )
            st.download_button(
                label="📥 تحميل الشيت الأساسي + الملخصات (Excel)",
                data=excel_bytes,
                file_name="المحفظة_الكاملة_مع_الملخصات.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ═══════════════════════════════════════════════════════════════════
# 2. Daily Coverage & Collection Report
# ═══════════════════════════════════════════════════════════════════
elif rpt_key == "coverage_daily":
    st.subheader("📊 تقرير التغطية والتحصيل (حسب المشرف والمحصل)")

    from utils.date_utils import extract_unique_dates
    unique_dates = extract_unique_dates(df, date_col)

    def _safe_int(val, default=0):
        if pd.isna(val) or val is None: return default
        try: return int(float(val))
        except: return default

    def _safe_float(val, default=0.0):
        if pd.isna(val) or val is None: return default
        try: return float(val)
        except: return default

    # ── اختيار نوع الفترة ──
    period_mode = st.radio(
        "نوع الفترة:",
        ["📅 يومي", "🗓 أسبوعي (من/إلى)", "📆 شهري"],
        horizontal=True, key="cov_period_mode"
    )

    col_d1, col_d2, col_d3 = st.columns(3)

    sel_date = start_date = end_date = sel_month = None

    with col_d1:
        if period_mode == "📅 يومي":
            date_mode = st.radio("طريقة اختيار التاريخ:", ["📋 من الشيت (المتوفر)", "📅 تقويم"], horizontal=True, key="cov_date_mode")
            if date_mode == "📅 تقويم":
                default_dt = None
                if unique_dates:
                    try:
                        import datetime
                        default_dt = datetime.datetime.strptime(unique_dates[0], '%Y-%m-%d').date()
                    except:
                        pass
                picked = st.date_input("اختر اليوم:", value=default_dt, key="cov_cal_input")
                sel_date = picked.strftime('%Y-%m-%d') if picked else None
            else:
                if unique_dates:
                    sel_date = st.selectbox("اختر يوم من تواريخ الشيت:", unique_dates, index=0)
                else:
                    picked = st.date_input("اختر اليوم:", key="cov_cal_fallback")
                    sel_date = picked.strftime('%Y-%m-%d') if picked else None

        elif period_mode == "🗓 أسبوعي (من/إلى)":
            start_date_inp = st.date_input("من تاريخ:", key="cov_start")
            end_date_inp   = st.date_input("إلى تاريخ:", key="cov_end")
            if start_date_inp and end_date_inp:
                start_date = start_date_inp.strftime('%Y-%m-%d')
                end_date   = end_date_inp.strftime('%Y-%m-%d')

        else:  # شهري
            import datetime
            sel_month = st.text_input("أدخل الشهر (مثال: 2025-08):",
                                       value=datetime.date.today().strftime('%Y-%m'), key="cov_month_inp")

    with col_d2:
        filter_port = st.multiselect("تصفية حسب المحفظة:", [p for p in df[port_col].unique() if pd.notna(p)], default=None)

    with col_d3:
        target_cov_count = st.number_input("🎯 مستهدف التغطية (عدد) لكل محصل:", min_value=0, value=0, step=10)
        target_coll_amt  = st.number_input("💰 مستهدف التحصيل (ريال) لكل محصل:", min_value=0.0, value=0.0, step=1000.0)

    filt_df = df[df[port_col].isin(filter_port)].copy() if filter_port else df.copy()

    pay_df_work, pay_map_work = ensure_payment_file()

    # ── تحديد وجود تاريخ كافٍ لتشغيل التقرير
    has_period = sel_date or (start_date and end_date) or (sel_month and len(sel_month) >= 7)

    if has_period:
        with st.spinner("جاري بناء تقرير التغطية والتحصيل..."):
            coverage_df = build_coverage_report(
                filt_df, column_map,
                selected_date=sel_date,
                payment_df=pay_df_work,
                payment_map=pay_map_work,
                target_coverage_count=int(target_cov_count),
                target_collection_amount=target_coll_amt,
                start_date=start_date,
                end_date=end_date,
                selected_month=sel_month,
            )

        if coverage_df.empty:
            period_label = sel_date or (f"{start_date} → {end_date}") or sel_month
            st.warning(f"لا توجد متابعات مسجلة في الفترة: {period_label}")
        else:
            period_label = sel_date or (f"{start_date} → {end_date}") or sel_month
            st.markdown(f"### 📊 نتائج التغطية والتحصيل للفترة: **{period_label}**")

            # 📥 زر تحميل مباشر في الأعلى
            excel_bytes = export_coverage_report(coverage_df, period_label)
            st.download_button(
                label="📥 تحميل تقرير التغطية والتحصيل الشامل (Excel)",
                data=excel_bytes,
                file_name=f"تقرير_التغطية_والتحصيل_{period_label}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                key="top_cov_dl_btn",
                use_container_width=True
            )
            st.markdown("<div style='margin: 15px 0;'></div>", unsafe_allow_html=True)

            # ── KPIs ──
            total_row = coverage_df.iloc[-1]
            k1, k2, k3, k4, k5, k6 = st.columns(6)
            k1.metric("✅ توصل",           f"{_safe_int(total_row.get('توصل')):,}")
            k2.metric("❌ عدم توصل",       f"{_safe_int(total_row.get('عدم توصل')):,}")
            k3.metric("📵 لا يرد",         f"{_safe_int(total_row.get('لا يرد')):,}")
            k4.metric("🔇 مغلق",           f"{_safe_int(total_row.get('مغلق')):,}")
            k5.metric("🎯 نسبة التغطية %", f"{_safe_float(total_row.get('نسبة التغطية %')):.1f}%")
            k6.metric("💰 إجمالي التحصيل", f"{_safe_float(total_row.get('إجمالي التحصيل')):,.2f} ﷼")

            if _safe_int(total_row.get('العملاء المغطين')) == 0 and unique_dates:
                recent_dates = " — ".join(unique_dates[:3])
                st.info(f"💡 **تنبيه:** لا توجد متابعات مسجلة في شيت المحفظة المرفوع بتاريخ **{period_label}**.\n\nآخر تواريخ متابعات مسجلة في الشيت هي: **{recent_dates}** (يمكنك اختيار تاريخ منها لرؤية إحصائيات التغطية لذلك اليوم).")

            # ── مؤشرات المستهدفات ──
            if target_cov_count > 0 or target_coll_amt > 0:
                st.markdown("#### 🏆 مؤشرات تحقيق المستهدفات:")
                ta1, ta2, ta3, ta4 = st.columns(4)
                if target_cov_count > 0:
                    covered_total = _safe_int(total_row.get('العملاء المغطين'))
                    ach_cov = round((covered_total / (target_cov_count * (len(coverage_df)-1))) * 100, 1) if target_cov_count > 0 else 0.0
                    ta1.metric("🎯 مستهدف التغطية الكلي", f"{target_cov_count * (len(coverage_df)-1):,} عميل")
                    ta2.metric("📈 تحقيق التغطية", f"{covered_total:,} ({ach_cov:.1f}%)",
                               delta=f"+{ach_cov-100:.1f}%" if ach_cov >= 100 else f"{ach_cov-100:.1f}%")
                if target_coll_amt > 0:
                    total_coll = _safe_float(total_row.get('إجمالي التحصيل'))
                    ach_coll = round((total_coll / (target_coll_amt * (len(coverage_df)-1))) * 100, 1) if target_coll_amt > 0 else 0.0
                    ta3.metric("💰 مستهدف التحصيل الكلي", f"{target_coll_amt * (len(coverage_df)-1):,.0f} ﷼")
                    ta4.metric("📊 تحقيق التحصيل %", f"{ach_coll:.1f}%",
                               delta=f"+{ach_coll-100:.1f}%" if ach_coll >= 100 else f"{ach_coll-100:.1f}%")

            st.markdown("---")
            st.markdown("#### 📋 جدول ملخص أداء التغطية والتحصيل:")

            # 🎯 تحديد الأعمدة الـ 8 المطلوبة حصرياً وبالترتيب الدقيق
            desired_cols = [
                sup_col, coll_col,
                'العملاء المغطين', 'مستهدف التغطية', 'نسبة التغطية %',
                'إجمالي التحصيل', 'مستهدف التحصيل', 'نسبة التحصيل %'
            ]
            cols_to_show = [c for c in desired_cols if c in coverage_df.columns]
            table_df = coverage_df[cols_to_show].copy()

            # إعادة تسمية الأعمدة لعرض عربي جميل ودقيق
            rename_map = {
                sup_col: 'المشرف',
                coll_col: 'المحصل',
                'العملاء المغطين': 'التغطية (عدد العملاء)',
                'مستهدف التغطية': 'مستهدف التغطية',
                'نسبة التغطية %': 'نسبة التغطية %',
                'إجمالي التحصيل': 'إجمالي التحصيل (ريال)',
                'مستهدف التحصيل': 'مستهدف التحصيل (ريال)',
                'نسبة التحصيل %': 'نسبة التحصيل %'
            }
            show_df = table_df.rename(columns=rename_map)

            # تنسيق أرقام الجدول والنسب المئوية
            fmt_dict = {
                'التغطية (عدد العملاء)': '{:,}',
                'مستهدف التغطية': '{:,}',
                'نسبة التغطية %': '{:.1f}%',
                'إجمالي التحصيل (ريال)': '{:,.2f}',
                'مستهدف التحصيل (ريال)': '{:,.2f}',
                'نسبة التحصيل %': '{:.1f}%'
            }
            active_fmt = {k: v for k, v in fmt_dict.items() if k in show_df.columns}
            st.dataframe(show_df.style.format(active_fmt), use_container_width=True)

            # Chart
            plot_df = coverage_df.iloc[:-1].copy()
            if not plot_df.empty and coll_col in plot_df.columns:
                fig = px.bar(plot_df, x=coll_col,
                             y=['توصل', 'عدم توصل', 'لا يرد', 'مغلق'],
                             title=f"توزيع التواصل — {period_label}", barmode='stack')
                st.plotly_chart(fig, use_container_width=True)

            st.download_button(
                label="📥 تحميل تقرير التغطية والتحصيل (Excel)",
                data=excel_bytes,
                file_name=f"تقرير_التغطية_{period_label}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="bottom_cov_dl_btn",
                use_container_width=True
            )



# ═══════════════════════════════════════════════════════════════════
# 3. Contact Status Report (توصل / عدم توصل / لا يرد / مغلق)
# ═══════════════════════════════════════════════════════════════════
elif rpt_key == "contact_status":
    st.subheader("📞 تقرير التوصل وعدم التوصل (مقارنة الحالات)")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        from utils.date_utils import extract_unique_dates
        unique_dates_cs = extract_unique_dates(df, date_col)
        if unique_dates_cs:
            from_date = st.selectbox("من تاريخ:", unique_dates_cs, index=len(unique_dates_cs)-1)
            to_date   = st.selectbox("إلى تاريخ:", unique_dates_cs, index=0)
        else:
            from_date = st.text_input("من تاريخ (YYYY-MM-DD):")
            to_date   = st.text_input("إلى تاريخ (YYYY-MM-DD):")
    with col_f2:
        filter_sup = st.multiselect("تصفية حسب المشرف:", [s for s in df[sup_col].unique() if pd.notna(s)])
    with col_f3:
        filter_port = st.multiselect("تصفية حسب المحفظة:", [p for p in df[port_col].unique() if pd.notna(p)])

    filt_df = df.copy()
    if filter_sup: filt_df = filt_df[filt_df[sup_col].isin(filter_sup)]
    if filter_port: filt_df = filt_df[filt_df[port_col].isin(filter_port)]

    if from_date and date_col in filt_df.columns:
        filt_df['_d'] = filt_df[date_col].astype(str).str[:10]
        filt_df = filt_df[(filt_df['_d'] >= str(from_date)[:10]) & (filt_df['_d'] <= str(to_date)[:10])]

    with st.spinner("جاري بناء التقرير..."):
        coverage_full = build_coverage_report(filt_df, column_map, selected_date=None)

    if coverage_full.empty:
        st.warning("لا توجد بيانات للفترة المحددة")
    else:
        total_row = coverage_full.iloc[-1]
        t1,t2,t3,t4 = st.columns(4)
        t1.metric("✅ إجمالي التوصل", f"{int(total_row.get('توصل',0)):,}", f"{float(total_row.get('نسبة التوصل %',0)):.1f}%")
        t2.metric("❌ عدم توصل", f"{int(total_row.get('عدم توصل',0)):,}")
        t3.metric("📵 لا يرد", f"{int(total_row.get('لا يرد',0)):,}")
        t4.metric("🔇 مغلق", f"{int(total_row.get('مغلق',0)):,}")

        st.dataframe(coverage_full.style.format({
            'توصل':'{:,}','عدم توصل':'{:,}','لا يرد':'{:,}','مغلق':'{:,}',
            'إجمالي المتابعة':'{:,}',
            'نسبة التوصل %':'{:.1f}%','نسبة عدم التوصل %':'{:.1f}%','نسبة لا يرد %':'{:.1f}%'
        }), use_container_width=True)

        # Donut chart for contact distribution
        categories = ['توصل','عدم توصل','لا يرد','مغلق']
        vals = [int(total_row.get(c,0)) for c in categories]
        fig_donut = go.Figure(go.Pie(
            labels=categories, values=vals,
            hole=0.5,
            marker_colors=['#2E7D32','#C62828','#E65100','#424242']
        ))
        fig_donut.update_layout(title_text='توزيع حالات التواصل')
        st.plotly_chart(fig_donut, use_container_width=True)

        excel_bytes = export_coverage_report(coverage_full, f"{from_date} → {to_date}")
        st.download_button("📥 تحميل تقرير التوصل Excel", data=excel_bytes,
                           file_name=f"تقرير_التوصل_{from_date}_{to_date}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ═══════════════════════════════════════════════════════════════════
# 4. Payment by Status Report
# ═══════════════════════════════════════════════════════════════════
elif rpt_key == "payment_by_status":
    st.subheader("💰 تقرير السداد والتحصيل حسب الحالات")

    pay_df_work, pay_map_work = ensure_payment_file()

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        from_date_p = st.date_input("من تاريخ السداد:")
    with col_d2:
        to_date_p = st.date_input("إلى تاريخ السداد:")

    if st.button("🔍 تحليل السداد بالحالات", type="primary"):
        with st.spinner("جاري تحليل السداد بالحالات..."):
            status_rpt = build_status_payment_report(
                df, column_map,
                payment_df=pay_df_work, payment_map=pay_map_work,
                date_from=str(from_date_p), date_to=str(to_date_p)
            )
            st.session_state['status_rpt'] = status_rpt

    if 'status_rpt' in st.session_state:
        status_rpt = st.session_state['status_rpt']
        if not status_rpt.empty:
            total_row = status_rpt.iloc[-1]
            s1,s2,s3,s4 = st.columns(4)
            s1.metric("عدد الحسابات الكلية", f"{int(total_row.get('عدد الحسابات',0)):,}")
            s2.metric("إجمالي المبالغ المديونية", f"{float(total_row.get('المبلغ',0)):,.2f}")
            s3.metric("إجمالي السداد", f"{float(total_row.get('السداد',0)):,.2f}")
            s4.metric("نسبة السداد الكلية", f"{float(total_row.get('النسبة %',0)):.2f}%")

            st.dataframe(status_rpt.style.format({
                'عدد الحسابات':'{:,}',
                'المبلغ':'{:,.2f}',
                'السداد':'{:,.2f}',
                'النسبة %':'{:.2f}%',
                'نسبة من إجمالي السداد %':'{:.2f}%'
            }), use_container_width=True)

            # Bar chart
            plot_df = status_rpt.iloc[:-1].copy()
            if 'السداد' in plot_df.columns:
                fig_bar = px.bar(plot_df, x='الحالة الرئيسية', y='السداد',
                                text_auto=',.0f', title='السداد حسب الحالة الرئيسية',
                                color='النسبة %')
                st.plotly_chart(fig_bar, use_container_width=True)

            # Export
            from io import BytesIO
            import openpyxl
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as w:
                status_rpt.to_excel(w, sheet_name='السداد بالحالات', index=False)
            st.download_button("📥 تحميل تقرير السداد بالحالات Excel",
                               data=buf.getvalue(),
                               file_name=f"تقرير_السداد_بالحالات.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ═══════════════════════════════════════════════════════════════════
# 5. Monthly Report Dashboard
# ═══════════════════════════════════════════════════════════════════
elif rpt_key == "monthly_report":
    st.subheader("📅 التقرير الشهري — Dashboard مجمع")

    pay_df_work, pay_map_work = ensure_payment_file()

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        selected_month = st.text_input("الشهر (مثال: 2025-06):", value="2025-06")
    with col_m2:
        slicer_ports = st.multiselect("تصفية حسب المحفظة:", [p for p in df[port_col].unique() if pd.notna(p)])
    with col_m3:
        slicer_sups  = st.multiselect("تصفية حسب المشرف:", [s for s in df[sup_col].unique() if pd.notna(s)])

    filt_df_m = df.copy()
    if slicer_ports: filt_df_m = filt_df_m[filt_df_m[port_col].isin(slicer_ports)]
    if slicer_sups:  filt_df_m = filt_df_m[filt_df_m[sup_col].isin(slicer_sups)]

    if st.button("📊 بناء التقرير الشهري", type="primary"):
        with st.spinner("جاري بناء التقرير الشهري..."):
            monthly_df = build_monthly_report(
                filt_df_m, column_map,
                payment_df=pay_df_work, payment_map=pay_map_work,
                selected_month=selected_month
            )
            st.session_state['monthly_df'] = monthly_df

    if 'monthly_df' in st.session_state:
        monthly_df = st.session_state['monthly_df']
        if not monthly_df.empty:
            st.markdown(f"### 📊 تقرير المتابعة الشهري — {selected_month}")

            # Summary table (like photo 4)
            st.dataframe(monthly_df.style.format({
                c: '{:,.2f}' for c in monthly_df.select_dtypes(include='number').columns
            }), use_container_width=True)

            # Donut chart for monthly collection by portfolio
            plot_df_m = monthly_df.iloc[:-1].copy()
            port_col_m = monthly_df.columns[0]
            coll_col_m = 'إجمالي التحصيل الشهري' if 'إجمالي التحصيل الشهري' in monthly_df.columns else None

            c_left, c_right = st.columns(2)
            with c_left:
                if coll_col_m and coll_col_m in plot_df_m.columns:
                    fig_donut = go.Figure(go.Pie(
                        labels=plot_df_m[port_col_m].astype(str),
                        values=pd.to_numeric(plot_df_m[coll_col_m], errors='coerce').fillna(0),
                        hole=0.55,
                        textinfo='label+percent'
                    ))
                    fig_donut.update_layout(title_text='إجمالي التحصيل الشهري لكل محفظة')
                    st.plotly_chart(fig_donut, use_container_width=True)

            with c_right:
                debt_col_m = 'إجمالي المحفظة' if 'إجمالي المحفظة' in monthly_df.columns else None
                if debt_col_m:
                    fig_bar = px.bar(
                        plot_df_m, x=port_col_m,
                        y=[debt_col_m, coll_col_m] if coll_col_m else [debt_col_m],
                        title='مقارنة المديونية والتحصيل الشهري لكل محفظة',
                        barmode='group', text_auto=',.0f'
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

            # Collector breakdown per portfolio
            st.markdown("### 📋 أداء المحصلين تفصيلياً:")
            grp = [c for c in [port_col, sup_col, coll_col] if c in filt_df_m.columns]
            if grp:
                coll_detail = filt_df_m.groupby(grp).agg(
                    عدد_العملاء=(cust_col, 'nunique') if cust_col in filt_df_m.columns else (coll_col, 'count'),
                    إجمالي_المتبقي=(rem_col, 'sum') if rem_col in filt_df_m.columns else (coll_col, 'count')
                ).reset_index()

                # Per portfolio bar chart
                for prt in (slicer_ports or [p for p in filt_df_m[port_col].unique() if pd.notna(p)]):
                    p_data = coll_detail[coll_detail[port_col] == prt] if port_col in coll_detail.columns else coll_detail
                    if not p_data.empty:
                        fig_p = px.bar(p_data, x=coll_col if coll_col in p_data.columns else p_data.columns[-2],
                                       y='إجمالي_المتبقي', text_auto=',.0f',
                                       title=f'تفصيل المحصلين — محفظة {prt}', color='إجمالي_المتبقي')
                        st.plotly_chart(fig_p, use_container_width=True)

            # Export
            excel_bytes = export_monthly_report(monthly_df)
            st.download_button("📥 تحميل التقرير الشهري Excel", data=excel_bytes,
                               file_name=f"التقرير_الشهري_{selected_month}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ═══════════════════════════════════════════════════════════════════
# ─── زرار تحميل الشيت الأساسي + التقارير في نهاية كل تقرير ───
# ═══════════════════════════════════════════════════════════════════
st.markdown("---")
from utils.shared_download import render_maharah_download_button
render_maharah_download_button("📥 تحميل التقرير النهائي (Excel Styled)", key_prefix="reports_page_bottom", page_key="page_07_reports")
