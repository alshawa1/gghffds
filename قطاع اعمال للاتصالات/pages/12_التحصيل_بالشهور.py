# -*- coding: utf-8 -*-
"""
قطاع اعمال للاتصالات/pages/12_التحصيل_بالشهور.py
─────────────────────────────────────────────
برنامج تقرير التحصيل بالشهور بالمستهدف:
مقارنة تحصيل كل محصل ومشرف شهر بشهر مع المستهدف المالي لكل شهر ونسب الإنجاز بربط رقم المديونية وتاريخ السداد.
"""

import streamlit as st
import polars as pl
import pandas as pd
import io
import os
import sys
from datetime import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BIZ_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(BIZ_DIR)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from modules.module12_monthly_targets import MonthlyTargetsModule
from export.excel_writer_xl import ExcelReportWriter

st.markdown("""
<div style="background: #ffffff; border: 1px solid #cbd5e1; padding: 22px; border-radius: 14px; margin-bottom: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
    <h2 style="margin: 0; color: #0f172a; display: flex; align-items: center; gap: 10px; font-weight: 900;">
        📅 تقرير التحصيل بالشهور بالمستهدف
    </h2>
    <p style="margin: 8px 0 0 0; color: #475569; font-size: 1.05rem; font-weight: 600;">
        مقارنة تحصيل كل محصل ومشرف شهراً بشهر مع المستهدف المالي لكل شهر، واحتساب نسب الإنجاز بدقة عبر ربط رقم المديونية وتاريخ السداد.
    </p>
</div>
""", unsafe_allow_html=True)

col_u1, col_u2 = st.columns(2)

with col_u1:
    port_file = st.file_uploader(
        "📂 1. ملف المحفظة الأساسية (.xlsx)",
        type=["xlsx", "xls"],
        help="ملف المحفظة الذي يحتوي على المشرف والمحصل ورقم المديونية"
    )

with col_u2:
    pmt_file = st.file_uploader(
        "💰 2. ملف السدادات والتحصيل (.xlsx)",
        type=["xlsx", "xls"],
        help="ملف السدادات الذي يحتوي على رقم المديونية ومبلغ السداد وتاريخ السداد"
    )

if not port_file or not pmt_file:
    st.info("💡 يرجى رفع ملف المحفظة وملف السدادات للبدء في اكتشاف الشهور وإعداد التقرير.")
    st.stop()

@st.cache_data(show_spinner="⏳ جارٍ قراءة وتحليل ملفات البيانات...")
def _read_data(port_bytes, pmt_bytes):
    df_port = pl.read_excel(io.BytesIO(port_bytes), engine="calamine")
    df_pmt  = pl.read_excel(io.BytesIO(pmt_bytes), engine="calamine")
    return df_port, df_pmt

try:
    df_port, df_pmt = _read_data(port_file.getvalue(), pmt_file.getvalue())
except Exception as e:
    st.error(f"❌ حدث خطأ أثناء قراءة الملفات: {e}")
    st.stop()

avail_months = MonthlyTargetsModule.detect_available_months(df_pmt)

if not avail_months:
    st.warning("⚠️ لم يتم العثور على تواريخ سداد صالحة في ملف السدادات.")
    st.stop()

st.markdown("### ⚙️ إعدادات الشهور والمستهدفات")

month_keys_map = {m["label"]: m["key"] for m in avail_months}
all_labels = list(month_keys_map.keys())

sel_labels = st.multiselect(
    "🗓 اختر الشهور المراد إدراجها بالتقرير:",
    options=all_labels,
    default=all_labels,
    help="يمكنك اختيار شهر واحد أو عدة شهور للمقارنة جنباً إلى جنب"
)

if not sel_labels:
    st.warning("يرجى اختيار شهر واحد على الأقل للمتابعة.")
    st.stop()

sel_keys = [month_keys_map[lbl] for lbl in sel_labels]

st.markdown("##### 🎯 تحديد مستهدف التحصيل المالي لكل شهر (لكل محصل - ريال):")
c_tgt1, c_tgt2 = st.columns([2, 1])
with c_tgt1:
    unified_val = st.number_input(
        "مستهدف موحد لجميع الشهور (ريال):",
        min_value=100.0,
        value=50000.0,
        step=1000.0,
        help="قيمة افتراضية تسري على كل الشهور المحددة"
    )
with c_tgt2:
    use_unified = st.checkbox("اعتماد نفس المستهدف لجميع الشهور", value=True)

targets_dict = {}
m_cols = st.columns(min(len(sel_labels), 3))
for idx, lbl in enumerate(sel_labels):
    k = month_keys_map[lbl]
    col_w = m_cols[idx % len(m_cols)]
    with col_w:
        if use_unified:
            targets_dict[k] = float(unified_val)
            st.text_input(f"مستهدف {lbl}:", value=f"{unified_val:,.2f} ﷼", disabled=True, key=f"biz_disp_{k}")
        else:
            t_inp = st.number_input(f"مستهدف {lbl} (ريال):", min_value=100.0, value=50000.0, step=1000.0, key=f"biz_inp_{k}")
            targets_dict[k] = float(t_inp)

# تصفية المشرفين
sup_candidates = ["المشرف", "اسم المشرف", "supervisor", "Supervisor"]
sup_c = next((c for c in sup_candidates if c in df_port.columns), None)
selected_sups = None
if sup_c:
    sups_list = sorted([str(x).strip() for x in df_port[sup_c].drop_nulls().unique().to_list() if str(x).strip() not in ('', 'nan', 'None')])
    if sups_list:
        st.markdown("##### 👥 تصفية المشرفين (اختياري):")
        chosen_sups = st.multiselect("اختر المشرفين (اتركه فارغاً لاختيار الكل):", options=sups_list, default=sups_list)
        if chosen_sups:
            selected_sups = chosen_sups

if st.button("🚀 إنشاء وتوليد تقرير التحصيل بالشهور", use_container_width=True, type="primary"):
    with st.spinner("⏳ جارٍ ربط البيانات واحتساب مبالغ التحصيل والمستهدفات بدقة..."):
        try:
            mod = MonthlyTargetsModule()
            res = mod.run(
                portfolio=df_port,
                payments=df_pmt,
                selected_months=sel_keys,
                monthly_targets=targets_dict,
                supervisors=selected_sups
            )
            report_table = res["report_table"]
            months_meta  = res["months_meta"]
            stats        = res["stats"]

            st.balloons()
            st.success("✨ تم إنشاء التقرير بنجاح واحتساب كافة نسب الإنجاز!")

            # كروت المؤشرات
            st.markdown("#### 📊 مؤشرات الأداء الكلية:")
            kpi_cols = st.columns(min(len(stats), 4))
            for i, (k, v) in enumerate(stats.items()):
                c_idx = i % len(kpi_cols)
                with kpi_cols[c_idx]:
                    st.metric(label=k, value=str(v))

            # عرض الجدول
            st.markdown("---")
            st.markdown("### 📋 جدول تقرير التحصيل بالشهور بالمستهدف:")
            disp_cols = [c for c in report_table.columns if not c.startswith("_")]

            col_cfg = {
                "المشرف": st.column_config.TextColumn("👤 المشرف", width="medium"),
                "المحصل": st.column_config.TextColumn("👔 المحصل", width="medium"),
            }
            for c_name in disp_cols:
                if "%" in c_name:
                    col_cfg[c_name] = st.column_config.ProgressColumn(c_name, format="%.2f%%", min_value=0, max_value=100)
                elif "تحصيل" in c_name or "مستهدف" in c_name:
                    col_cfg[c_name] = st.column_config.NumberColumn(c_name, format="%.2f ﷼")

            st.dataframe(
                report_table.select(disp_cols).to_pandas(),
                use_container_width=True,
                hide_index=True,
                column_config=col_cfg
            )

            # تصدير إكسيل
            out_buf = io.BytesIO()
            writer = ExcelReportWriter(output_path=out_buf)
            writer.write_monthly_targets_report(
                report_table=report_table,
                months_meta=months_meta,
                stats=stats
            )
            writer.save()
            excel_bytes = out_buf.getvalue()

            ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"تقرير_التحصيل_بالشهور_{ts_str}.xlsx"

            st.download_button(
                label="📥 تحميل التقرير النهائي (Excel منسق وفاخر)",
                data=excel_bytes,
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        except Exception as e:
            st.error(f"❌ حدث خطأ أثناء إنشاء التقرير: {e}")
            st.exception(e)
