import pandas as pd
from datetime import date

class PaymentMatcher:
    def match(self, portfolio_df: pd.DataFrame, payment_df: pd.DataFrame, 
              portfolio_col_map: dict, payment_col_map: dict, 
              date_from: date = None, date_to: date = None) -> dict:
        """
        Matches payments from payment_df into portfolio_df ensuring no double counting.
        """
        p_customer_col = portfolio_col_map.get('customer_id', 'رقم الهوية')
        p_debt_col = portfolio_col_map.get('debt_id', 'رقم المديونية')
        
        pay_customer_col = payment_col_map.get('customer_id', 'رقم الهوية')
        pay_amount_col = payment_col_map.get('payment_amount', 'مبلغ السداد')
        pay_date_col = payment_col_map.get('payment_date', 'تاريخ السداد')
        pay_debt_col = payment_col_map.get('debt_id', 'رقم المديونية')

        # Work on copies
        pdf = portfolio_df.copy()
        pay_df = payment_df.copy()

        # Normalize IDs
        if p_customer_col in pdf.columns:
            pdf['__join_cust'] = pdf[p_customer_col].astype(str).str.strip().str.lower()
        
        if pay_customer_col in pay_df.columns:
            pay_df['__join_cust'] = pay_df[pay_customer_col].astype(str).str.strip().str.lower()

        # Date filtering
        if pay_date_col in pay_df.columns and (date_from or date_to):
            try:
                pay_dates = pd.to_datetime(pay_df[pay_date_col], errors='coerce')
                mask = pd.Series(True, index=pay_df.index)
                if date_from:
                    mask = mask & (pay_dates >= pd.to_datetime(date_from))
                if date_to:
                    mask = mask & (pay_dates <= pd.to_datetime(date_to))
                pay_df = pay_df[mask]
            except Exception as e:
                pass

        # Ensure numeric amount
        pay_df['__pay_amount'] = pd.to_numeric(pay_df.get(pay_amount_col, 0), errors='coerce').fillna(0)

        # Aggregate Payments
        # We aggregate before joining to avoid double counting if a customer has multiple rows in portfolio
        if p_debt_col in pdf.columns and pay_debt_col in pay_df.columns:
            # We match on both if debt id is provided in payments
            pay_df['__join_debt'] = pay_df[pay_debt_col].astype(str).str.strip().str.lower()
            pdf['__join_debt'] = pdf[p_debt_col].astype(str).str.strip().str.lower()
            
            agg_pay = pay_df.groupby(['__join_cust', '__join_debt'])['__pay_amount'].sum().reset_index()
            pdf = pd.merge(pdf, agg_pay, on=['__join_cust', '__join_debt'], how='left')
        else:
            # Match on customer only
            agg_pay = pay_df.groupby('__join_cust')['__pay_amount'].sum().reset_index()
            pdf = pd.merge(pdf, agg_pay, on='__join_cust', how='left')

        pdf['__pay_amount'] = pdf['__pay_amount'].fillna(0)
        
        # Calculate stats
        total_paid = pay_df['__pay_amount'].sum()
        matched_paid = pdf['__pay_amount'].sum()
        
        # Customers who paid
        customers_who_paid = agg_pay['__join_cust'].nunique()
        total_customers = pdf['__join_cust'].nunique() if '__join_cust' in pdf.columns else 0

        # Unmatched payments
        if p_debt_col in pdf.columns and pay_debt_col in pay_df.columns:
            matched_keys = pdf[['__join_cust', '__join_debt']].drop_duplicates()
            unmatched_df = pd.merge(pay_df, matched_keys, on=['__join_cust', '__join_debt'], how='left', indicator=True)
            unmatched_df = unmatched_df[unmatched_df['_merge'] == 'left_only'].drop(columns=['_merge'])
        else:
            matched_keys = pdf[['__join_cust']].drop_duplicates()
            unmatched_df = pd.merge(pay_df, matched_keys, on='__join_cust', how='left', indicator=True)
            unmatched_df = unmatched_df[unmatched_df['_merge'] == 'left_only'].drop(columns=['_merge'])
            
        unmatched_paid = unmatched_df['__pay_amount'].sum()

        stats = {
            'total_paid': total_paid,
            'matched_paid': matched_paid,
            'unmatched_paid': unmatched_paid,
            'match_rate': (matched_paid / total_paid * 100) if total_paid > 0 else 0,
            'total_customers': total_customers,
            'customers_who_paid': customers_who_paid
        }
        
        # Clean up temporary columns
        cols_to_drop = [c for c in pdf.columns if c.startswith('__join_')]
        pdf = pdf.drop(columns=cols_to_drop)
        pdf = pdf.rename(columns={'__pay_amount': 'مبلغ السداد المطابق'})
        
        return {
            'matched_df': pdf,
            'unmatched_payments': unmatched_df,
            'stats': stats
        }
