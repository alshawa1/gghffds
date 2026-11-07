import pandas as pd

class DistributionValidator:
    @staticmethod
    def validate_before_distribution(
        pulled_df: pd.DataFrame,
        target_collectors: list[str],
        column_map: dict,
        collector_portfolio_map: dict,
        allow_cross_portfolio: bool = False
    ) -> dict:
        """
        Validates before executing distribution.
        If allow_cross_portfolio is True, portfolio isolation errors become warnings.
        """
        col_cust = column_map.get('customer_id', 'رقم الهوية')
        col_debt_id = column_map.get('debt_id', 'رقم المديونية')
        col_debt_amt = column_map.get('debt_amount', 'مبلغ الميدونية')
        col_remaining = column_map.get('remaining', 'متبقي سداد موثق')
        col_portfolio = column_map.get('portfolio', 'المحافظ')
        
        errors = []
        warnings = []
        can_proceed = True
        
        if pulled_df is None or pulled_df.empty:
            errors.append("البيانات المسحوبة فارغة.")
            can_proceed = False
            
        if not target_collectors:
            errors.append("لم يتم تحديد محصلين مستهدفين.")
            can_proceed = False
            
        if can_proceed and col_cust not in pulled_df.columns:
            errors.append(f"العمود المطلوب غير موجود: {col_cust}")
            can_proceed = False
            
        if can_proceed:
            pulled_portfolios = set(pulled_df[col_portfolio].unique())
            target_portfolios = set([collector_portfolio_map.get(c) for c in target_collectors if collector_portfolio_map.get(c)])
            
            for p in pulled_portfolios:
                if p not in target_portfolios:
                    msg = f"لا يوجد محصل مستهدف ينتمي للمحفظة: {p}."
                    if allow_cross_portfolio:
                        warnings.append(f"⚠️ {msg} (مسموح به: تم تعطيل عزل المحافظ بناءً على اختيارك).")
                    else:
                        errors.append(f"{msg} لن يتم توزيع عملاء هذه المحفظة ما لم يتم استثناء عزل المحافظ.")
                        can_proceed = False
                    
            unmapped_collectors = [c for c in target_collectors if c not in collector_portfolio_map or pd.isna(collector_portfolio_map.get(c))]
            if unmapped_collectors:
                msg = f"المحصلين التاليين ليس لديهم محفظة محددة: {', '.join(unmapped_collectors)}"
                if allow_cross_portfolio:
                    warnings.append(f"⚠️ {msg}")
                else:
                    errors.append(msg)
                    can_proceed = False

        stats = {}
        if can_proceed and not pulled_df.empty:
            unique_debts_df = pulled_df.drop_duplicates(subset=[col_cust, col_debt_id]) if (col_cust in pulled_df.columns and col_debt_id in pulled_df.columns) else pulled_df
            stats = {
                'customers': pulled_df[col_cust].nunique() if col_cust in pulled_df.columns else len(pulled_df),
                'debts': unique_debts_df.shape[0],
                'debt_amount': float(unique_debts_df[col_debt_amt].sum()) if col_debt_amt in unique_debts_df.columns else 0.0,
                'remaining': float(unique_debts_df[col_remaining].sum()) if col_remaining in unique_debts_df.columns else 0.0
            }
            
        return {
            'can_proceed': can_proceed,
            'errors': errors,
            'warnings': warnings,
            'stats': stats
        }
