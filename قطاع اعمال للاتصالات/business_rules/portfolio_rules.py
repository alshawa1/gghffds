import pandas as pd

class PortfolioRules:
    @staticmethod
    def validate_transfer(customer_id: str, customer_portfolio: str, target_collector: str, collector_portfolio_map: dict) -> tuple[bool, str]:
        """
        Validates if transferring a customer to a target collector violates Portfolio Isolation Rules.
        """
        target_portfolios = collector_portfolio_map.get(target_collector, [])
        if isinstance(target_portfolios, str):
            target_portfolios = [target_portfolios]

        if not target_portfolios:
            return False, f"المحصل {target_collector} غير معين على أي محفظة"

        if customer_portfolio not in target_portfolios:
            return False, f"لا يمكن النقل: العميل ينتمي لمحفظة {customer_portfolio} والمحصل يعمل على محافظ {target_portfolios}"

        return True, ""

    @staticmethod
    def get_customer_portfolio(customer_id: str, df: pd.DataFrame, column_map: dict) -> str:
        """
        Gets the portfolio for a specific customer. Assumes customer stays in one portfolio.
        """
        customer_col = column_map.get('customer_id', 'رقم الهوية')
        portfolio_col = column_map.get('portfolio', 'المحافظ')

        customer_rows = df[df[customer_col] == customer_id]
        if customer_rows.empty:
            return None

        # Get first non-null portfolio
        portfolios = customer_rows[portfolio_col].dropna().unique()
        return portfolios[0] if len(portfolios) > 0 else None

    @staticmethod
    def group_by_portfolio(df: pd.DataFrame, column_map: dict) -> dict:
        """
        Groups dataframe by portfolio.
        """
        portfolio_col = column_map.get('portfolio', 'المحافظ')
        if portfolio_col not in df.columns:
            return {}

        return {str(portfolio): group for portfolio, group in df.groupby(portfolio_col) if pd.notna(portfolio)}

    @staticmethod
    def get_portfolio_stats(df: pd.DataFrame, column_map: dict) -> pd.DataFrame:
        """
        Calculates statistics per portfolio.
        """
        portfolio_col = column_map.get('portfolio', 'المحافظ')
        customer_col = column_map.get('customer_id', 'رقم الهوية')
        debt_col = column_map.get('debt_id', 'رقم المديونية')
        debt_amt_col = column_map.get('debt_amount', 'مبلغ الميدونية')
        paid_col = column_map.get('paid_doc', 'السدادات الموثقة')
        remaining_col = column_map.get('remaining_doc', 'متبقي سداد موثق')
        collector_col = column_map.get('collector', 'المحصل')
        supervisor_col = column_map.get('supervisor', 'المشرف')

        if portfolio_col not in df.columns:
            return pd.DataFrame()

        stats = []
        for port, group in df.groupby(portfolio_col):
            if pd.isna(port):
                continue

            unique_customers = group[customer_col].nunique() if customer_col in group.columns else 0
            unique_debts = group[debt_col].nunique() if debt_col in group.columns else len(group)
            tot_debt = group[debt_amt_col].sum() if debt_amt_col in group.columns else 0.0
            tot_paid = group[paid_col].sum() if paid_col in group.columns else 0.0
            tot_rem = group[remaining_col].sum() if remaining_col in group.columns else 0.0

            rate = (tot_paid / tot_debt * 100) if tot_debt > 0 else 0.0

            collectors = group[collector_col].nunique() if collector_col in group.columns else 0
            supervisors = group[supervisor_col].nunique() if supervisor_col in group.columns else 0

            stats.append({
                'المحفظة': str(port),
                'عدد العملاء': unique_customers,
                'عدد المديونيات': unique_debts,
                'إجمالي المديونية': tot_debt,
                'إجمالي السداد الموثق': tot_paid,
                'إجمالي المتبقي': tot_rem,
                'نسبة السداد': round(rate, 2),
                'عدد المحصلين': collectors,
                'عدد المشرفين': supervisors
            })

        return pd.DataFrame(stats)
