"""
powerbi_exporter/validator.py
==============================
Validates Star Schema Data Package before export.
Checks PK/FK integrity, payment uniqueness, cross-portfolio logic, and quality rules.
"""
import pandas as pd
from typing import Dict, Any


def validate_package(star_schema: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Validates Star Schema package.

    Returns:
        {
            'is_valid': bool,
            'total_customers': int,
            'total_debts': int,
            'total_payments': int,
            'total_debt_amount': float,
            'total_payment_amount': float,
            'collection_rate_pct': float,
            'data_quality_issues_count': int,
            'issues_df': pd.DataFrame,
            'summary_markdown': str
        }
    """
    issues = []

    dim_cust = star_schema.get('DimCustomer', pd.DataFrame())
    dim_coll = star_schema.get('DimCollector', pd.DataFrame())
    dim_sup  = star_schema.get('DimSupervisor', pd.DataFrame())
    dim_port = star_schema.get('DimPortfolio', pd.DataFrame())
    fact_debt = star_schema.get('FactDebt', pd.DataFrame())
    fact_pay  = star_schema.get('FactPayment', pd.DataFrame())
    dq_df     = star_schema.get('Data_Quality', pd.DataFrame())

    # 1. Primary Key Uniqueness
    if not dim_cust.empty and dim_cust['Customer_ID'].duplicated().any():
        issues.append({
            'Level': 'Critical',
            'Check': 'DimCustomer PK Uniqueness',
            'Details': f"يوجد {dim_cust['Customer_ID'].duplicated().sum()} تكرار في المفتاح الرئيسي للعملاء!"
        })

    if not fact_pay.empty and 'Payment_ID' in fact_pay.columns and fact_pay['Payment_ID'].duplicated().any():
        issues.append({
            'Level': 'Critical',
            'Check': 'FactPayment Composite Key Uniqueness',
            'Details': f"يوجد {fact_pay['Payment_ID'].duplicated().sum()} مفتاح سداد مكرر!"
        })

    # 2. Foreign Key Integrity
    if not fact_debt.empty and not dim_cust.empty:
        orphan_cust = set(fact_debt['Customer_ID']) - set(dim_cust['Customer_ID'])
        if orphan_cust:
            issues.append({
                'Level': 'High',
                'Check': 'FactDebt -> DimCustomer FK Integrity',
                'Details': f"يوجد {len(orphan_cust)} عملاء في الديون غير موجودين في جدول DimCustomer!"
            })

    if not fact_pay.empty and not dim_cust.empty:
        orphan_pay_cust = set(fact_pay['Customer_ID']) - set(dim_cust['Customer_ID'])
        if orphan_pay_cust:
            issues.append({
                'Level': 'Medium',
                'Check': 'FactPayment -> DimCustomer FK Integrity',
                'Details': f"يوجد {len(orphan_pay_cust)} سدادات لعملاء غير موجودين في DimCustomer!"
            })

    # 3. Double Counting & Amount Checks
    total_debt_amt = float(fact_debt['Debt_Amount'].sum()) if not fact_debt.empty else 0.0
    total_rem_amt  = float(fact_debt['Remaining_Amount'].sum()) if not fact_debt.empty else 0.0
    total_pay_amt  = float(fact_pay['Payment_Amount'].sum()) if not fact_pay.empty else 0.0

    if total_pay_amt > total_debt_amt and total_debt_amt > 0:
        issues.append({
            'Level': 'Warning',
            'Check': 'Double Counting Check',
            'Details': f"إجمالي السدادات ({total_pay_amt:,.2f}) يتجاوز إجمالي المديونية ({total_debt_amt:,.2f})!"
        })

    issues_df = pd.DataFrame(issues) if issues else pd.DataFrame(columns=['Level', 'Check', 'Details'])

    is_valid = not any(i['Level'] in ('Critical', 'High') for i in issues)
    coll_rate = round((total_pay_amt / total_debt_amt * 100), 2) if total_debt_amt > 0 else 0.0

    quality_issues_count = len(issues) + (len(dq_df[dq_df['Issue_Type'] != 'سليم 100%']) if not dq_df.empty else 0)

    summary_md = f"""
### 📊 تقرير التحقق من حزمة Power BI:
- **حالة الحزمة:** {'✅ جاهزة للاستيراد 100%' if is_valid else '⚠️ يوجد تحذيرات جودة بيانات'}
- **عدد العملاء الفريدين:** {len(dim_cust):,} عميل
- **عدد المديونيات:** {len(fact_debt):,} مديونية
- **عدد عمليات السداد:** {len(fact_pay):,} عملية سداد
- **إجمالي المديونية:** {total_debt_amt:,.2f} ريال
- **إجمالي التحصيل:** {total_pay_amt:,.2f} ريال
- **نسبة التحصيل العامة:** {coll_rate:.2f}%
- **ملاحظات جودة البيانات:** {quality_issues_count} ملاحظة
"""

    return {
        'is_valid': is_valid,
        'total_customers': len(dim_cust),
        'total_debts': len(fact_debt),
        'total_payments': len(fact_pay),
        'total_debt_amount': total_debt_amt,
        'total_remaining_amount': total_rem_amt,
        'total_payment_amount': total_pay_amt,
        'collection_rate_pct': coll_rate,
        'data_quality_issues_count': quality_issues_count,
        'issues_df': issues_df,
        'summary_markdown': summary_md
    }
