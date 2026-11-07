import polars as pl
import logging
from .knowledge_base import CopilotKnowledgeBase

_log = logging.getLogger(__name__)

SUPERVISOR_COLS = ["المشرف", "المشرف موثق السداد", "اسم المشرف", "Supervisor"]

class SupervisorFilterEngine:
    """
    مُحرك التصفية الديناميكي للمشرفين.
    يتيح اختيار المشرفين النشطين وتطبيق الفلترة قبل تشغيل أية موديولات أو تقارير.
    """
    def __init__(self, kb: CopilotKnowledgeBase | None = None):
        self.kb = kb or CopilotKnowledgeBase()

    def detect_supervisor_column(self, df: pl.DataFrame) -> str | None:
        for col in df.columns:
            if str(col).strip() in SUPERVISOR_COLS:
                return str(col).strip()
        return None

    def get_portfolio_supervisors(self, df: pl.DataFrame) -> list[str]:
        col = self.detect_supervisor_column(df)
        if not col or col not in df.columns:
            return []
        
        sups = (
            df[col]
            .cast(pl.String)
            .drop_nulls()
            .unique()
            .to_list()
        )
        sups_clean = sorted([s.strip() for s in sups if s and s.strip() and s.strip().lower() != "null"])
        
        # Register in SQLite Memory
        if sups_clean:
            self.kb.register_supervisors(sups_clean)
            
        return sups_clean

    def filter_portfolio(self, df: pl.DataFrame, selected_supervisors: list[str] | None) -> pl.DataFrame:
        if not selected_supervisors:
            return df
        
        col = self.detect_supervisor_column(df)
        if not col or col not in df.columns:
            return df

        selected_set = set(selected_supervisors)
        filtered = df.filter(
            pl.col(col).cast(pl.String).str.strip_chars().is_in(selected_set)
        )
        _log.info("🎯 Supervisor Filter Applied: %d -> %d rows (%d supervisors selected)", len(df), len(filtered), len(selected_supervisors))
        return filtered
