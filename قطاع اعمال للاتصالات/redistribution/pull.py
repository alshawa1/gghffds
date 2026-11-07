import pandas as pd

class PullEngine:
    @staticmethod
    def pull_customers(df: pd.DataFrame, source_collectors: list[str], column_map: dict,
                       selected_statuses: list[str] = None,
                       source_supervisors: list[str] = None) -> dict:
        """
        Pull all customers from selected source collectors/supervisors, optionally filtered by Main Status.
        - Groups customers by رقم الهوية (customer = identity, not row)
        - All debt rows for a customer come together
        - Returns unique customers with all their debt rows
        """
        col_cust = column_map.get('customer_id', 'رقم الهوية')
        col_debt_id = column_map.get('debt_id', 'رقم المديونية')
        col_debt_amt = column_map.get('debt_amount', 'مبلغ الميدونية')
        if col_debt_amt not in df.columns and 'مبلغ المديونية' in df.columns:
            col_debt_amt = 'مبلغ المديونية'
        col_remaining = column_map.get('remaining_doc', 'متبقي سداد موثق')
        if col_remaining not in df.columns and '_remaining_doc' in df.columns:
            col_remaining = '_remaining_doc'
        col_portfolio = column_map.get('portfolio', 'المحافظ')
        col_collector = column_map.get('collector', 'المحصل')
        col_supervisor = column_map.get('supervisor', 'المشرف')
        col_status = column_map.get('main_status', 'الحالة الرئيسية')

        # Filter by collectors / supervisors
        source_df = df.copy()
        if source_collectors:
            source_df = source_df[source_df[col_collector].isin(source_collectors)]
        if source_supervisors and col_supervisor in source_df.columns:
            source_df = source_df[source_df[col_supervisor].isin(source_supervisors)]

        # Filter by Main Status if provided
        if selected_statuses and col_status in source_df.columns:
            source_df = source_df[source_df[col_status].isin(selected_statuses)]

        unique_customers = source_df[col_cust].unique().tolist() if col_cust in source_df.columns else []
        
        # Pull ALL rows for these customers to keep them together
        pulled_df = df[df[col_cust].isin(unique_customers)].copy() if (col_cust in df.columns and unique_customers) else pd.DataFrame()
        
        # Calculate totals safely by dropping duplicates of debt records
        unique_debts_df = pulled_df.drop_duplicates(subset=[col_cust, col_debt_id]) if (not pulled_df.empty and col_cust in pulled_df.columns and col_debt_id in pulled_df.columns) else pulled_df
        
        total_debt = unique_debts_df[col_debt_amt].sum() if (not unique_debts_df.empty and col_debt_amt in unique_debts_df.columns) else 0.0
        total_remaining = unique_debts_df[col_remaining].sum() if (not unique_debts_df.empty and col_remaining in unique_debts_df.columns) else 0.0
        
        portfolio_breakdown = {}
        if col_portfolio in pulled_df.columns and not pulled_df.empty:
            for p, p_group in pulled_df.groupby(col_portfolio):
                p_unique = p_group.drop_duplicates(subset=[col_cust, col_debt_id]) if (col_cust in p_group.columns and col_debt_id in p_group.columns) else p_group
                portfolio_breakdown[p] = {
                    'customers': p_group[col_cust].nunique() if col_cust in p_group.columns else len(p_group),
                    'debts': p_unique.shape[0],
                    'remaining': float(p_unique[col_remaining].sum()) if col_remaining in p_unique.columns else 0.0
                }
                
        source_summary = []
        if not pulled_df.empty and col_collector in pulled_df.columns:
            for c, c_group in pulled_df.groupby(col_collector):
                c_unique = c_group.drop_duplicates(subset=[col_cust, col_debt_id]) if (col_cust in c_group.columns and col_debt_id in c_group.columns) else c_group
                source_summary.append({
                    'collector': c,
                    'customers': c_group[col_cust].nunique() if col_cust in c_group.columns else len(c_group),
                    'debts': c_unique.shape[0],
                    'debt_amount': float(c_unique[col_debt_amt].sum()) if col_debt_amt in c_unique.columns else 0.0,
                    'remaining': float(c_unique[col_remaining].sum()) if col_remaining in c_unique.columns else 0.0
                })
            
        return {
            'pulled_df': pulled_df,
            'unique_customers': unique_customers,
            'customer_count': len(unique_customers),
            'unique_debts': unique_debts_df.shape[0] if not pulled_df.empty else 0,
            'total_debt': float(total_debt),
            'total_remaining': float(total_remaining),
            'portfolio_breakdown': portfolio_breakdown,
            'source_summary': source_summary
        }
