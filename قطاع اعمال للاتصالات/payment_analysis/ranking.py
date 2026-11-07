import pandas as pd

class RankingEngine:
    @staticmethod
    def rank_collectors(
        aggregated_df: pd.DataFrame,
        rank_by: str = 'collection_rate'
    ) -> pd.DataFrame:
        """
        Returns ranked DataFrame.
        """
        if aggregated_df.empty:
            return pd.DataFrame()
            
        df = aggregated_df.copy()
        
        # Map rank_by to column
        if rank_by == 'collection_rate' and 'نسبة_السداد' in df.columns:
            sort_col = 'نسبة_السداد'
        elif rank_by == 'total_paid' and 'إجمالي_السداد' in df.columns:
            sort_col = 'إجمالي_السداد'
        elif rank_by == 'customers_paid' and 'العملاء' in df.columns:
            sort_col = 'العملاء'
        else:
            sort_col = 'إجمالي_السداد' if 'إجمالي_السداد' in df.columns else df.columns[0]
            
        df = df.sort_values(by=sort_col, ascending=False).reset_index(drop=True)
        df.insert(0, 'الترتيب', df.index + 1)
        return df

    @staticmethod
    def rank_supervisors(aggregated_df: pd.DataFrame, rank_by: str = 'collection_rate') -> pd.DataFrame:
        return RankingEngine.rank_collectors(aggregated_df, rank_by)

# Module-level aliases for direct imports
rank_collectors = RankingEngine.rank_collectors
rank_supervisors = RankingEngine.rank_supervisors
