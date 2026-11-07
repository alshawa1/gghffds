import pandas as pd

class PaymentMatcher:
    @staticmethod
    def match_payments(
        portfolio_df: pd.DataFrame,
        payment_df: pd.DataFrame,
        portfolio_col_map: dict,
        payment_col_map: dict,
        date_from: str = None,
        date_to: str = None,
        match_by_debt: bool = False
    ) -> dict:
        """
        CRITICAL: Aggregate payments BEFORE joining to prevent double counting.
        """
        p_cust = portfolio_col_map.get('customer_id', 'رقم الهوية')
        p_debt = portfolio_col_map.get('debt_id', 'رقم المديونية')
        
        pay_cust = payment_col_map.get('customer_id', 'رقم الهوية')
        pay_debt = payment_col_map.get('debt_id', 'رقم المديونية')
        pay_amt = payment_col_map.get('amount', 'مبلغ السداد')
        pay_date = payment_col_map.get('date', 'تاريخ السداد')
        
        # 1. Filter by date if provided
        pay_df = payment_df.copy()
        if date_from and date_to and pay_date in pay_df.columns:
            pay_df[pay_date] = pd.to_datetime(pay_df[pay_date], errors='coerce')
            pay_df = pay_df[(pay_df[pay_date] >= pd.to_datetime(date_from)) & (pay_df[pay_date] <= pd.to_datetime(date_to))]
            
        # 2. Normalize customer IDs
        pay_df[pay_cust] = pay_df[pay_cust].astype(str).str.strip()
        port_df = portfolio_df.copy()
        port_df[p_cust] = port_df[p_cust].astype(str).str.strip()
        
        if match_by_debt and pay_debt in pay_df.columns and p_debt in port_df.columns:
            pay_df[pay_debt] = pay_df[pay_debt].astype(str).str.strip()
            port_df[p_debt] = port_df[p_debt].astype(str).str.strip()
            # 3. Aggregate payments by customer and debt
            agg_pay = pay_df.groupby([pay_cust, pay_debt])[pay_amt].sum().reset_index()
            agg_pay.rename(columns={pay_cust: p_cust, pay_debt: p_debt, pay_amt: 'payment_total'}, inplace=True)
            # 4. Join
            matched_df = pd.merge(port_df, agg_pay, on=[p_cust, p_debt], how='left')
        else:
            # 3. Aggregate payments by customer
            agg_pay = pay_df.groupby(pay_cust)[pay_amt].sum().reset_index()
            agg_pay.rename(columns={pay_cust: p_cust, pay_amt: 'payment_total'}, inplace=True)
            # 4. Join
            matched_df = pd.merge(port_df, agg_pay, on=p_cust, how='left')
            
        matched_df['payment_total'] = matched_df['payment_total'].fillna(0)
        # Rename payment column to Arabic name
        matched_df.rename(columns={'payment_total': 'مبلغ السداد'}, inplace=True)
        
        # Unmatched payments
        unmatched_mask = ~pay_df[pay_cust].isin(port_df[p_cust])
        unmatched_payments = pay_df[unmatched_mask]
        
        # Stats
        total_paid_in_portfolio = agg_pay[agg_pay[p_cust].isin(port_df[p_cust])]['payment_total'].sum()
        total_raw = pay_df[pay_amt].sum() if not pay_df.empty else 0
        match_rate = (total_paid_in_portfolio / total_raw * 100) if total_raw > 0 else 0.0
        stats = {
            'total_payments_raw': total_raw,
            'total_matched': total_paid_in_portfolio,
            'matched_paid': total_paid_in_portfolio,
            'total_unmatched': unmatched_payments[pay_amt].sum() if not unmatched_payments.empty else 0,
            'unique_customers_paid': agg_pay[agg_pay[p_cust].isin(port_df[p_cust])].shape[0] if not agg_pay.empty else 0,
            'match_rate': round(float(match_rate), 2)
        }
        
        return {
            'matched_df': matched_df,
            'unmatched_payments': unmatched_payments,
            'stats': stats
        }
