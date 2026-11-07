"""
powerbi_exporter/doc_generator.py
==================================
Generates Documentation files for Power BI Export:
- README.txt (step-by-step Power BI import instructions, page designs, rules)
- Relationships.xlsx Dataframe
- Data_Dictionary.xlsx Dataframe
- Data_Model_Documentation.xlsx Dataframe
"""
import pandas as pd
from typing import Dict, Any


def generate_readme_text(val_report: Dict[str, Any]) -> str:
    """Generates complete README.txt for the Power BI Package."""
    return f"""===============================================================================
POWER BI READY DATA PACKAGE — MAHARA DEBT COLLECTION SECTOR
===============================================================================
تاريخ التصدير: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
مصدر البيانات: نظام مهاره لتحصيل الديون — قطاع أعمال الاتصالات

-------------------------------------------------------------------------------
1. ملخص البيانات والجودة (Data Quality Summary):
-------------------------------------------------------------------------------
- حالة الحزمة: {'جاهزة للاستيراد 100%' if val_report.get('is_valid') else 'يوجد ملاحظات جودة'}
- إجمالي عدد العملاء: {val_report.get('total_customers', 0):,} عميل
- إجمالي عدد المديونيات: {val_report.get('total_debts', 0):,} مديونية
- إجمالي عدد عمليات السداد: {val_report.get('total_payments', 0):,} عملية
- إجمالي مبلغ المديونية: {val_report.get('total_debt_amount', 0.0):,.2f} ريال
- إجمالي مبلغ التحصيل: {val_report.get('total_payment_amount', 0.0):,.2f} ريال
- نسبة التحصيل الإجمالية: {val_report.get('collection_rate_pct', 0.0):.2f}%
- عدد ملاحظات جودة البيانات: {val_report.get('data_quality_issues_count', 0)}

-------------------------------------------------------------------------------
2. خطوات الاستيراد وبناء الـ Dashboard في Power BI:
-------------------------------------------------------------------------------
الخطوة 1: فتح برنامج Power BI Desktop وإنشاء ملف جديد (.pbix).
الخطوة 2: اضغط على Get Data -> Excel Workbook واستورد كافة الملفات من مجلد Data/:
          - DimCustomer.xlsx
          - FactDebt.xlsx
          - FactPayment.xlsx
          - DimCollector.xlsx
          - DimSupervisor.xlsx
          - DimPortfolio.xlsx
          - DimCase.xlsx
          - DimDate.xlsx
          - Customer_Payment_History.xlsx
          - Daily_Snapshots.xlsx
          - Unmatched_Payments.xlsx
          - Data_Quality.xlsx

الخطوة 3: إعداد العلاقات (Relationships):
          راجع ملف Model/Relationships.xlsx وقم بربط الجداول كما يلي:
          - DimCustomer[Customer_ID]  1 -> *  FactDebt[Customer_ID]
          - DimCustomer[Customer_ID]  1 -> * FactPayment[Customer_ID]
          - DimCollector[Collector_ID] 1 -> * FactDebt[Collector_ID]
          - DimCollector[Collector_ID] 1 -> * FactPayment[Collector_ID]
          - DimSupervisor[Supervisor_ID] 1 -> * FactDebt[Supervisor_ID]
          - DimSupervisor[Supervisor_ID] 1 -> * FactPayment[Supervisor_ID]
          - DimPortfolio[Portfolio_ID] 1 -> * FactDebt[Portfolio_ID]
          - DimPortfolio[Portfolio_ID] 1 -> * FactPayment[Portfolio_ID]
          - DimDate[Date]             1 -> * FactPayment[Payment_Date]
          - DimCase[Case_ID]           1 -> * FactDebt[Case_ID]

الخطوة 4: تطبيق الثيم الهوياتي (Theme):
          في Power BI اذهب لـ View -> Themes -> Browse for Themes
          واختر ملف Theme/PowerBI_Theme.json

الخطوة 5: إضافة صيغ ومقاييس DAX:
          افتح مجلد DAX/ وانسخ المعادلات الموجودة في كل ملف لإنشاء Measures مخصصة.

-------------------------------------------------------------------------------
3. دليل صفحات الـ Dashboard الـ 11 المقترحة:
-------------------------------------------------------------------------------
Page 1  - Executive Overview: نظرة تنفيذية شاملة (KPIs + أداء المحصلين والتحصيل اليومي).
Page 2  - Portfolio Analysis: تحليل تفصيلي لـ 6 محافظ مقارنة بالحجوم والمتبقي.
Page 3  - Collection Performance: تفاصيل التحصيل وتوزيع المبالغ اليومية والشهرية.
Page 4  - Collector Performance: رانك المحصلين، أعداد التوصل، ونسب إنجاز الأهداف.
Page 5  - Supervisor Performance: مقارنة أداء المشرفين وفرق العمل.
Page 6  - Case Analysis: تحليل الحالات الرئيسية والفرعية ومعدل السداد لكل حالة.
Page 7  - Customer 360: شاشة البحث برقم الهوية وعرض السجل الكامل للعميل والتوقعات.
Page 8  - Debt & Aging: أعمار المديونيات وفئات التأخير والراكد.
Page 9  - Payment Behavior: سلوك العملاء، التكرارية، ومتوسط الفترات بين السدادات.
Page 10 - Data Quality: لوحة مراقبة السدادات المكررة أو غير المطابقة وأخطاء النظام.
Page 11 - Historical Trends: اتجاهات النمو والتغير الشهري والسنوي MoM & YoY.

-------------------------------------------------------------------------------
4. قواعد العمل المطبقة (Single Source of Truth):
-------------------------------------------------------------------------------
- عدم ازدواجية التحصيل (No Double Counting).
- تطبيق الصرامة في عزل المحافظ (Portfolio Isolation Rule).
- ربط السدادات برقم الهوية والمرجع بدقة متناهية.
- الأرقام والمؤشرات متطابقة 100% مع شاشة Streamlit.
===============================================================================
"""


def generate_relationships_df() -> pd.DataFrame:
    """Generates Relationships documentation DataFrame."""
    rel_data = [
        {
            'From Table': 'DimCustomer',
            'From Column': 'Customer_ID',
            'To Table': 'FactDebt',
            'To Column': 'Customer_ID',
            'Cardinality': '1 to Many (1:*)',
            'Filter Direction': 'Single',
            'Description': 'ربط بيانات العملاء بالمديونيات المسجلة'
        },
        {
            'From Table': 'DimCustomer',
            'From Column': 'Customer_ID',
            'To Table': 'FactPayment',
            'To Column': 'Customer_ID',
            'Cardinality': '1 to Many (1:*)',
            'Filter Direction': 'Single',
            'Description': 'ربط العملاء بحركات السداد الفعلية'
        },
        {
            'From Table': 'DimCollector',
            'From Column': 'Collector_ID',
            'To Table': 'FactDebt',
            'To Column': 'Collector_ID',
            'Cardinality': '1 to Many (1:*)',
            'Filter Direction': 'Single',
            'Description': 'ربط المحصلين بمديونياتهم الموزعة'
        },
        {
            'From Table': 'DimCollector',
            'From Column': 'Collector_ID',
            'To Table': 'FactPayment',
            'To Column': 'Collector_ID',
            'Cardinality': '1 to Many (1:*)',
            'Filter Direction': 'Single',
            'Description': 'ربط المحصلين بعمليات التحصيل السديدة'
        },
        {
            'From Table': 'DimSupervisor',
            'From Column': 'Supervisor_ID',
            'To Table': 'FactDebt',
            'To Column': 'Supervisor_ID',
            'Cardinality': '1 to Many (1:*)',
            'Filter Direction': 'Single',
            'Description': 'ربط المشرفين بفرع وتوزيع الديون'
        },
        {
            'From Table': 'DimSupervisor',
            'From Column': 'Supervisor_ID',
            'To Table': 'FactPayment',
            'To Column': 'Supervisor_ID',
            'Cardinality': '1 to Many (1:*)',
            'Filter Direction': 'Single',
            'Description': 'ربط المشرفين بالسدادات المحققة'
        },
        {
            'From Table': 'DimPortfolio',
            'From Column': 'Portfolio_ID',
            'To Table': 'FactDebt',
            'To Column': 'Portfolio_ID',
            'Cardinality': '1 to Many (1:*)',
            'Filter Direction': 'Single',
            'Description': 'ربط المحافظ بالمديونيات الموزعة جغرافياً وتشغيلياً'
        },
        {
            'From Table': 'DimPortfolio',
            'From Column': 'Portfolio_ID',
            'To Table': 'FactPayment',
            'To Column': 'Portfolio_ID',
            'Cardinality': '1 to Many (1:*)',
            'Filter Direction': 'Single',
            'Description': 'ربط المحافظ بعمليات السداد'
        },
        {
            'From Table': 'DimCase',
            'From Column': 'Case_ID',
            'To Table': 'FactDebt',
            'To Column': 'Case_ID',
            'Cardinality': '1 to Many (1:*)',
            'Filter Direction': 'Single',
            'Description': 'ربط تصنيف الحالات الرئيسية والفرعية بالديون'
        },
        {
            'From Table': 'DimDate',
            'From Column': 'Date',
            'To Table': 'FactPayment',
            'To Column': 'Payment_Date',
            'Cardinality': '1 to Many (1:*)',
            'Filter Direction': 'Single',
            'Description': 'جدول التاريخ لتحليلات Time Intelligence والسدادات'
        }
    ]
    return pd.DataFrame(rel_data)


def generate_data_dictionary_df() -> pd.DataFrame:
    """Generates Data Dictionary documentation DataFrame."""
    dict_data = [
        # DimCustomer
        {'Table': 'DimCustomer', 'Column': 'Customer_ID', 'Description': 'رقم الهوية الفريد للعميل (Primary Key)', 'Data Type': 'Text', 'Key': 'PK', 'Source': 'Portfolio File'},
        {'Table': 'DimCustomer', 'Column': 'Customer_Name', 'Description': 'اسم أو وصف العميل', 'Data Type': 'Text', 'Key': 'None', 'Source': 'Generated'},
        {'Table': 'DimCustomer', 'Column': 'Portfolio_Name', 'Description': 'اسم المحفظة التابع لها العميل', 'Data Type': 'Text', 'Key': 'FK', 'Source': 'Portfolio File'},
        {'Table': 'DimCustomer', 'Column': 'Main_Status', 'Description': 'الحالة الرئيسية للعميل', 'Data Type': 'Text', 'Key': 'None', 'Source': 'Portfolio File'},
        {'Table': 'DimCustomer', 'Column': 'Sub_Status', 'Description': 'الحالة الفرعية للعميل', 'Data Type': 'Text', 'Key': 'None', 'Source': 'Portfolio File'},
        {'Table': 'DimCustomer', 'Column': 'Followup_Date', 'Description': 'تاريخ آخر متابعة مسجلة', 'Data Type': 'Date', 'Key': 'FK', 'Source': 'Portfolio File'},

        # FactDebt
        {'Table': 'FactDebt', 'Column': 'Debt_ID', 'Description': 'رقم المديونية الفريد (Primary Key)', 'Data Type': 'Text', 'Key': 'PK', 'Source': 'System Engine'},
        {'Table': 'FactDebt', 'Column': 'Customer_ID', 'Description': 'رقم الهوية التابع له المديونية', 'Data Type': 'Text', 'Key': 'FK', 'Source': 'Portfolio File'},
        {'Table': 'FactDebt', 'Column': 'Portfolio_ID', 'Description': 'معرف المحفظة', 'Data Type': 'Text', 'Key': 'FK', 'Source': 'System Engine'},
        {'Table': 'FactDebt', 'Column': 'Collector_ID', 'Description': 'معرف المحصل المستلم للملف', 'Data Type': 'Text', 'Key': 'FK', 'Source': 'System Engine'},
        {'Table': 'FactDebt', 'Column': 'Supervisor_ID', 'Description': 'معرف المشرف المسؤول', 'Data Type': 'Text', 'Key': 'FK', 'Source': 'System Engine'},
        {'Table': 'FactDebt', 'Column': 'Debt_Amount', 'Description': 'مبلغ المديونية الأصلي (ريال)', 'Data Type': 'Decimal', 'Key': 'None', 'Source': 'Portfolio File'},
        {'Table': 'FactDebt', 'Column': 'Remaining_Amount', 'Description': 'مبلغ المتبقي الحالي (ريال)', 'Data Type': 'Decimal', 'Key': 'None', 'Source': 'Portfolio File'},
        {'Table': 'FactDebt', 'Column': 'Documented_Paid', 'Description': 'السدادات الموثقة بالشيت الأصلي', 'Data Type': 'Decimal', 'Key': 'None', 'Source': 'Portfolio File'},

        # FactPayment
        {'Table': 'FactPayment', 'Column': 'Payment_ID', 'Description': 'مفتاح السداد المركب الفريد (Primary Key)', 'Data Type': 'Text', 'Key': 'PK', 'Source': 'Matching Engine'},
        {'Table': 'FactPayment', 'Column': 'Customer_ID', 'Description': 'رقم هوية العميل المسدد', 'Data Type': 'Text', 'Key': 'FK', 'Source': 'Payment File'},
        {'Table': 'FactPayment', 'Column': 'Debt_ID', 'Description': 'معرف المديونية المطابقة', 'Data Type': 'Text', 'Key': 'FK', 'Source': 'Matching Engine'},
        {'Table': 'FactPayment', 'Column': 'Payment_Date', 'Description': 'تاريخ السداد الفعلي', 'Data Type': 'Date', 'Key': 'FK', 'Source': 'Payment File'},
        {'Table': 'FactPayment', 'Column': 'Payment_Amount', 'Description': 'قيمة مبلغ السداد المالي (ريال)', 'Data Type': 'Decimal', 'Key': 'None', 'Source': 'Payment File'},

        # DimCollector
        {'Table': 'DimCollector', 'Column': 'Collector_ID', 'Description': 'كود المحصل الفريد (Primary Key)', 'Data Type': 'Text', 'Key': 'PK', 'Source': 'System Engine'},
        {'Table': 'DimCollector', 'Column': 'Collector_Name', 'Description': 'اسم المحصل الكامل', 'Data Type': 'Text', 'Key': 'None', 'Source': 'Portfolio File'},

        # DimSupervisor
        {'Table': 'DimSupervisor', 'Column': 'Supervisor_ID', 'Description': 'كود المشرف الفريد (Primary Key)', 'Data Type': 'Text', 'Key': 'PK', 'Source': 'System Engine'},
        {'Table': 'DimSupervisor', 'Column': 'Supervisor_Name', 'Description': 'اسم المشرف المسؤول', 'Data Type': 'Text', 'Key': 'None', 'Source': 'Portfolio File'}
    ]
    return pd.DataFrame(dict_data)


def generate_data_model_doc_df() -> pd.DataFrame:
    """Generates Data Model Overview documentation DataFrame."""
    doc_data = [
        {'Architecture': 'Star Schema Dimensional Model', 'Component': 'DimCustomer', 'Role': 'Dimension', 'Granularity': '1 Row per Customer ID', 'Description': 'يحتوي على كافة بيانات وتصنيفات العميل'},
        {'Architecture': 'Star Schema Dimensional Model', 'Component': 'DimCollector', 'Role': 'Dimension', 'Granularity': '1 Row per Collector', 'Description': 'يحتوي على أسماء وتوزيعات المحصلين'},
        {'Architecture': 'Star Schema Dimensional Model', 'Component': 'DimSupervisor', 'Role': 'Dimension', 'Granularity': '1 Row per Supervisor', 'Description': 'يحتوي على هيكل المشرفين وإدارة الفرق'},
        {'Architecture': 'Star Schema Dimensional Model', 'Component': 'DimPortfolio', 'Role': 'Dimension', 'Granularity': '1 Row per Portfolio', 'Description': 'يحتوي على فئات ونطاقات المحافظ المعالجة'},
        {'Architecture': 'Star Schema Dimensional Model', 'Component': 'DimDate', 'Role': 'Dimension', 'Granularity': '1 Row per Date (Daily)', 'Description': 'جدول التاريخ والتقويم لـ Time Intelligence'},
        {'Architecture': 'Star Schema Dimensional Model', 'Component': 'FactDebt', 'Role': 'Fact Table', 'Granularity': '1 Row per Debt Record', 'Description': 'جدول حقائق المديونيات والرصيد المتبقي'},
        {'Architecture': 'Star Schema Dimensional Model', 'Component': 'FactPayment', 'Role': 'Fact Table', 'Granularity': '1 Row per Payment Transaction', 'Description': 'جدول حقائق حركة السداد والتحصيل الفعلي'}
    ]
    return pd.DataFrame(doc_data)
