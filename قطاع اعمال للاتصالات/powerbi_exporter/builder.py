"""
powerbi_exporter/builder.py
============================
Star Schema Data Model Builder for Power BI Export.
Converts clean_df portfolio and payment_df into Star Schema DataFrames.
"""
import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Optional, Dict


def build_star_schema(clean_df: pd.DataFrame, col_map: Dict[str, str],
                      payment_df: Optional[pd.DataFrame] = None,
                      payment_map: Optional[Dict[str, str]] = None) -> Dict[str, pd.DataFrame]:
    """
    Builds Star Schema DataFrames from cleaned portfolio and payment data.

    Returns dictionary of DataFrames:
        - DimCustomer
        - DimCollector
        - DimSupervisor
        - DimPortfolio
        - DimCase
        - DimDate
        - FactDebt
        - FactPayment
        - Customer_Payment_History
        - Daily_Snapshots
        - Unmatched_Payments
        - Data_Quality
    """
    df = clean_df.copy()

    # Determine column names safely
    cust_col = col_map.get('customer_id') or ('_customer_id' if '_customer_id' in df.columns else 'رقم الهوية')
    debt_col = col_map.get('debt_amount') or ('مبلغ المديونية' if 'مبلغ المديونية' in df.columns else 'مبلغ الميدونية')
    rem_col  = col_map.get('remaining_doc') or ('متبقي سداد موثق' if 'متبقي سداد موثق' in df.columns else '_remaining_doc')
    paid_col = col_map.get('paid_doc') or ('السدادات الموثقة' if 'السدادات الموثقة' in df.columns else '_paid_doc')
    port_col = col_map.get('portfolio') or ('المافظ' if 'المحافظ' in df.columns else '_portfolio')
    coll_col = col_map.get('collector') or ('المحصل' if 'المحصل' in df.columns else '_collector')
    sup_col  = col_map.get('supervisor') or ('المشرف' if 'المشرف' in df.columns else '_supervisor')
    m_status_col = col_map.get('main_status') or ('الحالة الرئيسية' if 'الحالة الرئيسية' in df.columns else '_main_status')
    s_status_col = col_map.get('sub_status') or ('الحالة الفرعية' if 'الحالة الفرعية' in df.columns else '_sub_status')
    date_col = col_map.get('followup_date') or ('تاريخ المتابعة' if 'تاريخ المتابعة' in df.columns else '_followup_date')

    # Ensure helper string columns exist
    df['__cust_id'] = df[cust_col].astype(str).str.strip() if cust_col in df.columns else df.index.astype(str)
    df['__portfolio'] = df[port_col].astype(str).str.strip() if port_col in df.columns else 'المحفظة العامة'
    df['__collector'] = df[coll_col].astype(str).str.strip() if coll_col in df.columns else 'غير محدد'
    df['__supervisor'] = df[sup_col].astype(str).str.strip() if sup_col in df.columns else 'غير محدد'
    df['__main_status'] = df[m_status_col].astype(str).str.strip() if m_status_col in df.columns else 'غير محدد'
    df['__sub_status'] = df[s_status_col].astype(str).str.strip() if s_status_col in df.columns else 'غير محدد'

    # Numeric clean
    df['__debt_amt'] = pd.to_numeric(df[debt_col], errors='coerce').fillna(0.0) if debt_col in df.columns else 0.0
    df['__rem_amt']  = pd.to_numeric(df[rem_col], errors='coerce').fillna(0.0) if rem_col in df.columns else 0.0
    df['__paid_amt'] = pd.to_numeric(df[paid_col], errors='coerce').fillna(0.0) if paid_col in df.columns else 0.0

    # Date clean
    import warnings
    if date_col in df.columns:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            df['__followup_date'] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True).dt.strftime('%Y-%m-%d')
    else:
        df['__followup_date'] = None

    # -------------------------------------------------------------
    # 1. DimCustomer (Unique Customer ID)
    # -------------------------------------------------------------
    cust_unique = df.drop_duplicates(subset=['__cust_id']).copy()
    dim_customer = pd.DataFrame({
        'Customer_ID': cust_unique['__cust_id'],
        'Customer_Name': cust_unique['__cust_id'].apply(lambda c: f"عميل {c}"),
        'Portfolio_Name': cust_unique['__portfolio'],
        'Main_Status': cust_unique['__main_status'],
        'Sub_Status': cust_unique['__sub_status'],
        'Followup_Date': cust_unique['__followup_date']
    }).reset_index(drop=True)

    # -------------------------------------------------------------
    # 2. DimCollector
    # -------------------------------------------------------------
    coll_unique = df[['__collector', '__supervisor']].drop_duplicates(subset=['__collector']).copy()
    dim_collector = pd.DataFrame({
        'Collector_ID': coll_unique['__collector'].apply(lambda c: f"COLL_{hash(c) & 0xFFFFFF}"),
        'Collector_Name': coll_unique['__collector'],
        'Supervisor_Name': coll_unique['__supervisor']
    }).reset_index(drop=True)
    coll_map_dict = dict(zip(dim_collector['Collector_Name'], dim_collector['Collector_ID']))

    # -------------------------------------------------------------
    # 3. DimSupervisor
    # -------------------------------------------------------------
    sup_unique = df['__supervisor'].drop_duplicates().copy()
    dim_supervisor = pd.DataFrame({
        'Supervisor_ID': sup_unique.apply(lambda s: f"SUP_{hash(s) & 0xFFFFFF}"),
        'Supervisor_Name': sup_unique
    }).reset_index(drop=True)
    sup_map_dict = dict(zip(dim_supervisor['Supervisor_Name'], dim_supervisor['Supervisor_ID']))

    # -------------------------------------------------------------
    # 4. DimPortfolio
    # -------------------------------------------------------------
    port_unique = df['__portfolio'].drop_duplicates().copy()
    dim_portfolio = pd.DataFrame({
        'Portfolio_ID': port_unique.apply(lambda p: f"PORT_{hash(p) & 0xFFFFFF}"),
        'Portfolio_Name': port_unique
    }).reset_index(drop=True)
    port_map_dict = dict(zip(dim_portfolio['Portfolio_Name'], dim_portfolio['Portfolio_ID']))

    # -------------------------------------------------------------
    # 5. DimCase
    # -------------------------------------------------------------
    case_unique = df[['__main_status', '__sub_status']].drop_duplicates().copy()
    dim_case = pd.DataFrame({
        'Case_ID': [f"CASE_{i+1:03d}" for i in range(len(case_unique))],
        'Main_Case': case_unique['__main_status'],
        'Sub_Case': case_unique['__sub_status']
    }).reset_index(drop=True)
    case_map_dict = dict(zip(zip(dim_case['Main_Case'], dim_case['Sub_Case']), dim_case['Case_ID']))

    # -------------------------------------------------------------
    # 6. FactDebt
    # -------------------------------------------------------------
    fact_debt = pd.DataFrame({
        'Debt_ID': [f"DEBT_{i+1:06d}" for i in range(len(df))],
        'Customer_ID': df['__cust_id'],
        'Portfolio_ID': df['__portfolio'].map(port_map_dict),
        'Collector_ID': df['__collector'].map(coll_map_dict),
        'Supervisor_ID': df['__supervisor'].map(sup_map_dict),
        'Case_ID': [case_map_dict.get((m, s), 'CASE_001') for m, s in zip(df['__main_status'], df['__sub_status'])],
        'Debt_Amount': df['__debt_amt'],
        'Remaining_Amount': df['__rem_amt'],
        'Documented_Remaining': df['__rem_amt'],
        'Documented_Paid': df['__paid_amt'],
        'Delinquency_Date': df['__followup_date'],
        'Main_Case': df['__main_status'],
        'Sub_Case': df['__sub_status'],
        'Followup_Date': df['__followup_date']
    }).reset_index(drop=True)

    # -------------------------------------------------------------
    # 7. FactPayment & UnmatchedPayments
    # -------------------------------------------------------------
    fact_payment_rows = []
    unmatched_rows = []

    if payment_df is not None and not payment_df.empty:
        pay_df = payment_df.copy()
        pmap = payment_map or {}

        p_cust_col = pmap.get('customer_id') or ('_customer_id' if '_customer_id' in pay_df.columns else 'رقم الهوية')
        p_amt_col  = pmap.get('payment_amount') or ('مبلغ السداد' if 'مبلغ السداد' in pay_df.columns else '_payment_amount')
        p_date_col = pmap.get('payment_date') or ('تاريخ السداد' if 'تاريخ السداد' in pay_df.columns else '_payment_date')
        p_coll_col = pmap.get('collector') or ('المحصل' if 'المحصل' in pay_df.columns else '_collector')

        pay_df['__cust'] = pay_df[p_cust_col].astype(str).str.strip() if p_cust_col in pay_df.columns else ''
        pay_df['__amt']  = pd.to_numeric(pay_df[p_amt_col], errors='coerce').fillna(0.0) if p_amt_col in pay_df.columns else 0.0
        if p_date_col in pay_df.columns:
            pay_df['__date'] = pd.to_datetime(pay_df[p_date_col], errors='coerce', dayfirst=True).dt.strftime('%Y-%m-%d')
        else:
            pay_df['__date'] = datetime.today().strftime('%Y-%m-%d')

        pay_df['__coll'] = pay_df[p_coll_col].astype(str).str.strip() if p_coll_col in pay_df.columns else 'غير محدد'

        # Map to customer debt
        cust_debt_map = fact_debt.set_index('Customer_ID')

        for idx, row in pay_df.iterrows():
            c_id = row['__cust']
            amt = row['__amt']
            pdate = row['__date'] or datetime.today().strftime('%Y-%m-%d')
            coll_name = row['__coll']

            # Unique composite key: Customer_ID * Debt_ID * Date * Amount * Index
            if c_id in cust_debt_map.index:
                debt_match = cust_debt_map.loc[c_id]
                if isinstance(debt_match, pd.DataFrame):
                    debt_match = debt_match.iloc[0]
                
                d_id = debt_match['Debt_ID']
                port_id = debt_match['Portfolio_ID']
                sup_id = debt_match['Supervisor_ID']
                coll_id = coll_map_dict.get(coll_name, debt_match['Collector_ID'])
                m_case = debt_match['Main_Case']
                s_case = debt_match['Sub_Case']

                comp_key = f"PAY_{c_id}_{d_id}_{pdate}_{int(amt)}_{idx+1}"
                fact_payment_rows.append({
                    'Payment_ID': comp_key,
                    'Customer_ID': c_id,
                    'Debt_ID': d_id,
                    'Payment_Date': pdate,
                    'Payment_Amount': amt,
                    'Collector_ID': coll_id,
                    'Supervisor_ID': sup_id,
                    'Portfolio_ID': port_id,
                    'Main_Case': m_case,
                    'Sub_Case': s_case
                })
            else:
                unmatched_rows.append({
                    'Payment_ID': f"UNMATCHED_{c_id}_{pdate}_{int(amt)}_{idx+1}",
                    'Customer_ID': c_id,
                    'Payment_Date': pdate,
                    'Payment_Amount': amt,
                    'Collector_Name': coll_name,
                    'Reason': 'عميل سداد غير موجود في محفظة الديون'
                })

    fact_payment = pd.DataFrame(fact_payment_rows) if fact_payment_rows else pd.DataFrame(columns=[
        'Payment_ID', 'Customer_ID', 'Debt_ID', 'Payment_Date', 'Payment_Amount',
        'Collector_ID', 'Supervisor_ID', 'Portfolio_ID', 'Main_Case', 'Sub_Case'
    ])

    unmatched_payments = pd.DataFrame(unmatched_rows) if unmatched_rows else pd.DataFrame(columns=[
        'Payment_ID', 'Customer_ID', 'Payment_Date', 'Payment_Amount', 'Collector_Name', 'Reason'
    ])

    # -------------------------------------------------------------
    # 8. DimDate
    # -------------------------------------------------------------
    all_dates = []
    if not fact_debt['Followup_Date'].isna().all():
        all_dates.extend(pd.to_datetime(fact_debt['Followup_Date'].dropna()).tolist())
    if not fact_payment.empty and not fact_payment['Payment_Date'].isna().all():
        all_dates.extend(pd.to_datetime(fact_payment['Payment_Date'].dropna()).tolist())

    if all_dates:
        min_date = min(all_dates)
        max_date = max(all_dates)
    else:
        min_date = datetime(2025, 1, 1)
        max_date = datetime(2026, 12, 31)

    # Pad date range slightly
    min_date = min_date - pd.Timedelta(days=30)
    max_date = max_date + pd.Timedelta(days=30)
    date_series = pd.date_range(start=min_date, end=max_date, freq='D')

    today_str = datetime.today().strftime('%Y-%m')

    dim_date = pd.DataFrame({
        'Date': date_series.strftime('%Y-%m-%d'),
        'Day': date_series.day,
        'Day_Name': date_series.day_name(),
        'Month': date_series.month,
        'Month_Number': date_series.month,
        'Month_Name': date_series.month_name(),
        'Quarter': [f"Q{q}" for q in date_series.quarter],
        'Year': date_series.year,
        'Year_Month': date_series.strftime('%Y-%m'),
        'Week': date_series.isocalendar().week,
        'Week_Number': date_series.isocalendar().week,
        'Is_Current_Month': date_series.strftime('%Y-%m') == today_str,
        'Is_Current_Year': date_series.year == datetime.today().year
    }).reset_index(drop=True)

    # -------------------------------------------------------------
    # 9. Customer_Payment_History (Customer 360)
    # -------------------------------------------------------------
    cust_history_rows = []
    cust_grp = fact_debt.groupby('Customer_ID')

    pay_grp = fact_payment.groupby('Customer_ID') if not fact_payment.empty else None

    for c_id, d_rows in cust_grp:
        t_debt = d_rows['Debt_Amount'].sum()
        t_rem = d_rows['Remaining_Amount'].sum()

        p_amt = 0.0
        p_cnt = 0
        first_p = None
        last_p = None

        if pay_grp and c_id in pay_grp.groups:
            p_rows = pay_grp.get_group(c_id)
            p_amt = p_rows['Payment_Amount'].sum()
            p_cnt = len(p_rows)
            p_dates = sorted(p_rows['Payment_Date'].dropna().tolist())
            if p_dates:
                first_p = p_dates[0]
                last_p = p_dates[-1]

        paid_pct = round((p_amt / t_debt * 100), 1) if t_debt > 0 else 0.0
        prob_score = round(min(1.0, (paid_pct / 100.0) * 0.7 + (1.0 if p_cnt > 0 else 0.0) * 0.3), 2)
        prob_cat = 'مرتفع جدأ' if prob_score >= 0.8 else ('متوسط' if prob_score >= 0.4 else 'منخفض')

        cust_history_rows.append({
            'Customer_ID': c_id,
            'Total_Debt': t_debt,
            'Total_Paid': p_amt,
            'Total_Remaining': t_rem,
            'Payment_Percentage': paid_pct,
            'Payment_Count': p_cnt,
            'First_Payment_Date': first_p,
            'Last_Payment_Date': last_p,
            'Average_Payment': round(p_amt / p_cnt, 2) if p_cnt > 0 else 0.0,
            'Payment_Probability_Score': prob_score,
            'Probability_Category': prob_cat
        })

    cust_payment_history = pd.DataFrame(cust_history_rows) if cust_history_rows else pd.DataFrame(columns=[
        'Customer_ID', 'Total_Debt', 'Total_Paid', 'Total_Remaining', 'Payment_Percentage',
        'Payment_Count', 'First_Payment_Date', 'Last_Payment_Date', 'Average_Payment',
        'Payment_Probability_Score', 'Probability_Category'
    ])

    # -------------------------------------------------------------
    # 10. Daily_Snapshots
    # -------------------------------------------------------------
    daily_snap_rows = []
    if not dim_date.empty:
        # Group debts & payments by date
        valid_dates = dim_date['Date'].head(30).tolist()
        for d in valid_dates:
            daily_snap_rows.append({
                'Snapshot_Date': d,
                'Total_Active_Customers': len(dim_customer),
                'Total_Outstanding_Debt': fact_debt['Remaining_Amount'].sum(),
                'Daily_Collection': fact_payment[fact_payment['Payment_Date'] == d]['Payment_Amount'].sum() if not fact_payment.empty else 0.0
            })
    daily_snapshots = pd.DataFrame(daily_snap_rows)

    # -------------------------------------------------------------
    # 11. Data_Quality Audit Log
    # -------------------------------------------------------------
    dq_rows = []
    # Check duplicate customer IDs
    dup_cust = df['__cust_id'].duplicated().sum()
    if dup_cust > 0:
        dq_rows.append({
            'Issue_Type': 'تكرار رقم الهوية في المحفظة',
            'Severity': 'Medium',
            'Count': dup_cust,
            'Description': f'يوجد {dup_cust} مديونية مكررة لنفس العملاء تم تجميعهم تحت نفس DimCustomer'
        })

    # Check null customer IDs
    null_cust = (df['__cust_id'] == '').sum()
    if null_cust > 0:
        dq_rows.append({
            'Issue_Type': 'رقم هوية مفقود',
            'Severity': 'High',
            'Count': null_cust,
            'Description': f'يوجد {null_cust} سجل بدون رقم هوية'
        })

    if unmatched_rows:
        dq_rows.append({
            'Issue_Type': 'سدادات غير مطابقة للمحفظة',
            'Severity': 'Medium',
            'Count': len(unmatched_rows),
            'Description': f'يوجد {len(unmatched_rows)} عملية سداد لعملاء غير موجودين في المحفظة الحالية'
        })

    if not dq_rows:
        dq_rows.append({
            'Issue_Type': 'سليم 100%',
            'Severity': 'Info',
            'Count': 0,
            'Description': 'جميع البيانات اجتازت فحوصات جودة البيانات بنجاح تام بدون أي أخطاء'
        })

    data_quality = pd.DataFrame(dq_rows)

    return {
        'DimCustomer': dim_customer,
        'DimCollector': dim_collector,
        'DimSupervisor': dim_supervisor,
        'DimPortfolio': dim_portfolio,
        'DimCase': dim_case,
        'DimDate': dim_date,
        'FactDebt': fact_debt,
        'FactPayment': fact_payment,
        'Customer_Payment_History': cust_payment_history,
        'Daily_Snapshots': daily_snapshots,
        'Unmatched_Payments': unmatched_payments,
        'Data_Quality': data_quality
    }
