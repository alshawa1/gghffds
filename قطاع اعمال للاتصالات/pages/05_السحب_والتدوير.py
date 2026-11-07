import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="السحب والتدوير", page_icon="🔄", layout="wide")
st.markdown("<style>body { direction: rtl; text-align: right; } .stApp { direction: rtl; }</style>", unsafe_allow_html=True)

st.title("🔄 برنامج السحب والتدوير")
st.markdown("##### مهاره لتحصيل الديون — إعادة توزيع المحصلين والمشرفين")

from utils.page_upload import page_portfolio_uploader, render_supervisor_filter

df_full, column_map, raw_df = page_portfolio_uploader("page_05_redistribution", label="📂 ارفع ملف المحفظة للسحب والتدوير (Excel)")

if df_full is None or df_full.empty:
    st.stop()

df = render_supervisor_filter(df_full, column_map, "page_05_redistribution")

from utils.shared_download import render_maharah_download_button
render_maharah_download_button("📥 تحميل التقرير النهائي الشامل (Excel Styled)", key_prefix="pull_page_top", page_key="page_05_redistribution")
st.markdown("---")

from redistribution.pull import PullEngine
from redistribution.distribute import DistributeEngine
from redistribution.validation import DistributionValidator
from utils.shared_download import render_maharah_download_button

col_coll = column_map.get('collector', 'المحصل')
col_sup  = column_map.get('supervisor', 'المشرف')
col_port = column_map.get('portfolio', 'المحافظ')
col_status = column_map.get('main_status', 'الحالة الرئيسية')
col_user = column_map.get('username', 'اسم المستخدم')

all_collectors = sorted([c for c in df[col_coll].unique() if pd.notna(c) and str(c).strip() not in ('', 'nan')])
all_supervisors = sorted([s for s in df[col_sup].unique() if pd.notna(s) and str(s).strip() not in ('', 'nan')]) if col_sup in df.columns else []
all_statuses = sorted([st_val for st_val in df[col_status].unique() if pd.notna(st_val) and str(st_val).strip() not in ('', 'nan')]) if col_status in df.columns else []

st.markdown("""
> 💡 **قواعد محرك السحب والتدوير:**
> 1. **السحب المباشر:** حدد محصل أو أكثر لسحب مديونياتهم (مع إمكانية الفلترة بالحالة الرئيسية).
> 2. **خيار المشرف:** يمكنك إعادة التوزيع لنفس المشرف أو التدوير لمشرف آخر بنفس المحفظة.
> 3. **تجميع العميل:** تظل كل مديونيات العميل الواحدة (رقم الهوية) مجمعة معاً إلى نفس المحصل الجديد.
""")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════
# 1️⃣ خطوة 1: اختيار المحصلين المصدر (السحب منهم)
# ═══════════════════════════════════════════════════════════════════
st.subheader("1️⃣ خطوة 1: اختيار المحصلين المسحوب منهم العملاء")

s_col1, s_col2 = st.columns(2)

with s_col1:
    source_colls = st.multiselect(
        "اختر المحصل/المحصلين لسحب العملاء منهم:",
        all_collectors,
        key="src_colls_select"
    )

with s_col2:
    selected_statuses = st.multiselect(
        "اختر الحالة الرئيسية للعملاء (اختیاري - جميع الحالات لو تُرك فارغاً):",
        all_statuses,
        key="src_statuses_select"
    )

if not source_colls:
    st.info("👆 يرجى اختيار محصل واحد على الأقل لسحب العملاء منه لبدء خطوة التدوير.")
else:
    pull_res = PullEngine.pull_customers(
        df,
        source_collectors=source_colls,
        column_map=column_map,
        selected_statuses=selected_statuses
    )
    pulled_df = pull_res['pulled_df']

    if pulled_df.empty:
        st.warning("⚠️ لا يوجد عملاء ينطبق عليهم خيار السحب المحدد.")
    else:
        st.markdown("#### 📊 نتائج سحب العملاء:")
        m1, m2, m3, m4 = st.columns(4)
        cust_cnt = pull_res.get('customer_count', len(pull_res.get('unique_customers', [])))
        m1.metric("عدد العملاء المسحوبين", f"{cust_cnt:,}")
        m2.metric("عدد المديونيات", f"{pull_res['unique_debts']:,}")
        m3.metric("إجمالي المديونية المسحوبة", f"{pull_res['total_debt']:,.2f} ريال")
        m4.metric("إجمالي المتبقي المسحوب", f"{pull_res['total_remaining']:,.2f} ريال")

        # Detect source supervisors and source portfolios for the pulled customers
        source_sups_in_pull = sorted([s for s in pulled_df[col_sup].unique() if pd.notna(s)]) if col_sup in pulled_df.columns else []
        source_ports_in_pull = sorted([p for p in pulled_df[col_port].unique() if pd.notna(p)]) if col_port in pulled_df.columns else []

        st.caption(f"المحفظة الأصيلة للعملاء المسحوبين: {', '.join(source_ports_in_pull)} | المشرف الحالي: {', '.join(source_sups_in_pull)}")

        st.markdown("---")

        # ═══════════════════════════════════════════════════════════════════
        # 2️⃣ خطوة 2: اختيار التوزيع (نفس المشرف أم مشرف آخر)
        # ═══════════════════════════════════════════════════════════════════
        st.subheader("2️⃣ خطوة 2: اختيار وجهة التدوير والمحصلين الجدد")

        t_col1, t_col2 = st.columns(2)

        with t_col1:
            transfer_option = st.radio(
                "نوع إعادة التوزيع:",
                ["التوزيع لنفس المشرف الحالي", "التوزيع لمشرف آخر"],
                key="tr_option"
            )

        with t_col2:
            if transfer_option == "التوزيع لنفس المشرف الحالي":
                # Available collectors under the same supervisors
                target_sup_selected = source_sups_in_pull[0] if source_sups_in_pull else None
                if target_sup_selected and col_sup in df.columns:
                    target_available_colls = sorted(df[df[col_sup] == target_sup_selected][col_coll].unique().tolist())
                else:
                    target_available_colls = all_collectors
            else:
                # Select a different supervisor
                different_sups = [s for s in all_supervisors if s not in source_sups_in_pull]
                if not different_sups:
                    different_sups = all_supervisors
                
                target_sup_selected = st.selectbox("اختر المشرف الجديد:", different_sups, key="target_new_sup")
                
                # Filter available collectors under the selected new supervisor
                if target_sup_selected and col_sup in df.columns:
                    target_available_colls = sorted(df[df[col_sup] == target_sup_selected][col_coll].unique().tolist())
                else:
                    target_available_colls = all_collectors

        st.markdown("#### 👥 اختر المحصلين الجدد لاستلام العملاء المسحوبين:")
        target_colls = st.multiselect(
            "اختر المحصلين المستهدفين:",
            target_available_colls,
            default=[c for c in target_available_colls if c not in source_colls],  # default exclude source collectors
            key="target_colls_final"
        )

        bal_col1, bal_col2 = st.columns(2)
        with bal_col1:
            balance_method = st.selectbox(
                "معيار توازن التوزيع بين المحصلين المختارين:",
                [
                    ("توازن مزدوج - العملاء + متبقي السداد (العدل التام)", "dual_balance"),
                    ("توازن متبقي السداد فقط", "remaining_balance"),
                    ("توازن عدد العملاء فقط", "customer_count")
                ],
                format_func=lambda x: x[0],
                key="bal_method_final"
            )[1]

        with bal_col2:
            allow_cross_portfolio = st.checkbox(
                "🔓 تجاوز قاعدة عزل المحافظ (السماح بالنقل بين المحافظ المختلفة)",
                value=False,
                key="allow_cross_port_toggle",
                help="عند تفعيل هذا الخيار، سيسمح النظام بنقل وتدوير العملاء إلى محصلين يعملون في محافظ أخرى."
            )

        if not target_colls:
            st.info("👈 يرجى اختيار محصل جديد واحد على الأقل في القائمة أعلاه لتنفيذ التوزيع.")
        else:
            collector_info_cols = [c for c in [col_coll, col_sup, col_port, col_user] if c in df.columns]
            collector_info = df[collector_info_cols].drop_duplicates(subset=[col_coll]).copy()
            collector_info = collector_info[collector_info[col_coll].isin(target_colls)]
            collector_info.columns = ['المحصل', 'المشرف', 'المحافظ', 'اسم المستخدم'][:len(collector_info.columns)]

            coll_port_map = dict(zip(collector_info['المحصل'], collector_info['المحافظ']))

            val_res = DistributionValidator.validate_before_distribution(
                pulled_df, target_colls, column_map, coll_port_map, allow_cross_portfolio=allow_cross_portfolio
            )

            st.markdown("#### 🛡️ فحص عزل المحافظ والأمان:")
            if val_res['can_proceed']:
                if allow_cross_portfolio:
                    st.warning("⚠️ تم تعطيل قاعدة عزل المحافظ بناءً على رغبتك. يمكنك النقل عبر المحافظ الآن!")
                else:
                    st.success("✅ التوافق تام 100%! المحصلين المختارين ينتمون لنفس محفظة العملاء. يمكنك الضغط لتنفيذ التدوير.")
            else:
                for err in val_res['errors']:
                    st.error(f"❌ {err}")

            if val_res['warnings']:
                for warn in val_res['warnings']:
                    st.warning(f"{warn}")

            if st.button("🚀 تنفيذ وتطبيق السحب والتدوير الجديد الآن", type="primary", disabled=not val_res['can_proceed']):
                with st.spinner("جاري التوزيع والتأكد من عدم تشتيت أي عميل..."):
                    dist_res = DistributeEngine.distribute_customers(
                        pulled_df, target_colls, collector_info, column_map,
                        balance_method=balance_method,
                        allow_cross_portfolio=allow_cross_portfolio
                    )

                    if dist_res['success']:
                        dist_df = dist_res['distributed_df']
                        coll_summary = dist_res['collector_summary']
                        port_summary = dist_res['portfolio_summary']

                        # Update clean_df in session_state for this page
                        st.session_state['page_05_redistribution_clean_df'] = dist_df.copy()
                        st.session_state['dist_res'] = dist_res

                        st.success("🎉 تم السحب والتدوير وتحديث المحفظة بنجاح 100%!")

                        st.markdown("### 📊 ملخص توزيع المحصلين الجدد:")
                        st.dataframe(coll_summary, use_container_width=True)

                        st.markdown("### 📋 عينة من نتائج التدوير الفعلي:")
                        sample_cols = [c for c in ['رقم الهوية', 'المحافظ', 'الحالة الرئيسية', 'المحصل', 'المحصل الجديد', 'المشرف الجديد', 'متبقي سداد موثق'] if c in dist_df.columns]
                        st.dataframe(dist_df[sample_cols].head(20), use_container_width=True)
                    else:
                        st.error("فشل التوزيع بسبب وجود تعارضات في المحافظ.")

# ─── زرار تحميل الشيت الأساسي والتقارير ───
render_maharah_download_button("📥 تحميل التقرير النهائي (Excel Styled)", key_prefix="pull_page_final_styled", page_key="page_05_redistribution")
