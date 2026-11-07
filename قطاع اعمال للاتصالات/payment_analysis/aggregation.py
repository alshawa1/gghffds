import pandas as pd

class PaymentAggregator:
    @staticmethod
    def _base_aggregate(matched_df: pd.DataFrame, group_col: str, column_map: dict) -> pd.DataFrame:
        if matched_df.empty or group_col not in matched_df.columns:
            return pd.DataFrame()
            
        col_cust = column_map.get('customer_id', 'رقم الهوية')
        col_debt = column_map.get('debt_amount', 'مبلغ الميدونية')
        col_rem = column_map.get('remaining', 'متبقي سداد موثق')
        col_debt_id = column_map.get('debt_id', 'رقم المديونية')
        
        # 1. Customers info (to avoid double counting payment)
        cust_info = matched_df.drop_duplicates(subset=[col_cust]).copy()
        
        # 2. Debts info (to avoid double counting debt amounts)
        unique_debts = matched_df.drop_duplicates(subset=[col_cust, col_debt_id]).copy()
        
        # Payment column name (support both Arabic and English)
        pay_col = 'مبلغ السداد' if 'مبلغ السداد' in cust_info.columns else 'payment_total'
        
        # Payment sum per customer
        payment_by_group = cust_info.groupby(group_col)[pay_col].sum().reset_index()
        
        # Debt/remaining sum per debt
        debt_by_group = unique_debts.groupby(group_col).agg(
            العملاء=(col_cust, 'nunique'),
            المديونيات=(col_debt_id, 'count'),
            إجمالي_المديونية=(col_debt, 'sum'),
            إجمالي_المتبقي=(col_rem, 'sum')
        ).reset_index()
        
        res = pd.merge(debt_by_group, payment_by_group, on=group_col, how='left')
        res.rename(columns={pay_col: 'إجمالي_السداد', group_col: 'الكيان'}, inplace=True)
        
        res['نسبة_السداد'] = (res['إجمالي_السداد'] / res['إجمالي_المديونية']).fillna(0) * 100
        return res


    @staticmethod
    def aggregate_by_collector(matched_df: pd.DataFrame, column_map: dict) -> pd.DataFrame:
        col = column_map.get('collector', 'المحصل')
        df = PaymentAggregator._base_aggregate(matched_df, col, column_map)
        if not df.empty: df.rename(columns={'الكيان': 'المحصل'}, inplace=True)
        return df

    @staticmethod
    def aggregate_by_supervisor(matched_df: pd.DataFrame, column_map: dict) -> pd.DataFrame:
        col = column_map.get('supervisor', 'المشرف')
        df = PaymentAggregator._base_aggregate(matched_df, col, column_map)
        if not df.empty: df.rename(columns={'الكيان': 'المشرف'}, inplace=True)
        return df

    @staticmethod
    def aggregate_by_portfolio(matched_df: pd.DataFrame, column_map: dict) -> pd.DataFrame:
        col = column_map.get('portfolio', 'المحافظ')
        df = PaymentAggregator._base_aggregate(matched_df, col, column_map)
        if not df.empty: df.rename(columns={'الكيان': 'المحفظة'}, inplace=True)
        return df

    @staticmethod
    def aggregate_by_main_status(matched_df: pd.DataFrame, column_map: dict) -> pd.DataFrame:
        col = column_map.get('main_status', 'الحالة الرئيسية')
        df = PaymentAggregator._base_aggregate(matched_df, col, column_map)
        if not df.empty: df.rename(columns={'الكيان': 'الحالة الرئيسية'}, inplace=True)
        return df

    @staticmethod
    def aggregate_by_sub_status(matched_df: pd.DataFrame, column_map: dict) -> pd.DataFrame:
        col = column_map.get('sub_status', 'الحالة الفرعية')
        df = PaymentAggregator._base_aggregate(matched_df, col, column_map)
        if not df.empty: df.rename(columns={'الكيان': 'الحالة الفرعية'}, inplace=True)
        return df

    @staticmethod
    def aggregate_by_date(matched_df: pd.DataFrame, payment_col_map: dict, freq='D') -> pd.DataFrame:
        # Date based aggregation needs dates directly mapped or passed, keeping empty structure as requested.
        return pd.DataFrame()
