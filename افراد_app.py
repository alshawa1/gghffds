# -*- coding: utf-8 -*-
# System Individuals Module

def run_afrad_app():
    import sys
    import os
    import tempfile
    from datetime import datetime, timedelta
    import polars as pl
    import streamlit as st

    # ─── إعداد مسار المشروع وحل تعارض الموديولات ───
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    STC_DIR = os.path.join(THIS_DIR, "STC_System")
    BIZ_DIR = os.path.join(THIS_DIR, "قطاع اعمال للاتصالات")

    colliding = ['core', 'data', 'utils', 'export', 'modules', 'gui', 'pages',
                 'payment_analysis', 'powerbi_exporter']
    mods_to_del = [m for m in list(sys.modules.keys()) if m.split('.')[0] in colliding]
    for mod in mods_to_del:
        sys.modules.pop(mod, None)

    if THIS_DIR not in sys.path:
        sys.path.insert(0, THIS_DIR)
    if os.path.exists(STC_DIR) and STC_DIR not in sys.path:
        sys.path.insert(0, STC_DIR)

    try:
        from core.data_loader import load_files
        from core.utils import MAIN_PORTFOLIO, PROMISE_PAY, MAHARAH_PAY, COMPANY_PAY
        from export.excel_writer_xl import ExcelReportWriter
    except ImportError:
        if os.path.exists(STC_DIR):
            sys.path.insert(0, STC_DIR)
        from core.data_loader import load_files
        from core.utils import MAIN_PORTFOLIO, PROMISE_PAY, MAHARAH_PAY, COMPANY_PAY
        from export.excel_writer_xl import ExcelReportWriter

    # ─── إعدادات الصفحة ───

    # ════════════════════════════════════════════════════════════════════
    #  CSS كلاسيكي أنيق - وضوح تام ونصوص عالية التباين
    # ════════════════════════════════════════════════════════════════════
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');

        /* ─── القواعد العامة ─── */
        html, body, [class*="css"], .stApp {
            font-family: 'Cairo', 'Segoe UI', sans-serif !important;
            direction: RTL;
            text-align: right;
            background-color: #f8fafc !important;
            color: #0f172a !important;
        }

        .stApp {
            background-color: #f8fafc !important;
        }

        /* ─── الشريط الجانبي ─── */
        [data-testid="stSidebar"] {
            background: #ffffff !important;
            border-left: 1px solid #e2e8f0 !important;
        }
        [data-testid="stSidebar"] * {
            direction: RTL;
            text-align: right;
            color: #1e293b !important;
        }

        /* ─── شريط التنقل في Sidebar ─── */
        .stRadio > div {
            direction: RTL;
        }
        .stRadio > div > label {
            direction: RTL;
            text-align: right !important;
            font-size: 14px;
            padding: 8px 12px;
            border-radius: 8px;
            color: #334155 !important;
            transition: background 0.2s, color 0.2s;
        }
        .stRadio > div > label:hover {
            background: #f1f5f9 !important;
            color: #0f172a !important;
        }

        /* ─── الكروت والمناطق ─── */
        [data-testid="metric-container"] {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        [data-testid="metric-container"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }
        [data-testid="stMetricValue"] {
            color: #0f172a !important;
            font-weight: 900;
            font-size: 24px;
        }
        [data-testid="stMetricLabel"] {
            color: #475569 !important;
            font-size: 13px;
            font-weight: 700;
        }

        /* ─── أزرار ─── */
        .stButton > button {
            background: #ffffff !important;
            color: #1e293b !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px;
            font-weight: 700 !important;
            font-size: 14px;
            padding: 8px 20px;
            transition: all 0.2s !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }
        .stButton > button:hover {
            background: #f1f5f9 !important;
            border-color: #94a3b8 !important;
            color: #0f172a !important;
        }
        .stButton > button[kind="primary"] {
            background: #1e293b !important;
            color: #ffffff !important;
            border: none !important;
        }
        .stButton > button[kind="primary"]:hover {
            background: #0f172a !important;
            color: #ffffff !important;
        }

        /* ─── زر التحميل ─── */
        .stDownloadButton > button {
            background: #059669 !important;
            color: white !important;
            border: none !important;
            border-radius: 8px;
            font-weight: 700 !important;
            font-size: 14px;
            box-shadow: 0 2px 6px rgba(5, 150, 105, 0.2) !important;
            transition: all 0.2s !important;
        }
        .stDownloadButton > button:hover {
            background: #047857 !important;
            color: white !important;
        }

        /* ─── حقل الإدخال والقوائم ─── */
        .stTextInput input, .stSelectbox select, .stMultiSelect,
        [data-testid="stTextInput"] input {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
            color: #0f172a !important;
            direction: RTL !important;
        }
        .stTextInput input:focus, [data-testid="stTextInput"] input:focus {
            border-color: #475569 !important;
            box-shadow: 0 0 0 2px rgba(71, 85, 105, 0.15) !important;
        }

        /* ─── الخطوط الفاصلة ─── */
        hr {
            border-color: #e2e8f0 !important;
        }

        /* ─── رسائل النجاح والخطأ ─── */
        .stSuccess {
            background: #ecfdf5 !important;
            border: 1px solid #a7f3d0 !important;
            border-radius: 8px;
            color: #065f46 !important;
        }
        .stError {
            background: #fef2f2 !important;
            border: 1px solid #fecaca !important;
            border-radius: 8px;
            color: #991b1b !important;
        }
        .stInfo {
            background: #f8fafc !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px;
            color: #1e293b !important;
        }
        .stWarning {
            background: #fffbeb !important;
            border: 1px solid #fde68a !important;
            border-radius: 8px;
            color: #92400e !important;
        }

        /* ─── عنوان بطاقة الـ AI ─── */
        .ai-header-card {
            background: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 14px;
            padding: 20px 24px;
            margin-bottom: 20px;
            direction: RTL;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        }

        /* ─── شريط الفصل الكلاسيكي ─── */
        .purple-divider {
            height: 1px;
            background: #cbd5e1;
            margin: 14px 0;
        }

        /* ─── DataFrames ─── */
        [data-testid="stDataFrame"] {
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #cbd5e1;
            background: #ffffff;
        }

        /* ─── File Uploader ─── */
        [data-testid="stFileUploader"] {
            background: #ffffff !important;
            border: 1px dashed #94a3b8 !important;
            border-radius: 10px !important;
            padding: 16px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.02);
            transition: border-color 0.2s, background 0.2s;
        }
        [data-testid="stFileUploader"]:hover {
            border-color: #475569 !important;
            background: #f8fafc !important;
        }

        /* ─── RTL كامل ─── */
        .stMarkdown, .stSelectbox, .stFileUploader, .stButton,
        .stMultiSelect, .stDateInput, .stTextArea, p, label, h1, h2, h3, h4, h5 {
            direction: RTL;
            text-align: right !important;
            color: #0f172a;
        }
        </style>
    """, unsafe_allow_html=True)





    # ════════════════════════════════════════════════════════════════════
    #  تعريف الموديولات
    # ════════════════════════════════════════════════════════════════════
    MODULES = {
        "ai_copilot": {
            "name": "🤖 AI Operations Copilot",
            "desc": "مساعد الذكاء الاصطناعي لقسم العمليات. يفهم بياناتك، يحللها، ويجيب عن أي سؤال باللغة الطبيعية.",
            "id": 99,
            "files": [
                {"key": "portfolio", "label": "ملف المحفظة (.xlsx)", "required": True},
                {"key": "payments", "label": "ملف السدادات (.xlsx) - اختياري", "required": False}
            ]
        },
        "rotation": {
            "name": "🔄 السحب والتدوير",
            "desc": "سحب جميع عملاء محصل معين وإعادة توزيعهم بالتساوي على باقي المحصليين التابعين لنفس المشرف، مع الحفاظ على جميع مديونيات العميل الواحد لدى نفس المحصل الجديد.",
            "id": 6,
            "files": [
                {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx)", "required": True}
            ]
        },
        "contact": {
            "name": "📞 التوصل وعدم التوصل",
            "desc": "تحليل وتصنيف العملاء بناءً على حالات التواصل الرئيسية والفرعية والمتابعة للوصول إلى التصنيف النهائي وتتبع محاولات الاتصال.",
            "id": 2,
            "files": [
                {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx)", "required": True}
            ]
        },
        "targets": {
            "name": "🎯 العملاء المستهدفة",
            "desc": "تحديد العملاء ذوي الأولوية المرتفعة بناءً على متبقي السداد الموثق ونسب التغطية والتوجيهات المعتمدة.",
            "id": 7,
            "files": [
                {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx)", "required": True}
            ]
        },
        "neglect": {
            "name": "⏰ الإهمال والمتابعات",
            "desc": "تحليل وتصنيف حالات الإهمال وتحديد العملاء غير المتابعين بناءً على أيام المتابعة وآخر محاولة تواصل.",
            "id": 3,
            "files": [
                {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx)", "required": True}
            ]
        },
        "errors": {
            "name": "🔴 أخطاء النظام والوعود",
            "desc": "كشف وتوثيق الأخطاء في بيانات المحفظة والمطابقة مع وعود السداد النشطة أو المنتهية لتصحيح حالة العميل.",
            "id": 1,
            "files": [
                {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx)", "required": True},
                {"key": "promise", "label": "ملف وعود السداد (.xlsx) - اختياري", "required": False}
            ]
        },
        "balancing": {
            "name": "⚖️ سحب وتوزيع المحافظ",
            "desc": "إعادة توزيع العملاء من محافظ مصدر على محافظ هدف بخوارزمية ذكية تحقق توازناً مزدوجاً في عدد العملاء وإجمالي متبقي السداد بين جميع المحصلين المستهدفين.",
            "id": 8,
            "files": [
                {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx)", "required": True}
            ]
        },
        "operations": {
            "name": "📊 مركز تقارير العمليات",
            "desc": "تقرير التغطية والتحصيل ونسب الإنجاز مقارنة بالمستهدف لكل محصل ومشرف (يومي / أسبوعي / شهري) بربط رقم المديونية وتاريخ المتابعة.",
            "id": 9,
            "files": [
                {"key": "portfolio", "label": "ملف المحفظة (.xlsx) *", "required": True},
                {"key": "payments", "label": "ملف التحصيل / السدادات (.xlsx) (اختياري للتحصيل)", "required": False}
            ]
        },
        "portfolio_analytics": {
            "name": "📊 التحليل الاستراتيجي وعمر الدين",
            "desc": "تحليل استراتيجي شامل: نسب التوصل، عمر الدين المستخرج من سنة إنتهاء الحساب، متبقي سداد موثق، أداء المشرفين، وأفضل وأسوأ 10 محصلين.",
            "id": 14,
            "files": [
                {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx) *", "required": True},
                {"key": "payments", "label": "ملف التحصيل / السدادات (.xlsx) - اختياري", "required": False}
            ]
        },
        "electronic": {
            "name": "💻 التحصيل الإلكتروني",
            "desc": "تحليل أداء التحصيل الإلكتروني وعرض نسب التغطية والتوصل مع إمكانية التصفية حسب الفرع والمشرف وبناء ملخص بناءً على الـ Segment ونوع الخدمة.",
            "id": 10,
            "files": [
                {"key": "portfolio", "label": "ملف التحصيل الإلكتروني (الكتروني.xlsx)", "required": True}
            ]
        },
        "daily_followup": {
            "name": "📈 التقرير اليومي — فولو اب",
            "desc": "ربط المحفظة المجمعة × المحفظة الموزعة × السدادات. إضافة كولوم المحافظ لشيت السدادات، وتوليد شارتس وسلايسرز وجدول ملخص أداء المحافظ وأفضل المشرفين والمحصلين.",
            "id": 999,
            "files": [
                {"key": "master", "label": "ملف المحفظة المجمعة (.xlsx) *", "required": True},
                {"key": "portfolio", "label": "ملف المحفظة الموزعة (.xlsx) *", "required": True},
                {"key": "payments", "label": "ملف شيت السدادات (.xlsx) *", "required": True}
            ]
        },
        "fill_reports": {
            "name": "📝 ملء التقارير والقوالب",
            "desc": "تعبئة القوالب والشيتات الفارغة تلقائياً من شيت المحفظة مع إمكانية التصفية بالمشرفين والمحافظ ومطابقة الأعمدة بمرونة تامة.",
            "id": 1000,
            "files": []
        },
        "send_campaigns": {
            "name": "📢 برنامج الإرسال الذكي",
            "desc": "تحديد واستهداف أنسب العملاء تحصيلاً لحملات الرسائل النصية والبريد الإلكتروني، مع تجميع المديونيات برقم الهوية وتعبئة فورمة الإرسال.",
            "id": 1001,
            "files": []
        },
        "collector_rotation": {
            "name": "🔄 تدوير المحصلين الذكي",
            "desc": "تدوير وتبديل جميع عملاء المحصلين بتوازن كامل مبني على متبقي السداد الموثق، مع خيار التدوير تحت نفس المشرف وإضافة كولوم المحصل واليوزر الجديد.",
            "id": 1002,
            "files": []
        },
        "monthly_targets": {
            "name": "📅 التحصيل بالشهور بالمستهدف",
            "desc": "مقارنة تحصيل كل محصل ومشرف شهر بشهر مع المستهدف المالي لكل شهر ونسب الإنجاز بربط رقم المديونية وتاريخ السداد.",
            "id": 12,
            "files": [
                {"key": "portfolio", "label": "ملف المحفظة (.xlsx) *", "required": True},
                {"key": "payments", "label": "ملف التحصيل / السدادات (.xlsx) *", "required": True}
            ]
        }
    }


    # ════════════════════════════════════════════════════════════════════
    #  دوال مساعدة
    # ════════════════════════════════════════════════════════════════════
    @st.cache_data(show_spinner="⏳ جارٍ قراءة وتحميل البيانات بأقصى سرعة...")
    def read_excel_calamine(file_path: str) -> pl.DataFrame:
        try:
            return pl.read_excel(file_path, engine="calamine").select([
                pl.col(c).cast(pl.String, strict=False).fill_null("").str.strip_chars().alias(c)
                for c in pl.read_excel(file_path, engine="calamine").columns
            ])
        except Exception as e:
            from python_calamine import CalamineWorkbook
            wb = CalamineWorkbook.from_path(file_path)
            sheet = wb.get_sheet_by_name(wb.sheet_names[0])
            data = sheet.to_python()
            if not data:
                return pl.DataFrame()
            headers = []
            seen = {}
            for i, h in enumerate(data[0]):
                h_str = str(h).strip() if h is not None else f"Column_{i}"
                if not h_str:
                    h_str = f"Column_{i}"
                if h_str in seen:
                    seen[h_str] += 1
                    h_str = f"{h_str}_{seen[h_str]}"
                else:
                    seen[h_str] = 0
                headers.append(h_str)
            records = data[1:]
            str_records = [
                [str(cell) if cell is not None else "" for cell in row]
                for row in records
            ]
            return pl.DataFrame(str_records, schema=headers, orient="row")


    @st.cache_data
    def scan_portfolio_for_balancing(file_path):
        try:
            df = read_excel_calamine(file_path)
            from modules.module8_balancing import PortfolioBalancingModule
            portfolios = PortfolioBalancingModule.get_portfolios(df)
            collector_map = PortfolioBalancingModule.get_collectors_per_portfolio(df)
            return portfolios, collector_map
        except Exception as e:
            st.error(f"حدث خطأ أثناء فحص الملف: {e}")
            return [], {}


    @st.cache_data
    def scan_portfolio_for_operations(file_path):
        try:
            df = read_excel_calamine(file_path)
            from modules.module9_operations_report import OperationsReportModule
            opts = OperationsReportModule.get_filter_options(df)
            dates_info = OperationsReportModule.detect_available_dates(df)
            opts["dates_info"] = dates_info
            return opts
        except Exception as e:
            st.error(f"حدث خطأ أثناء فحص ملف العمليات: {e}")
            return {}


    @st.cache_data
    def scan_portfolio_for_targeting(file_path):
        try:
            df = read_excel_calamine(file_path)
            from modules.module11_targeting_report import TargetingReportModule
            return TargetingReportModule.get_supervisors_and_collectors(df)
        except Exception as e:
            st.error(f"حدث خطأ أثناء فحص ملف المحفظة للاستهداف: {e}")
            return {}


    @st.cache_data
    def scan_portfolio_for_electronic(file_path):
        try:
            df = read_excel_calamine(file_path)
            from modules.module9_operations_report import _detect
            branch_col = _detect(df, ["الفرع", "branch"])
            sup_col = _detect(df, ["المشرف", "supervisor"])
            branches = df[branch_col].drop_nulls().unique().to_list() if branch_col else []
            supervisors = df[sup_col].drop_nulls().unique().to_list() if sup_col else []
            return {"branches": sorted([str(x) for x in branches if str(x).strip()]), 
                    "supervisors": sorted([str(x) for x in supervisors if str(x).strip()])}
        except Exception as e:
            st.error(f"حدث خطأ أثناء فحص ملف التحصيل الإلكتروني: {e}")
            return {}


    @st.cache_data
    def scan_portfolio_for_rotation(file_path):
        try:
            df = read_excel_calamine(file_path)
            from modules.module6b_rotation import PortfolioRotationModule
            supervisors = PortfolioRotationModule.get_supervisors(df)
            mapping = {}
            for sup in supervisors:
                mapping[sup] = PortfolioRotationModule.get_collectors_for_supervisor(df, sup)
            main_statuses = PortfolioRotationModule.get_main_statuses(df)
            return {"mapping": mapping, "main_statuses": main_statuses}
        except Exception as e:
            st.error(f"حدث خطأ أثناء فحص الملف: {e}")
            return None


    @st.cache_data
    def load_portfolio_df(file_path):
        """تحميل إطار البيانات من ملف المحفظة"""
        return read_excel_calamine(file_path)


    def detect_supervisor_column(df: pl.DataFrame) -> str | None:
        """اكتشاف عمود المشرف تلقائياً"""
        candidates = ["اسم المشرف", "المشرف", "مشرف", "Supervisor", "supervisor"]
        for c in candidates:
            if c in df.columns:
                return c
        # fuzzy fallback
        for col in df.columns:
            if "مشرف" in col or "supervisor" in col.lower():
                return col
        return None


    # ════════════════════════════════════════════════════════════════════
    #  الشريط الجانبي - قائمة البرامج المتاحة
    # ════════════════════════════════════════════════════════════════════
    with st.sidebar:
        st.markdown("<p style='color:#1e3a8a; font-weight:800; font-size:14px; text-align:right; margin-bottom:8px;'>⚙️ برامج قطاع الأفراد:</p>", unsafe_allow_html=True)

        selected_key = st.radio(
            label="اختر البرنامج:",
            options=list(MODULES.keys()),
            format_func=lambda k: MODULES[k]["name"],
            label_visibility="collapsed"
        )

        st.markdown("<div class='purple-divider'></div>", unsafe_allow_html=True)


    # ════════════════════════════════════════════════════════════════════
    #  الرأس الرئيسي للصفحة
    # ════════════════════════════════════════════════════════════════════
    module_info = MODULES[selected_key]

    # Header بطاقة عليا
    if selected_key == "ai_copilot":
        st.markdown("""
        <div class="ai-header-card">
            <div style="display:flex; align-items:center; gap:16px; flex-direction:row-reverse;">
                <div style="font-size:44px; line-height:1;">🤖</div>
                <div>
                    <div style="font-size:24px; font-weight:900; color:#0f172a;">
                        AI Operations Copilot
                    </div>
                    <div style="color:#475569; font-size:14px; font-weight:600; margin-top:4px;">
                        مساعد الذكاء الاصطناعي لقسم العمليات — يفهم بياناتك ويجيب عن أي سؤال
                    </div>
                    <div class="purple-divider" style="margin:10px 0 0 0; width:180px;"></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="padding: 16px 0 8px 0;">
            <h2 style="color:#0f172a; font-weight:900; margin-bottom:4px;">{module_info['name']}</h2>
            <div class="purple-divider" style="width:120px;"></div>
        </div>
        """, unsafe_allow_html=True)
        st.info(module_info["desc"])


    # ════════════════════════════════════════════════════════════════════
    #  🤖 واجهة AI Operations Copilot
    # ════════════════════════════════════════════════════════════════════
    if selected_key == "ai_copilot":

        # تهيئة الحالة
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if "ai_portfolio_df" not in st.session_state:
            st.session_state.ai_portfolio_df = None
        if "ai_payments_df" not in st.session_state:
            st.session_state.ai_payments_df = None
        if "ai_supervisors" not in st.session_state:
            st.session_state.ai_supervisors = []
        if "ai_selected_sups" not in st.session_state:
            st.session_state.ai_selected_sups = []

        # ─── قسم رفع الملفات ───
        st.markdown("#### 📂 رفع الملفات")
        col_p, col_pay = st.columns(2)

        with col_p:
            port_file = st.file_uploader("ملف المحفظة (.xlsx) *", type=["xlsx", "xls"], key="ai_port_file")
        with col_pay:
            pay_file = st.file_uploader("ملف السدادات (.xlsx) - اختياري", type=["xlsx", "xls"], key="ai_pay_file")

        if port_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                tmp.write(port_file.getbuffer())
                tmp_path = tmp.name
            try:
                df_port = load_portfolio_df(tmp_path)
                st.session_state.ai_portfolio_df = df_port
                sup_col = detect_supervisor_column(df_port)
                if sup_col:
                    all_sups = sorted(df_port[sup_col].cast(pl.String).drop_nulls().unique().to_list())
                    st.session_state.ai_supervisors = all_sups
                else:
                    st.session_state.ai_supervisors = []
                st.success(f"✅ تم تحميل المحفظة — {len(df_port):,} عميل | {len(df_port.columns)} عمود")
            except Exception as e:
                st.error(f"خطأ في قراءة ملف المحفظة: {e}")
            finally:
                try:
                    os.unlink(tmp_path)
                except:
                    pass

        if pay_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                tmp.write(pay_file.getbuffer())
                tmp_path = tmp.name
            try:
                df_pay = load_portfolio_df(tmp_path)
                st.session_state.ai_payments_df = df_pay
                st.success(f"✅ تم تحميل السدادات — {len(df_pay):,} صف")
            except Exception as e:
                st.error(f"خطأ في قراءة ملف السدادات: {e}")
            finally:
                try:
                    os.unlink(tmp_path)
                except:
                    pass

        # ─── فلتر المشرفين ───
        if st.session_state.ai_portfolio_df is not None:
            st.markdown("<div class='purple-divider'></div>", unsafe_allow_html=True)
            st.markdown("#### 👥 تحديد نطاق العمل (المشرفين)")
            st.caption("اختر المشرفين الذين تريد أن يعمل الـ AI على بياناتهم. اتركها فارغة للعمل على الكل.")

            sups_all = st.session_state.ai_supervisors
            if sups_all:
                selected_sups = st.multiselect(
                    "اختر المشرفين:",
                    options=sups_all,
                    default=st.session_state.ai_selected_sups,
                    key="sup_multiselect",
                    label_visibility="collapsed"
                )
                st.session_state.ai_selected_sups = selected_sups
                if selected_sups:
                    st.info(f"🔍 العمل على: {', '.join(selected_sups)} ({len(selected_sups)} مشرف)")
                else:
                    st.info("🌐 العمل على المحفظة الكاملة (جميع المشرفين)")
            else:
                st.warning("⚠️ لم يتم اكتشاف عمود المشرفين تلقائياً. سيعمل الـ AI على كامل المحفظة.")

            # ─── واجهة الدردشة ───
            st.markdown("<div class='purple-divider'></div>", unsafe_allow_html=True)
            st.markdown("#### 🧠 تحدث مع AI Operations Copilot")

            # عرض رسائل المحادثة
            chat_container = st.container()
            with chat_container:
                if not st.session_state.chat_history:
                    st.markdown("""
                    <div class="chat-bubble-ai">
                        <strong>🤖 مرحباً!</strong> أنا AI Operations Copilot الخاص بـ STC.<br><br>
                        يمكنني الإجابة عن أي سؤال حول محفظتك. جرب مثلاً:<br>
                        • <em>كم نسبة التغطية اليوم؟</em><br>
                        • <em>كم عدد العملاء الإجمالي؟</em><br>
                        • <em>من أفضل مشرف في المحفظة؟</em><br>
                        • <em>ما توصيتك لتحسين الأداء؟</em><br>
                        • <em>كم إجمالي متبقي السداد؟</em>
                    </div>
                    """, unsafe_allow_html=True)

                for msg in st.session_state.chat_history:
                    if msg["role"] == "user":
                        st.markdown(f"""
                        <div class="chat-bubble-user">
                            <strong>👤 أنت:</strong><br>{msg['content']}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="chat-bubble-ai">
                            <strong>🤖 AI Copilot:</strong><br>{msg['content']}
                        </div>
                        """, unsafe_allow_html=True)

            # حقل الإدخال
            col_q, col_send = st.columns([5, 1])
            with col_q:
                user_question = st.text_input(
                    "اسأل الـ AI...",
                    placeholder="مثال: كم نسبة التغطية اليوم؟",
                    key="ai_question",
                    label_visibility="collapsed"
                )
            with col_send:
                send_btn = st.button("✉️ إرسال", use_container_width=True)

            col_clr, _ = st.columns([1, 4])
            with col_clr:
                if st.button("🗑️ مسح المحادثة", use_container_width=True):
                    st.session_state.chat_history = []
                    st.rerun()

            if (send_btn or user_question) and user_question and user_question.strip():
                if send_btn or True:
                    # حفظ سؤال المستخدم
                    st.session_state.chat_history.append({"role": "user", "content": user_question})

                    # تشغيل الـ AI
                    with st.spinner("🤖 AI يحلل بياناتك..."):
                        try:
                            from core.knowledge_base import CopilotKnowledgeBase
                            from core.ai_copilot import AIOperationsCopilot

                            kb = CopilotKnowledgeBase()
                            copilot = AIOperationsCopilot(
                                portfolio_df=st.session_state.ai_portfolio_df,
                                payments_df=st.session_state.ai_payments_df,
                                kb=kb
                            )
                            answer = copilot.ask(
                                question=user_question,
                                selected_supervisors=st.session_state.ai_selected_sups or None
                            )
                        except Exception as e:
                            answer = f"⚠️ حدث خطأ أثناء تحليل البيانات: {e}"

                    st.session_state.chat_history.append({"role": "ai", "content": answer})
                    st.rerun()

        else:
            st.markdown("""
            <div style="
                text-align:center;
                padding: 60px 20px;
                color: #64748b;
                border: 2px dashed #cbd5e1;
                border-radius: 12px;
                background: #ffffff;
                margin-top: 24px;
            ">
                <div style="font-size:52px; margin-bottom:12px;">📂</div>
                <div style="font-size:18px; color:#0f172a; font-weight:800;">
                    يرجى رفع ملف المحفظة للبدء
                </div>
                <div style="font-size:14px; color:#64748b; margin-top:6px; font-weight:600;">
                    سيقوم المساعد الذكي بتحليل البيانات فور رفع الملف
                </div>
            </div>
            """, unsafe_allow_html=True)


    elif selected_key == "daily_followup":
        import re
        daily_page = os.path.join(THIS_DIR, "قطاع اعمال للاتصالات", "pages", "09_التقرير_اليومي_فولو_اب.py")
        with open(daily_page, "r", encoding="utf-8") as f:
            code = f.read()
        code = re.sub(r"st\.set_page_config\([^)]*\)", "pass", code)
        exec(compile(code, daily_page, 'exec'), {'__name__': '__main__', '__file__': daily_page})

    elif selected_key == "fill_reports":
        import re
        fill_page = os.path.join(THIS_DIR, "قطاع اعمال للاتصالات", "pages", "10_ملء_التقارير.py")
        with open(fill_page, "r", encoding="utf-8") as f:
            code = f.read()
        code = re.sub(r"st\.set_page_config\([^)]*\)", "pass", code)
        exec(compile(code, fill_page, 'exec'), {'__name__': '__main__', '__file__': fill_page})

    elif selected_key == "send_campaigns":
        import re
        send_page = os.path.join(THIS_DIR, "قطاع اعمال للاتصالات", "pages", "11_برنامج_الارسال.py")
        with open(send_page, "r", encoding="utf-8") as f:
            code = f.read()
        code = re.sub(r"st\.set_page_config\([^)]*\)", "pass", code)
        exec(compile(code, send_page, 'exec'), {'__name__': '__main__', '__file__': send_page})

    elif selected_key == "collector_rotation":
        import re
        rot_page = os.path.join(THIS_DIR, "قطاع اعمال للاتصالات", "pages", "13_تدوير_المحصلين.py")
        with open(rot_page, "r", encoding="utf-8") as f:
            code = f.read()
        code = re.sub(r"st\.set_page_config\([^)]*\)", "pass", code)
        exec(compile(code, rot_page, 'exec'), {'__name__': '__main__', '__file__': rot_page})

    # ════════════════════════════════════════════════════════════════════
    #  واجهة باقي الموديولات (الموديولات الأصلية كما هي)
    # ════════════════════════════════════════════════════════════════════
    else:
        # ─── قسم رفع الملفات ───
        st.markdown("#### 📂 رفع الملفات المطلوبة")
        uploaded_files = {}

        cols_upload = st.columns(len(module_info["files"]))
        for i, fspec in enumerate(module_info["files"]):
            with cols_upload[i]:
                uploaded_files[fspec["key"]] = st.file_uploader(
                    label=fspec["label"],
                    type=["xlsx", "xls"],
                    key=f"{selected_key}_{fspec['key']}"
                )

        # ─── معطيات السحب والتدوير ───
        rotation_params = {}
        if selected_key == "rotation" and uploaded_files.get("portfolio"):
            portfolio_file = uploaded_files["portfolio"]
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_scan:
                tmp_scan.write(portfolio_file.getbuffer())
                tmp_scan_path = tmp_scan.name
            try:
                scan_res = scan_portfolio_for_rotation(tmp_scan_path)
                if scan_res:
                    if isinstance(scan_res, dict) and "mapping" in scan_res:
                        mapping = scan_res["mapping"]
                        available_statuses = scan_res.get("main_statuses", [])
                    else:
                        mapping = scan_res
                        available_statuses = []

                    all_sups = sorted(list(mapping.keys()))
                    # كل المحصلين في الملف
                    all_collectors_map = {c: sup for sup, cols in mapping.items() for c in cols}

                    st.markdown("#### 🔄 إعدادات السحب وإعادة التوزيع")

                    # ── خطوة 1: اختيار مشرف/مشرفين ──
                    st.markdown("##### 1️⃣ اختر المشرف / المشرفين:")
                    selected_sups = st.multiselect(
                        "اختر مشرف واحد أو أكثر:",
                        options=all_sups,
                        help="يمكنك اختيار أكثر من مشرف — المحصلون المتاحون للسحب سيكونون من المشرفين المختارين"
                    )

                    # ── خطوة 2: المحصلون المسحوبون من المشرفين المختارين ──
                    if selected_sups:
                        pool_for_withdraw = sorted(list({c for sup in selected_sups for c in mapping.get(sup, [])}))
                        st.markdown("##### 2️⃣ اختر المحصل/المحصلين المراد **سحب** محافظهم:")
                        selected_cols = st.multiselect(
                            "المحصلون المتاحون للسحب (من المشرفين المختارين):",
                            options=pool_for_withdraw,
                            help="اختر محصل واحد أو أكثر لسحب محافظهم"
                        )
                    else:
                        st.multiselect("2️⃣ اختر المحصل/المحصلين المراد سحب محافظهم:", ["-- اختر المشرف أولاً --"], disabled=True)
                        selected_cols = []

                    # ── خطوة 3: المحصلون المستقبلون ──
                    if selected_sups and selected_cols:
                        withdrawn_set = set(selected_cols)

                        # كل المحصلين في الملف ما عدا المسحوبين — مجمّعين حسب المشرف
                        st.markdown("##### 3️⃣ اختر المحصلين **المستقبلين** (لنقل العملاء إليهم):")

                        # عرض المحصلين مجمعين بالمشرف لوضوح أكثر
                        receiver_by_sup = {}
                        for sup, cols in mapping.items():
                            available = [c for c in cols if c not in withdrawn_set]
                            if available:
                                receiver_by_sup[sup] = available

                        # بناء options مع label واضح
                        all_receivers = sorted(list({c for cols in receiver_by_sup.values() for c in cols}))

                        # default = محصلو نفس المشرفين المختارين (غير المسحوبين)
                        default_receivers = sorted(list({
                            c for sup in selected_sups
                            for c in mapping.get(sup, [])
                            if c not in withdrawn_set
                        }))

                        target_cols_sel = st.multiselect(
                            "اختر المحصلين المستقبلين (من أي مشرف — اتركه فارغاً للتوزيع التلقائي على باقي محصلي نفس المشرف):",
                            options=all_receivers,
                            default=default_receivers,
                            help="يمكنك اختيار محصلين من نفس المشرف أو مشرف مختلف تماماً"
                        )

                        # ── معلومات إضافية: من أي مشرف كل مستقبل ──
                        if target_cols_sel:
                            info_lines = []
                            for c in target_cols_sel:
                                sup_of_c = all_collectors_map.get(c, "غير معروف")
                                info_lines.append(f"**{c}** (مشرفه: {sup_of_c})")
                            with st.expander("📋 تفاصيل المحصلين المستقبلين"):
                                st.markdown(" — ".join(info_lines))

                        dest_count = len(target_cols_sel) if target_cols_sel else len(default_receivers)
                        withdrawn_names_str = " | ".join(selected_cols)

                        # ── خطوة 4: تحديد الحالات الرئيسية المراد توزيعها ──
                        selected_statuses = None
                        if available_statuses:
                            st.markdown("##### 4️⃣ تحديد الحالات الرئيسية المراد توزيعها:")
                            selected_statuses = st.multiselect(
                                "اختر الحالات الرئيسية المراد توزيعها على المحصلين المستقبلين (اتركه فارغاً لتوزيع كافة الحالات):",
                                options=available_statuses,
                                default=available_statuses,
                                help="الحالات المحددة ستوزع بالتساوي على المحصلين المستقبلين. باقي الحالات غير المحددة ستتحول تلقائياً إلى كود التحصيل الإلكتروني test.t مع ضمان توحيد العميل بالكامل وعدم تكراره بين محصلين."
                            )
                            if selected_statuses and len(selected_statuses) < len(available_statuses):
                                unselected = [s for s in available_statuses if s not in selected_statuses]
                                st.warning(f"⚡ الحالات التي ستذهب لكود التحصيل الإلكتروني (`test.t`): **{', '.join(unselected)}**")
                            elif not selected_statuses:
                                st.info("ℹ️ تم اختيار توزيع كامل الحالات على المحصلين المستقبلين.")

                        if dest_count == 0:
                            st.error("⚠️ يرجى تحديد محصل مستقبل واحد على الأقل لنقل العملاء إليه!")
                        else:
                            smart_check = st.checkbox(
                                "🚨 تفعيل التوجيه والتعيين الذكي بحسب حالة العميل (رصيد 0 ⬅️ opertaions / سلبي ⬅️ test / إيجابي ⬅️ المحصل الجديد)",
                                value=False,
                                help="في حال عدم تفعيل الخيار: يتم توزيع كامل عملاء المحصل بشكل طبيعي دون تطبيق شروط opertaions أو test."
                            )
                            if smart_check:
                                st.info(
                                    "💡 **التوجيه والتعيين الذكي مفعّل:**\n"
                                    "- 🔵 **عملاء متبقي سداد صفر أو أقل:** يُسند المحصل الجديد واليوزر كـ `opertaions`.\n"
                                    "- 🔴 **العملاء السلبيون (عدم توصل / مسجون / متوفي / رافض / لايرد / مغلق ... إلخ):** يُسند اليوزر الجديد كـ `test`.\n"
                                    "- 🟢 **العملاء الإيجابيون:** يُوزعون بالتساوي على المحصلين المستقبلين وتحديد يوزرهم وتحديث مشرفهم الجديد تلقائياً."
                                )
                            st.success(
                                f"✅ سيتم سحب عملاء **'{withdrawn_names_str}'** "
                                f"({len(selected_cols)} محصلين) وتوزيعهم على "
                                f"**{dest_count} محصلين مستقبلين**."
                            )
                            # supervisor = أول مشرف مختار (للـ fallback في module)
                            rotation_params["supervisor"] = selected_sups[0]
                            rotation_params["collector"] = selected_cols
                            rotation_params["target_collectors"] = target_cols_sel if target_cols_sel else None
                            rotation_params["smart_assignment"] = smart_check
                            rotation_params["selected_main_statuses"] = selected_statuses if (selected_statuses and len(selected_statuses) < len(available_statuses)) else None
            finally:
                try:
                    os.unlink(tmp_scan_path)
                except:
                    pass

        # ─── واجهة سحب وتوزيع المحافظ ───
        balancing_params = {}
        source_ports: list = []
        target_ports: list = []
        if selected_key == "balancing" and uploaded_files.get("portfolio"):
            portfolio_file = uploaded_files["portfolio"]
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_scan:
                tmp_scan.write(portfolio_file.getbuffer())
                tmp_scan_path = tmp_scan.name
            try:
                portfolios, collector_map = scan_portfolio_for_balancing(tmp_scan_path)
                if portfolios:
                    st.markdown("#### ⚖️ تحديد المحافظ")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("المحافظ المصدر (السحب منها):")
                        source_ports = st.multiselect(
                            label="اختر محفظة أو أكثر لسحب عملائها:",
                            options=portfolios,
                            key="bal_source",
                            label_visibility="collapsed"
                        )
                        if source_ports:
                            total_source_col = sum(len(collector_map.get(p, [])) for p in source_ports)
                            st.info(f"👥 عدد المحصلين في المحافظ المصدر: **{total_source_col}**")
                    with c2:
                        st.markdown("المحافظ الهدف (التوزيع عليها):")
                        available_targets = [p for p in portfolios if p not in (source_ports or [])]
                        target_ports = st.multiselect(
                            label="اختر محفظة أو أكثر للتوزيع عليها:",
                            options=available_targets,
                            key="bal_target",
                            label_visibility="collapsed"
                        )
                        if target_ports:
                            total_target_col = sum(len(collector_map.get(p, [])) for p in target_ports)
                            st.info(f"👥 عدد المحصلين في المحافظ الهدف: **{total_target_col}**")
                    if source_ports:
                        if target_ports:
                            overlap = set(source_ports) & set(target_ports)
                            if overlap:
                                st.error(f"⚠️ لا يمكن أن تكون المحفظة مصدراً وهدفاً في نفس الوقت: {', '.join(overlap)}")
                            else:
                                st.success(f"✅ سيتم سحب عملاء **{' | '.join(source_ports)}** وتوزيعهم على محصلي **{' | '.join(target_ports)}**.")
                        else:
                            st.success(f"✅ سيتم سحب وتوزيع عملاء **{' | '.join(source_ports)}** بالتساوي داخل كل محفظة.")
                        withdraw_all_check = st.checkbox(
                            "🚨 سحب كامل عملاء المحفظة المصدر (100%) وتوزيعهم بالكامل على باقي المحافظ",
                            value=False,
                            help="عند تفعيل هذا الخيار، سيتم تفريغ المحفظة المصدر بنسبة 100% وإعادة توزيع كافة عملائها بالتساوي على باقي المحافظ/المحصلين"
                        )

                        with st.expander("⚙️ إعدادات وتصفيات إضافية (اختياري — لا تحتاج لتعديلها مع التوازن التلقائي)", expanded=False):
                            col_a, col_b, col_c = st.columns(3)
                            with col_a:
                                max_cnt_diff = st.number_input(
                                    "أقصى تفاوت في عدد العملاء:",
                                    min_value=5, max_value=200, value=35, step=5,
                                    help="أقصى فرق مسموح به بين أعلى محصل وأقل محصل في عدد العملاء"
                                )
                            with col_b:
                                max_bal_diff = st.number_input(
                                    "أقصى تفاوت في متبقي السداد:",
                                    min_value=10000, max_value=500000, value=80000, step=5000,
                                    help="أقصى فرق مسموح به بين أعلى محصل وأقل محصل في متبقي السداد"
                                )
                            with col_c:
                                min_customers_col = st.number_input(
                                    "الحد الأدنى لعملاء المحصل:",
                                    min_value=0, max_value=500, value=0, step=10,
                                    help="صفر = بلا حد أدنى (التوازن الدقيق على متوسط المحفظة تلقائياً)"
                                )

                            if min_customers_col > 0:
                                st.info(f"🛡️ **حماية وتبادل ذكي**: لا ينزل أي محصل تحت **{min_customers_col}** عميل.")

                        balancing_params["source"] = source_ports
                        balancing_params["target"] = target_ports if target_ports else None
                        balancing_params["max_count_diff"] = max_cnt_diff
                        balancing_params["max_bal_diff"] = max_bal_diff
                        balancing_params["min_per_col"] = min_customers_col
                        balancing_params["withdraw_all"] = withdraw_all_check
            finally:
                try:
                    os.unlink(tmp_scan_path)
                except:
                    pass

        # ─── واجهة مركز تقارير العمليات ───
        ops_params = {}
        if selected_key == "operations" and uploaded_files.get("portfolio"):
            portfolio_file = uploaded_files["portfolio"]
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_scan:
                tmp_scan.write(portfolio_file.getbuffer())
                tmp_scan_path = tmp_scan.name
            try:
                filter_options = scan_portfolio_for_operations(tmp_scan_path)
                sup_col_map = scan_portfolio_for_targeting(tmp_scan_path)
                if filter_options:
                    st.markdown("---")
                    st.markdown("### 🏢 إعدادات تقرير العمليات (التغطية والتحصيل)")

                    dates_info = filter_options.get("dates_info", {})
                    top_date_str = dates_info.get("top_date") or dates_info.get("latest_date")
                    try:
                        top_date_obj = datetime.strptime(top_date_str, "%Y-%m-%d").date() if top_date_str else datetime.today().date()
                    except:
                        top_date_obj = datetime.today().date()

                    if top_date_str:
                        st.info(f"💡 تم رصد **{len(dates_info.get('dates', []))}** تاريخ متابعة في المحفظة. اليوم الأكثر نشاطاً المقترح: **{top_date_str}**")

                    # 1. الفترة الزمنية
                    col_mode, _ = st.columns([3, 1])
                    with col_mode:
                        rep_type = st.radio(
                            "اختر نوع الفترة الزمنية للتقرير:",
                            options=["📅 Daily Report (تقرير يومي)", "🗓 Weekly Report (تقرير أسبوعي)", "📆 Monthly Report (تقرير شهري)"],
                            index=0,
                            horizontal=True
                        )

                    st.markdown("##### ⏱️ إعدادات الفترة الزمنية (بناءً على تاريخ المتابعة في المحفظة)")
                    if "Daily" in rep_type:
                        ops_params["report_mode"] = "daily"
                        d_val = st.date_input("تاريخ التقرير اليومي:", value=top_date_obj)
                        ops_params["target_date"] = d_val.strftime("%Y-%m-%d")
                    elif "Weekly" in rep_type:
                        ops_params["report_mode"] = "weekly"
                        w_cols = st.columns(2)
                        with w_cols[0]:
                            s_val = st.date_input("تاريخ بداية الفترة:", value=top_date_obj - timedelta(days=6))
                        with w_cols[1]:
                            e_val = st.date_input("تاريخ نهاية الفترة:", value=top_date_obj)
                        ops_params["start_date"] = s_val.strftime("%Y-%m-%d")
                        ops_params["end_date"] = e_val.strftime("%Y-%m-%d")
                    elif "Monthly" in rep_type:
                        ops_params["report_mode"] = "monthly"
                        m_cols = st.columns(2)
                        default_y = top_date_obj.year
                        default_m = top_date_obj.month
                        with m_cols[0]:
                            m_val = st.selectbox("الشهر:", options=list(range(1, 13)), index=default_m - 1)
                        with m_cols[1]:
                            y_val = st.selectbox("السنة:", options=list(range(2023, 2031)),
                                                 index=list(range(2023, 2031)).index(default_y) if default_y in range(2023, 2031) else 0)
                        ops_params["month"] = m_val
                        ops_params["year"] = y_val

                    # 2. تحديد المستهدفات
                    st.markdown("##### 🎯 تحديد المستهدفات (لكل محصل)")
                    tgt_col1, tgt_col2 = st.columns(2)
                    with tgt_col1:
                        cov_target_val = st.number_input(
                            "مستهدف التغطية (كعدد عملاء لكل محصل):",
                            min_value=1,
                            value=200,
                            step=10,
                            help="عدد العملاء المطلوب متابعتهم في الفترة المحددة"
                        )
                    with tgt_col2:
                        col_target_val = st.number_input(
                            "مستهدف التحصيل (كمبالغ لكل محصل - ريال):",
                            min_value=100.0,
                            value=50000.0,
                            step=1000.0,
                            help="إجمالي مبالغ السداد المطلوب تحصيلها من كل محصل"
                        )
                    ops_params["coverage_target"] = cov_target_val
                    ops_params["collection_target"] = col_target_val

                    # 3. تحديد المشرفين
                    st.markdown("##### 👥 تحديد المشرفين:")
                    all_sups = filter_options.get("supervisors", [])
                    sel_sups = st.multiselect(
                        "اختر المشرفين المراد تضمينهم (اختياري - اتركه فارغاً لاختيار الكل):",
                        options=all_sups,
                        default=all_sups,
                        help="يمكنك استبعاد أي مشرف هو ومحصليه من التقرير"
                    )
                    ops_params["supervisors"] = sel_sups if sel_sups else None
            finally:
                try:
                    os.unlink(tmp_scan_path)
                except:
                    pass

        # ─── واجهة التحصيل الإلكتروني ───
        elec_params = {}
        if selected_key == "electronic" and uploaded_files.get("portfolio"):
            portfolio_file = uploaded_files["portfolio"]
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_scan:
                tmp_scan.write(portfolio_file.getbuffer())
                tmp_scan_path = tmp_scan.name
            try:
                filter_options = scan_portfolio_for_electronic(tmp_scan_path)
                if filter_options:
                    st.markdown("#### 💻 اختر المهمة المطلوبة (التحصيل الإلكتروني):")

                    elec_rep_mode = st.radio(
                        "المهمة المطلوبة:",
                        options=[
                            "1️⃣ تاسك حالات التواصل والنسب (توصل / عدم توصل / لا يرد ومغلق)",
                            "2️⃣ تاسك نسبة التغطية والنسب (تحديد تاريخ التغطية)",
                            "3️⃣ تاسك التقرير الشامل (Segment + نوع الخدمة + إمكانية تحديد فترة)"
                        ],
                        index=0
                    )

                    if "1️⃣" in elec_rep_mode:
                        elec_params["report_mode"] = "task1_contact"
                        elec_params["target_date"] = None
                    elif "2️⃣" in elec_rep_mode:
                        elec_params["report_mode"] = "task2_coverage"
                        d_val = st.date_input("تاريخ التغطية (لمطابقة تاريخ المتابعة):", datetime.today())
                        elec_params["target_date"] = d_val
                    else:
                        elec_params["report_mode"] = "task3_comprehensive"
                        st.markdown("##### 📅 تحديد الفترة الزمنية (اختياري):")
                        w_cols = st.columns(2)
                        with w_cols[0]:
                            s_val = st.date_input("تاريخ البداية:", datetime.today() - timedelta(days=30))
                        with w_cols[1]:
                            e_val = st.date_input("تاريخ النهاية:", datetime.today())
                        elec_params["start_date"] = s_val
                        elec_params["end_date"] = e_val
                        elec_params["target_date"] = None

                    c1, c2 = st.columns(2)
                    with c1:
                        branch_sel = st.multiselect("الفرع (اختياري):", filter_options.get("branches", []))
                    with c2:
                        sup_sel = st.multiselect("المشرف (اختياري):", filter_options.get("supervisors", []))

                    elec_params["branches"] = branch_sel if branch_sel else None
                    elec_params["supervisors"] = sup_sel if sup_sel else None
            finally:
                try:
                    os.unlink(tmp_scan_path)
                except:
                    pass

        # ─── واجهة تقرير التحصيل بالشهور بالمستهدف ───
        monthly_params = {}
        if selected_key == "monthly_targets" and uploaded_files.get("portfolio") and uploaded_files.get("payments"):
            portfolio_file = uploaded_files["portfolio"]
            payments_file = uploaded_files["payments"]

            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_port, \
                 tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_pmt:
                tmp_port.write(portfolio_file.getbuffer())
                tmp_pmt.write(payments_file.getbuffer())
                tmp_port_path = tmp_port.name
                tmp_pmt_path = tmp_pmt.name

            try:
                from modules.module12_monthly_targets import MonthlyTargetsModule
                df_scan_pmt = read_excel_calamine(tmp_pmt_path)
                df_scan_port = read_excel_calamine(tmp_port_path)

                avail_months = MonthlyTargetsModule.detect_available_months(df_scan_pmt)
                port_sups = []
                sup_c = next((c for c in ["المشرف", "اسم المشرف", "supervisor", "Supervisor"] if c in df_scan_port.columns), None)
                if sup_c:
                    port_sups = sorted([str(x).strip() for x in df_scan_port[sup_c].drop_nulls().unique().to_list() if str(x).strip() not in ('', 'nan', 'None')])

                if avail_months:
                    st.markdown("---")
                    st.markdown("### 📅 إعدادات تقرير التحصيل بالشهور والمستهدفات")

                    month_keys_map = {m["label"]: m["key"] for m in avail_months}
                    all_month_labels = list(month_keys_map.keys())

                    selected_month_labels = st.multiselect(
                        "اختر الشهور المراد تضمينها في التقرير:",
                        options=all_month_labels,
                        default=all_month_labels,
                        help="يمكنك اختيار شهر واحد أو عدة شهور للمقارنة"
                    )

                    selected_month_keys = [month_keys_map[lbl] for lbl in selected_month_labels if lbl in month_keys_map]
                    monthly_params["selected_months"] = selected_month_keys

                    # إدخال المستهدفات لكل شهر
                    st.markdown("##### 🎯 تحديد مستهدف التحصيل لكل شهر (لكل محصل - ريال):")
                    c_def1, c_def2 = st.columns([2, 1])
                    with c_def1:
                        unified_target = st.number_input(
                            "مستهدف موحد لجميع الشهور المحددة (لتسهيل الإدخال):",
                            min_value=100.0,
                            value=50000.0,
                            step=1000.0
                        )
                    with c_def2:
                        apply_unified = st.checkbox("اعتماد المستهدف الموحد لجميع الشهور", value=True)

                    monthly_targets_dict = {}
                    if selected_month_labels:
                        m_cols = st.columns(min(len(selected_month_labels), 3))
                        for idx, lbl in enumerate(selected_month_labels):
                            k = month_keys_map[lbl]
                            col_to_use = m_cols[idx % len(m_cols)]
                            with col_to_use:
                                if apply_unified:
                                    t_val = unified_target
                                    st.text_input(f"مستهدف {lbl}:", value=f"{unified_target:,.2f} ﷼", disabled=True, key=f"disp_tgt_{k}")
                                else:
                                    t_val = st.number_input(
                                        f"مستهدف {lbl}:",
                                        min_value=100.0,
                                        value=50000.0,
                                        step=1000.0,
                                        key=f"input_tgt_{k}"
                                    )
                                monthly_targets_dict[k] = float(t_val)

                    monthly_params["monthly_targets"] = monthly_targets_dict

                    # تصفية المشرفين (اختياري)
                    if port_sups:
                        st.markdown("##### 👥 تحديد المشرفين (اختياري):")
                        sel_sups = st.multiselect(
                            "اختر المشرفين المراد تضمينهم (اتركه فارغاً لاختيار الكل):",
                            options=port_sups,
                            default=port_sups,
                            help="يمكنك استبعاد أي مشرف هو ومحصليه من التقرير"
                        )
                        monthly_params["supervisors"] = sel_sups if sel_sups else None

            finally:
                try:
                    os.unlink(tmp_port_path)
                    os.unlink(tmp_pmt_path)
                except:
                    pass

        # ─── واجهة التحليل الشامل للمحفظة ───
        pa_params = {}
        if selected_key == "portfolio_analytics":
            if uploaded_files.get("payments"):
                st.markdown("⏱️ **تحديد فترة التحصيل (اختياري):**")
                pa_c1, pa_c2 = st.columns(2)
                with pa_c1:
                    pa_s_date = st.date_input("من تاريخ سداد:", value=None, key="pa_s_dt")
                with pa_c2:
                    pa_e_date = st.date_input("إلى تاريخ سداد:", value=None, key="pa_e_dt")
                if pa_s_date:
                    pa_params["date_from"] = pa_s_date.strftime("%Y-%m-%d")
                if pa_e_date:
                    pa_params["date_to"] = pa_e_date.strftime("%Y-%m-%d")
            else:
                st.info("💡 **شيت التحصيل:** اختياري. يمكن التحليل بملف المحفظة فقط، أو إرفاق ملف التحصيل لحساب نسب التحصيل وتحليل عمر الدين.")

        # ─── التحقق من الجاهزية ───
        ready_to_run = True
        for fspec in module_info["files"]:
            if fspec["required"] and not uploaded_files.get(fspec["key"]):
                ready_to_run = False
        if selected_key == "rotation" and not rotation_params:
            ready_to_run = False
        if selected_key == "balancing" and not balancing_params:
            ready_to_run = False
        if selected_key == "operations" and not ops_params:
            ready_to_run = False
        if selected_key == "electronic" and not elec_params:
            ready_to_run = False
        if selected_key == "monthly_targets" and not monthly_params.get("selected_months"):
            ready_to_run = False

        # ─── زر التشغيل ───
        st.markdown("<div class='purple-divider'></div>", unsafe_allow_html=True)

        if st.button("🚀 تشغيل التحليل والمعالجة", disabled=not ready_to_run, use_container_width=True):
            temp_files = []
            path_map = {}
            try:
                with st.spinner("⏳ جاري قراءة وتجهيز الملفات..."):
                    for key, file_obj in uploaded_files.items():
                        if file_obj:
                            suffix = os.path.splitext(file_obj.name)[1] or ".xlsx"
                            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                                tmp.write(file_obj.getbuffer())
                                tmp_path = tmp.name
                                temp_files.append(tmp_path)
                                if key == "portfolio":
                                    path_map[MAIN_PORTFOLIO] = tmp_path
                                elif key == "promise":
                                    path_map[PROMISE_PAY] = tmp_path
                                elif key == "payments":
                                    path_map["payments"] = tmp_path

                    dfs, results = load_files(path_map)
                    for k, vr in results.items():
                        if not vr.is_valid:
                            st.error(f"❌ الملف {k} غير صالح: {vr.summary()}")
                            st.stop()

                    portfolio = dfs.get(MAIN_PORTFOLIO)
                    promise = dfs.get(PROMISE_PAY, pl.DataFrame())

                with st.spinner("⚙️ جاري معالجة البيانات وتطبيق القواعد الحسابية..."):
                    task_id = module_info["id"]
                    stats = {}
                    out_fd, out_path = tempfile.mkstemp(suffix=".xlsx")
                    os.close(out_fd)
                    temp_files.append(out_path)
                    writer = ExcelReportWriter(out_path) if task_id != 14 else None

                    if task_id == 1:
                        from modules.module1_errors import SystemErrorsModule
                        r = SystemErrorsModule().run(portfolio, promise)
                        stats.update(r["stats"])
                        writer.write_errors(r["data"])

                    elif task_id == 2:
                        from modules.module2_contact import ContactStatusModule
                        r = ContactStatusModule().run(portfolio)
                        stats.update(r["stats"])
                        writer.write_contact(r["data"], r["pivot_supervisor"], r["pivot_collector"], r["pivot_status"])

                    elif task_id == 3:
                        from modules.module3_neglect import NeglectModule
                        r = NeglectModule().run(portfolio)
                        stats.update(r["stats"])
                        writer.write_neglect(r["data"], r["full_analysis"], r["pivot_summary"],
                                             r["pivot_supervisor"], r["pivot_collector"], r["pivot_status"],
                                             r["pivot_branch"], r["pivot_portfolio"], r["pivot_days"])

                    elif task_id == 7:
                        from modules.module7_targets import TargetCustomersModule
                        r = TargetCustomersModule().run(portfolio, promise, pl.DataFrame())
                        stats.update(r["stats"])
                        writer.write_targets(r["data"], r["pivot_supervisor"])

                    elif task_id == 6:
                        sup = rotation_params["supervisor"]
                        col = rotation_params["collector"]
                        tgt_cols = rotation_params.get("target_collectors")
                        smart_assign = rotation_params.get("smart_assignment", False)
                        selected_statuses = rotation_params.get("selected_main_statuses")
                        from modules.module6b_rotation import PortfolioRotationModule
                        r = PortfolioRotationModule().run(
                            portfolio,
                            col,
                            sup,
                            target_collectors=tgt_cols,
                            smart_assignment=smart_assign,
                            selected_main_statuses=selected_statuses,
                            electronic_code="test.t"
                        )
                        stats.update(r["stats"])
                        writer.write_rotation(r["data"], r["execution_report"],
                                              r["distribution_summary"], r["withdrawal_summary"])

                    elif task_id == 8:
                        from modules.module8_balancing import PortfolioBalancingModule
                        tgt = balancing_params.get("target") or None
                        r = PortfolioBalancingModule().run(
                            portfolio,
                            source_portfolios=balancing_params["source"],
                            target_portfolios=tgt,
                            min_customers_per_collector=balancing_params.get("min_per_col", 0),
                            max_count_diff=balancing_params.get("max_count_diff", 35),
                            max_balance_diff=float(balancing_params.get("max_bal_diff", 80000.0)),
                            withdraw_all_source=balancing_params.get("withdraw_all", False),
                        )
                        stats.update(r["stats"])
                        writer.write_balancing(r["data"], r["summary_pivot"],
                                               r.get("planning_sheet"), r.get("source_summary"),
                                               r.get("final_result_sheet"))

                    elif task_id == 9:
                        from modules.module9_operations_report import OperationsReportModule
                        pmt_df = dfs.get("payments")
                        r = OperationsReportModule().run(
                            portfolio,
                            payments=pmt_df,
                            report_mode=ops_params.get("report_mode", "daily"),
                            target_date=ops_params.get("target_date"),
                            start_date=ops_params.get("start_date"),
                            end_date=ops_params.get("end_date"),
                            month=ops_params.get("month"),
                            year=ops_params.get("year"),
                            supervisors=ops_params.get("supervisors"),
                            coverage_target=ops_params.get("coverage_target", 200),
                            collection_target=ops_params.get("collection_target", 50000),
                        )
                        stats.update(r["stats"])
                        writer.write_operations_report(
                            report_table=r["report_table"],
                            data=r["data"],
                            stats=r["stats"]
                        )

                    elif task_id == 10:
                        from modules.module10_electronic_collection import ElectronicCollectionModule
                        r = ElectronicCollectionModule().run(
                            portfolio,
                            report_mode=elec_params.get("report_mode", "coverage"),
                            target_date=elec_params.get("target_date"),
                            start_date=elec_params.get("start_date"),
                            end_date=elec_params.get("end_date"),
                            branches=elec_params.get("branches"),
                            supervisors=elec_params.get("supervisors")
                        )
                        if "error" in r:
                            st.error(r["error"])
                            st.stop()
                        stats.update(r["stats"])
                        writer.write_electronic_collection(
                            r["data"], r["pivot_supervisor"], r["pivot_collector"],
                            r["pivot_segment"], r["stats"]
                        )

                    elif task_id == 12:
                        from modules.module12_monthly_targets import MonthlyTargetsModule
                        r = MonthlyTargetsModule().run(
                            portfolio=portfolio,
                            payments=dfs.get("payments"),
                            selected_months=monthly_params.get("selected_months", []),
                            monthly_targets=monthly_params.get("monthly_targets", {}),
                            supervisors=monthly_params.get("supervisors"),
                        )
                        stats.update(r["stats"])
                        writer.write_monthly_targets_report(
                            report_table=r["report_table"],
                            months_meta=r["months_meta"],
                            stats=r["stats"]
                        )

                    elif task_id == 14:
                        from modules.module14_portfolio_analytics import StrategicPortfolioModule, export_analytics_excel_bytes
                        r = StrategicPortfolioModule().run(
                            portfolio=portfolio,
                            payments=dfs.get("payments"),
                            date_from=pa_params.get("date_from"),
                            date_to=pa_params.get("date_to"),
                            supervisors=pa_params.get("supervisors"),
                        )
                        stats.update(r["stats"])
                        pa_excel_data = export_analytics_excel_bytes(r)
                        with open(out_path, "wb") as f_pa:
                            f_pa.write(pa_excel_data)

                    if task_id not in [10, 12, 14] and writer:
                        writer.write_dashboard(stats, task_id)
                        writer.write_summary(stats)
                        writer.save()
                    elif task_id in [10, 12] and writer:
                        writer.save()

                st.balloons()
                st.success("✨ اكتملت معالجة البيانات بنجاح وتم إنشاء التقرير المنسق!")

                # ─── عرض الإحصائيات ───
                st.markdown("#### 📊 ملخص نتائج التقرير")
                stats_cols = st.columns(min(len(stats), 4))
                for j, (k, v) in enumerate(stats.items()):
                    col_idx = j % len(stats_cols)
                    with stats_cols[col_idx]:
                        st.metric(label=str(k) if k is not None else "غير مصنف", value=str(v))

                # عرض أفضل مشرف وأفضل محصل إذا كان تقرير العمليات
                if task_id == 9 and 'r' in locals():
                    best_sup = r.get("best_supervisor", "غير محدد")
                    best_col = r.get("best_collector", "غير محدد")
                    if best_sup != "غير محدد" or best_col != "غير محدد":
                        st.markdown("---")
                        st.markdown("### 🏆 نجوم وأبطال الأداء الفردي")
                        c_hero1, c_hero2 = st.columns(2)
                        with c_hero1:
                            st.markdown(f"""
                            <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                                <h4 style="color: #b45309; margin-bottom: 6px; font-weight: 800;">⭐ أفضل مشرف أداء</h4>
                                <h2 style="color: #0f172a; margin: 4px 0; font-weight: 900;">{best_sup}</h2>
                                <p style="color: #475569; font-size: 0.95rem; margin: 0; font-weight: 600;">أعلى نسبة تغطية وتواصل وتحصيل مالي متميز</p>
                            </div>
                            """, unsafe_allow_html=True)
                        with c_hero2:
                            st.markdown(f"""
                            <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                                <h4 style="color: #047857; margin-bottom: 6px; font-weight: 800;">🏆 أفضل محصل أداء</h4>
                                <h2 style="color: #0f172a; margin: 4px 0; font-weight: 900;">{best_col}</h2>
                                <p style="color: #475569; font-size: 0.95rem; margin: 0; font-weight: 600;">أعلى معدل تواصل ونسبة إغلاق وسداد موثق</p>
                            </div>
                            """, unsafe_allow_html=True)

                # جدول ملخص تقرير العمليات (Module 9)
                if task_id == 9 and 'r' in locals() and "report_table" in r:
                    st.markdown("---")
                    st.markdown("### 📋 جدول تقرير العمليات (التغطية والتحصيل ونسب الإنجاز)")
                    st.caption("يعرض أداء المشرفين والمحصلين ونسب التغطية ونسب التحصيل مقارنة بالمستهدفات المحددة بدقة:")
                    rep_tbl = r["report_table"]
                    disp_cols = [c for c in rep_tbl.columns if not c.startswith("_")]
                    st.dataframe(
                        rep_tbl.select(disp_cols).to_pandas(), 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "المشرف": st.column_config.TextColumn("👤 المشرف", width="medium"),
                            "المحصل": st.column_config.TextColumn("👔 المحصل", width="medium"),
                            "التغطية": st.column_config.NumberColumn("✅ التغطية (الفعلي)", format="%d"),
                            "مستهدف التغطية": st.column_config.NumberColumn("🎯 مستهدف التغطية", format="%d"),
                            "نسبة التغطية %": st.column_config.ProgressColumn(
                                "📊 نسبة التغطية %", help="التغطية ÷ مستهدف التغطية", format="%.2f%%", min_value=0, max_value=100
                            ),
                            "التحصيل": st.column_config.NumberColumn("💰 التحصيل (الفعلي)", format="%.2f ﷼"),
                            "مستهدف التحصيل": st.column_config.NumberColumn("🎯 مستهدف التحصيل", format="%.2f ﷼"),
                            "نسبة التحصيل %": st.column_config.ProgressColumn(
                                "📈 نسبة التحصيل %", help="التحصيل ÷ مستهدف التحصيل", format="%.2f%%", min_value=0, max_value=100
                            )
                        }
                    )

                # جدول ملخص التحصيل الإلكتروني التنفيذي (Module 10)
                if task_id == 10 and 'r' in locals() and "pivot_supervisor" in r:
                    st.markdown("---")
                    task_mode = elec_params.get("report_mode", "task1_contact")
                    if task_mode == "task1_contact":
                        st.markdown("### 📋 جدول ملخص حالات التواصل والنسب (Executive Summary)")
                        st.caption("يعرض إحصائيات التواصل الفعال، عدم التواصل، والحالات المغلقة/لا يرد مع النسب المئوية للمحفظة.")
                        disp_cols = ["المشرف", "عدد العملاء", "توصل", "نسبة التوصل %", "عدم توصل", "نسبة عدم التوصل %", "لايرد-مغلق", "نسبة لايرد ومغلق %"]
                    elif task_mode == "task2_coverage":
                        st.markdown("### 📋 جدول ملخص نسبة التغطية والنسب (Executive Summary)")
                        st.caption("يعرض نسبة العملاء المغطين وغير المغطين بناءً على تاريخ التغطية المحدد.")
                        disp_cols = ["المشرف", "عدد العملاء", "العملاء المغطين", "نسبة التغطية %", "غير المغطين", "نسبة عدم التغطية %"]

                        st.markdown("### 📋 جدول الملخص التنفيذي الشامل (Executive Summary)")
                        st.caption("تقرير شامل يجمع أداء المشرفين والقطاعات ونسب التغطية والتواصل.")
                        disp_cols = ["المشرف", "عدد العملاء", "العملاء المغطين", "نسبة التغطية %", "توصل", "نسبة التوصل %"]

                    sup_df = r["pivot_supervisor"]
                    cols_to_show = [c for c in disp_cols if c in sup_df.columns]
                    if cols_to_show:
                        show_df = sup_df.select(cols_to_show)
                        st.dataframe(show_df.to_pandas(), use_container_width=True, hide_index=True)

                    if task_mode == "task3_comprehensive" and "pivot_segment" in r and not r["pivot_segment"].is_empty():
                        st.markdown("#### 🧩 ملخص القطاعات (Segment) ونوع الخدمة الموثقة")
                        st.dataframe(r["pivot_segment"].to_pandas(), use_container_width=True, hide_index=True)

                # جدول توزيع المحصلين (Module 8)
                if task_id == 8 and 'r' in locals() and "summary_pivot" in r:
                    st.markdown("---")
                    st.markdown("#### 📋 جدول ملخص التوزيع النهائي للمحصلين")
                    summary_df = r["summary_pivot"]
                    target_cols = ["المحصل", "المحصل الجديد", "اليوزر", "عدد العملاء بعد", "عدد العملاء", "إجمالي متبقي السداد"]
                    cols_to_show = [c for c in target_cols if c in summary_df.columns]
                    if cols_to_show:
                        show_df = summary_df.select(cols_to_show)
                        first_col = cols_to_show[0]
                        show_df = show_df.filter(~pl.col(first_col).cast(pl.String).str.contains("📉|📈"))
                        st.dataframe(show_df.to_pandas(), use_container_width=True, hide_index=True)

                # جدول تقرير التحصيل بالشهور بالمستهدف (Module 12)
                if task_id == 12 and 'r' in locals() and "report_table" in r:
                    st.markdown("---")
                    st.markdown("### 📋 جدول تقرير التحصيل بالشهور بالمستهدف")
                    st.caption("يعرض أداء المشرفين والمحصلين ونسب الإنجاز شهر بشهر مقارنة بالمستهدفات المحددة بدقة:")
                    rep_tbl = r["report_table"]
                    disp_cols = [c for c in rep_tbl.columns if not c.startswith("_")]

                    col_cfg = {
                        "المشرف": st.column_config.TextColumn("👤 المشرف", width="medium"),
                        "المحصل": st.column_config.TextColumn("👔 المحصل", width="medium"),
                    }
                    for c_name in disp_cols:
                        if "%" in c_name:
                            col_cfg[c_name] = st.column_config.ProgressColumn(
                                c_name, format="%.2f%%", min_value=0, max_value=100
                            )
                        elif "تحصيل" in c_name or "مستهدف" in c_name:
                            col_cfg[c_name] = st.column_config.NumberColumn(
                                c_name, format="%.2f ﷼"
                            )

                    st.dataframe(
                        rep_tbl.select(disp_cols).to_pandas(), 
                        use_container_width=True, 
                        hide_index=True,
                        column_config=col_cfg
                    )

                # التحليل الشامل للمحفظة وعمر الدين (Module 14)
                if task_id == 14 and 'r' in locals() and "vintage_table" in r:
                    import plotly.express as px
                    import plotly.graph_objects as go

                    st.markdown("---")
                    st.markdown("## 🏛️ تقرير التحليل الشامل للمحفظة وعمر الدين")
                    st.caption("تحليل موحد ومباشر يتضمن نسب التواصل، تحليل عمر الدين، أداء المشرفين، وتقييم المحصلين.")

                    # ─────────────────────────────────────────────────────────────
                    # 1. لوحة الرسومات البيانية (درجات الأزرق)
                    # ─────────────────────────────────────────────────────────────
                    g_c1, g_c2 = st.columns([1, 1.4])
                    with g_c1:
                        contact_pie_df = r["contact_summary"].iloc[:-2].copy()
                        fig_contact = px.pie(
                            contact_pie_df,
                            names="حالة التواصل",
                            values="عدد الحسابات (السجلات)",
                            hole=0.45,
                            title="📞 توزيع ونسب حالات التواصل (قواعد موديول 2)",
                            color="حالة التواصل",
                            color_discrete_map={
                                "تم التوصل": "#1E3A8A",
                                "لا يرد ومغلق": "#2563EB",
                                "عدم التوصل": "#93C5FD"
                            }
                        )
                        fig_contact.update_traces(textposition='inside', textinfo='percent+label')
                        fig_contact.update_layout(
                            title_font_size=15,
                            legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5),
                            margin=dict(l=10, r=10, t=40, b=30),
                            height=360
                        )
                        st.plotly_chart(fig_contact, use_container_width=True)

                    with g_c2:
                        v_chart_df = r["vintage_table"].iloc[:-1].copy()
                        if not v_chart_df.empty:
                            fig_vintage = go.Figure()
                            fig_vintage.add_trace(go.Bar(
                                x=v_chart_df["عمر الدين (السنة)"],
                                y=v_chart_df["مبلغ المديونية"],
                                name="مبلغ المديونية (المحفظة)",
                                marker_color="#1E3A8A"
                            ))
                            fig_vintage.add_trace(go.Bar(
                                x=v_chart_df["عمر الدين (السنة)"],
                                y=v_chart_df["متبقي سداد موثق"],
                                name="متبقي سداد موثق (المحفظة)",
                                marker_color="#2563EB"
                            ))
                            if r.get("has_payments", False):
                                fig_vintage.add_trace(go.Bar(
                                    x=v_chart_df["عمر الدين (السنة)"],
                                    y=v_chart_df["إجمالي التحصيل"],
                                    name="إجمالي التحصيل (شيت التحصيل)",
                                    marker_color="#60A5FA"
                                ))
                            fig_vintage.update_layout(
                                barmode='group',
                                title="⏳ المديونية والمتبقي والتحصيل حسب سنة عمر الدين",
                                xaxis_title="سنة عمر الدين",
                                yaxis_title="المبلغ (ريال)",
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                template="plotly_white",
                                margin=dict(l=10, r=10, t=40, b=30),
                                height=360
                            )
                            st.plotly_chart(fig_vintage, use_container_width=True)

                    # ─────────────────────────────────────────────────────────────
                    # 2. جدول ملخص حالات التواصل (موديول 2)
                    # ─────────────────────────────────────────────────────────────
                    st.markdown("---")
                    st.markdown("### 📞 جدول ملخص حالات التواصل (قواعد برنامج التوصل وعدم التوصل)")
                    st.dataframe(r["contact_summary"], use_container_width=True, hide_index=True)

                    # ─────────────────────────────────────────────────────────────
                    # 3. جدول تحليل عمر الدين (الربط بشيت التحصيل)
                    # ─────────────────────────────────────────────────────────────
                    st.markdown("---")
                    st.markdown("### ⏳ جدول تحليل عمر الدين (سنة إنتهاء الحساب / فصل الخدمة)")
                    st.caption("مبلغ المديونية ومتبقي سداد موثق من المحفظة | التحصيل محسوب حصراً من شيت التحصيل بربط رقم المديونية | نسبة التحصيل % من مبلغ المديونية:")
                    st.dataframe(r["vintage_table"], use_container_width=True, hide_index=True)

                    # ─────────────────────────────────────────────────────────────
                    # 4. أداء المشرفين وفلترة المشرف وفرق المحصلين
                    # ─────────────────────────────────────────────────────────────
                    st.markdown("---")
                    st.markdown("### 👥 تقرير ومقارنة أداء المشرفين")
                    st.dataframe(r["supervisor_table"], use_container_width=True, hide_index=True)

                    sup_chart_df = r["supervisor_table"].copy()
                    if not sup_chart_df.empty:
                        fig_sup = go.Figure()
                        fig_sup.add_trace(go.Bar(
                            x=sup_chart_df["المشرف"],
                            y=sup_chart_df["مبلغ المديونية"],
                            name="مبلغ المديونية",
                            marker_color="#93C5FD"
                        ))
                        if r.get("has_payments", False):
                            fig_sup.add_trace(go.Bar(
                                x=sup_chart_df["المشرف"],
                                y=sup_chart_df["إجمالي التحصيل"],
                                name="إجمالي التحصيل",
                                marker_color="#1E3A8A"
                            ))
                        fig_sup.update_layout(
                            barmode='group',
                            title="👥 مقارنة المديونية والتحصيل لكل مشرف",
                            xaxis_title="المشرف",
                            yaxis_title="المبلغ (ريال)",
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            template="plotly_white",
                            height=330
                        )
                        st.plotly_chart(fig_sup, use_container_width=True)

                    # فلترة المشرف
                    st.markdown("#### 🔍 تفصيل أداء مشرف محدد وفريق المحصلين التابعين له")
                    sup_list = ["الكل (جميع المشرفين)"] + sorted([s for s in r["supervisor_table"]["المشرف"].unique() if s != "غير محدد"])
                    selected_sup = st.selectbox(
                        "اختر المشرف لعرض ملخصه التفصيلي وفريق المحصلين التابعين له:",
                        options=sup_list,
                        key="pa_selected_sup_single_page"
                    )

                    if selected_sup != "الكل (جميع المشرفين)":
                        sup_match = r["supervisor_table"][r["supervisor_table"]["المشرف"] == selected_sup]
                        if not sup_match.empty:
                            sup_row = sup_match.iloc[0]
                            st.markdown(f"##### 📌 بطاقة أداء المشرف: **{selected_sup}**")
                            
                            m1, m2, m3, m4, m5, m6 = st.columns(6)
                            with m1: st.metric("عدد الحسابات", f"{sup_row['عدد الحسابات']:,}")
                            with m2: st.metric("عدد العملاء", f"{sup_row['عدد العملاء']:,}")
                            with m3: st.metric("مبلغ المديونية", f"{sup_row['مبلغ المديونية']:,.2f} ﷼")
                            with m4: st.metric("متبقي سداد موثق", f"{sup_row['متبقي سداد موثق']:,.2f} ﷼")
                            with m5: st.metric("إجمالي التحصيل", f"{sup_row['إجمالي التحصيل']:,.2f} ﷼")
                            with m6: st.metric("نسبة التحصيل %", f"{sup_row['نسبة التحصيل %']}%")

                            c_m1, c_m2, c_m3 = st.columns(3)
                            with c_m1: st.metric("تم التوصل", f"{sup_row['تم التوصل']:,} ({sup_row['نسبة التوصل %']})")
                            with c_m2: st.metric("لا يرد ومغلق", f"{sup_row['لا يرد ومغلق']:,}")
                            with c_m3: st.metric("عدم التوصل", f"{sup_row['عدم التوصل']:,} ({sup_row['نسبة عدم التوصل %']})")

                            st.markdown(f"##### 👔 فريق المحصلين التابعين للمشرف ({selected_sup}):")
                            sup_cols_df = r["all_collectors"][r["all_collectors"]["المشرف"] == selected_sup].copy()
                            if not sup_cols_df.empty:
                                st.dataframe(sup_cols_df, use_container_width=True, hide_index=True)
                                
                                fig_team = px.bar(
                                    sup_cols_df,
                                    x="المحصل",
                                    y="إجمالي التحصيل",
                                    color="مبلغ المديونية",
                                    color_continuous_scale=["#93C5FD", "#3B82F6", "#1E3A8A"],
                                    title=f"📊 تحصيل محصلي المشرف {selected_sup}",
                                    text_auto=",.0f"
                                )
                                fig_team.update_layout(template="plotly_white", height=320)
                                st.plotly_chart(fig_team, use_container_width=True)
                            else:
                                st.info("لا يوجد محصلين مسجلين تحت هذا المشرف.")

                    # ─────────────────────────────────────────────────────────────
                    # 5. أفضل 10 وأسوأ 10 محصلين
                    # ─────────────────────────────────────────────────────────────
                    st.markdown("---")
                    st.markdown("### 🏆 لوحة أداء المحصلين (الأفضل والأسوأ تحصيلاً)")
                    c_top, c_bot = st.columns(2)
                    with c_top:
                        st.markdown("#### 🥇 أفضل 10 محصلين تحصيلاً")
                        st.dataframe(r["top_10_collectors"], use_container_width=True, hide_index=True)
                    with c_bot:
                        st.markdown("#### ⚠️ أقل 10 محصلين تحصيلاً")
                        st.dataframe(r["bottom_10_collectors"], use_container_width=True, hide_index=True)

# ─── زر التحميل ───
                with open(out_path, "rb") as f_out:
                    excel_bytes = f_out.read()

                ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                download_name = f"مهاره_{selected_key}_{ts_str}.xlsx"

                st.markdown("<div class='purple-divider'></div>", unsafe_allow_html=True)
                st.download_button(
                    label="📥 تحميل التقرير النهائي (Excel Styled)",
                    data=excel_bytes,
                    file_name=download_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            except Exception as e:
                st.exception(e)
                st.error(f"❌ حدث خطأ أثناء تشغيل النظام: {e}")

            finally:
                for p in temp_files:
                    try:
                        os.unlink(p)
                    except:
                        pass
