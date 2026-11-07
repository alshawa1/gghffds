import pandas as pd
from redistribution.balance import BalanceEngine
from redistribution.validation import DistributionValidator

class DistributeEngine:
    @staticmethod
    def distribute_customers(
        pulled_df: pd.DataFrame,
        target_collectors: list[str],
        collector_info: pd.DataFrame,
        column_map: dict,
        balance_method: str = 'remaining_balance',
        allow_cross_portfolio: bool = False
    ) -> dict:
        """
        Distribute customers from pulled_df to target_collectors.
        """
        col_cust = column_map.get('customer_id', 'رقم الهوية')
        col_debt_id = column_map.get('debt_id', 'رقم المديونية')
        col_remaining = column_map.get('remaining', 'متبقي سداد موثق')
        col_portfolio = column_map.get('portfolio', 'المحافظ')
        
        collector_portfolio_map = dict(zip(collector_info['المحصل'], collector_info['المحافظ']))
        
        val_result = DistributionValidator.validate_before_distribution(
            pulled_df, target_collectors, column_map, collector_portfolio_map, allow_cross_portfolio=allow_cross_portfolio
        )
        
        if not val_result['can_proceed']:
            return {
                'distributed_df': pd.DataFrame(),
                'collector_summary': pd.DataFrame(),
                'portfolio_summary': pd.DataFrame(),
                'validation_errors': val_result['errors'],
                'success': False
            }
            
        # Group customers for balancing
        cust_group = pulled_df.groupby(col_cust).agg({
            col_portfolio: 'first',
            col_remaining: lambda x: x.head(1).sum(), # Just placeholder, we need unique per debt
        }).reset_index()
        
        # Proper remaining summation (since one customer can have multiple debts, but rows might be duplicated per debt? Actually the raw data has 1 row per debt usually, but just in case)
        # To be completely safe: group by customer and debt first
        unique_debts = pulled_df.drop_duplicates(subset=[col_cust, col_debt_id])
        cust_agg = unique_debts.groupby(col_cust).agg({
            col_portfolio: 'first',
            col_remaining: 'sum',
            col_debt_id: 'count'
        }).reset_index()
        
        cust_agg.rename(columns={
            col_cust: 'customer_id',
            col_portfolio: 'portfolio',
            col_remaining: 'remaining_balance',
            col_debt_id: 'debt_count'
        }, inplace=True)
        
        distribution_map = BalanceEngine.calculate_optimal_distribution(
            cust_agg, target_collectors, collector_portfolio_map, balance_method
        )
        
        # Flatten distribution map: customer_id -> collector
        cust_to_collector = {}
        for coll, custs in distribution_map.items():
            for cust in custs:
                cust_to_collector[cust] = coll
                
        distributed_df = pulled_df.copy()
        
        # Add new assignment columns
        distributed_df['المحصل الجديد'] = distributed_df[col_cust].map(cust_to_collector)
        
        # Map supervisor and user name
        collector_to_sup = dict(zip(collector_info['المحصل'], collector_info['المشرف']))
        collector_to_user = dict(zip(collector_info['المحصل'], collector_info['اسم المستخدم']))
        
        distributed_df['المشرف الجديد'] = distributed_df['المحصل الجديد'].map(collector_to_sup)
        distributed_df['اسم المستخدم الجديد'] = distributed_df['المحصل الجديد'].map(collector_to_user)
        
        # Summaries
        if not distributed_df.empty:
            sum_df = distributed_df.drop_duplicates(subset=[col_cust, col_debt_id])
            collector_summary = sum_df.groupby('المحصل الجديد').agg(
                العملاء=(col_cust, 'nunique'),
                المديونيات=(col_debt_id, 'count'),
                إجمالي_المتبقي=(col_remaining, 'sum')
            ).reset_index()
            
            portfolio_summary = distributed_df.groupby(col_portfolio).agg(
                العملاء=(col_cust, 'nunique'),
                المديونيات=(col_debt_id, 'nunique'),
                المحصلين=('المحصل الجديد', 'nunique')
            ).reset_index()
        else:
            collector_summary = pd.DataFrame()
            portfolio_summary = pd.DataFrame()
            
        return {
            'distributed_df': distributed_df,
            'collector_summary': collector_summary,
            'portfolio_summary': portfolio_summary,
            'validation_errors': val_result['warnings'],
            'success': True
        }
