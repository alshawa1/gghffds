import polars as pl
import difflib
import logging
from .knowledge_base import CopilotKnowledgeBase, PRETRAINED_MAPPINGS

_log = logging.getLogger(__name__)

TARGET_FIELDS = {
    "remaining_balance": "متبقي السداد الموثق",
    "debt_amount": "مبلغ المديونية",
    "paid_amount": "مبلغ السداد",
    "national_id": "رقم الهوية",
    "main_id": "الرقم الرئيسي",
    "customer_name": "اسم العميل",
    "collector": "اسم المحصل",
    "supervisor": "المشرف",
    "main_status": "الحالة الرئيسية",
    "followup_note": "المتابعة",
    "portfolio_name": "اسم المحفظة"
}


class SchemaIntelligenceEngine:
    """
    مُحرك الذكاء الدلالي للاستكشاف التلقائي لهيكل المحافظ والملفات الجديدة.
    يتعرف على أسماء الأعمدة الدلالية ويطابقها وحفظ التفضيلات في الذاكرة.
    """
    def __init__(self, kb: CopilotKnowledgeBase | None = None):
        self.kb = kb or CopilotKnowledgeBase()

    def analyze_schema(self, df: pl.DataFrame) -> dict:
        """
        يرجع تحليلاً شاملاً لأعمدة DataFrame:
        - mapped: {col_raw: (target_key, target_label, confidence)}
        - needs_confirmation: [{col_raw, suggested_target_key, suggested_target_label, confidence}]
        - unmapped: [col_raw]
        """
        approved_map = self.kb.get_all_approved_mappings()
        mapped = {}
        needs_confirmation = []
        unmapped = []

        cols = df.columns

        for col in cols:
            col_clean = str(col).strip()

            # 1. Exact match in approved SQLite memory
            if col_clean in approved_map:
                target_key = approved_map[col_clean]
                target_label = TARGET_FIELDS.get(target_key, target_key)
                mapped[col_clean] = (target_key, target_label, 1.0)
                continue

            # 2. Fuzzy matching against known target synonyms
            best_match_key = None
            best_score = 0.0

            for target_key, synonyms in PRETRAINED_MAPPINGS.items():
                for syn in synonyms:
                    ratio = difflib.SequenceMatcher(None, col_clean.lower(), syn.lower()).ratio()
                    if ratio > best_score:
                        best_score = ratio
                        best_match_key = target_key

            if best_score >= 0.82 and best_match_key:
                # High confidence -> Auto map and remember
                target_label = TARGET_FIELDS.get(best_match_key, best_match_key)
                mapped[col_clean] = (best_match_key, target_label, round(best_score, 2))
                self.kb.save_column_mapping(col_clean, best_match_key, confidence=round(best_score, 2), status="approved")

            elif best_score >= 0.50 and best_match_key:
                # Medium confidence -> Suggest for user confirmation
                target_label = TARGET_FIELDS.get(best_match_key, best_match_key)
                needs_confirmation.append({
                    "column_raw": col_clean,
                    "suggested_key": best_match_key,
                    "suggested_label": target_label,
                    "confidence": round(best_score, 2)
                })
            else:
                unmapped.append(col_clean)

        return {
            "mapped": mapped,
            "needs_confirmation": needs_confirmation,
            "unmapped": unmapped
        }

    def confirm_mapping(self, column_raw: str, target_key: str):
        """يحفظ مطابقة المستخدم المقبولة في الذاكرة الدائمة للأبد."""
        self.kb.save_column_mapping(column_raw, target_key, confidence=1.0, status="approved")
        _log.info("🧠 Saved schema intelligence mapping: '%s' -> '%s'", column_raw, target_key)

    def standardize_dataframe(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        يعيد توحيد وتنسيق أسماء الأعمدة في DataFrame لتصبح معيارية بحسب الماتش الموجود بـ SQLite.
        """
        analysis = self.analyze_schema(df)
        mapped = analysis["mapped"]

        rename_dict = {}
        for col_raw, (target_key, target_label, _) in mapped.items():
            if col_raw != target_label and col_raw in df.columns:
                rename_dict[col_raw] = target_label

        if rename_dict:
            return df.rename(rename_dict)
        return df
