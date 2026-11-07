"""
AI Operations Copilot - النواة الذكية للمساعد العمليات.
يعالج الأسئلة باللغة الطبيعية، ينفذ المهام، ويولد التوصيات.
"""
import polars as pl
import logging
import re
from datetime import datetime, date, timedelta

from .knowledge_base import CopilotKnowledgeBase
from .schema_intelligence import SchemaIntelligenceEngine
from .supervisor_filter import SupervisorFilterEngine

_log = logging.getLogger(__name__)

ARABIC_MONTHS = {
    1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
    7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
}

# ── Keyword Intent Detector ──────────────────────────────────────────────────
INTENT_PATTERNS = {
    "coverage_rate": ["نسبة التغطية", "تغطية اليوم", "coverage", "كم التغطية", "نسبة الاتصال"],
    "total_customers": ["كم عدد العملاء", "إجمالي العملاء", "total customers", "عدد العملاء"],
    "paid_amount": ["متبقي السداد", "إجمالي السداد", "مبلغ السداد", "كم السداد", "الرصيد"],
    "best_supervisor": ["أفضل مشرف", "best supervisor", "من أفضل", "أعلى مشرف"],
    "worst_collector": ["أقل محصل", "worst collector", "أضعف محصل", "least performing"],
    "neglect_count": ["كم مهمل", "عدد المهملين", "الإهمال", "المهملون"],
    "target_customers": ["المستهدفون", "عملاء مستهدفين", "كم مستهدف"],
    "portfolio_risk": ["محافظ خطرة", "تحتاج تدخل", "محافظ ضعيفة", "risk portfolios"],
    "compare_week": ["قارن أسبوع", "compare week", "الأسبوع الماضي", "مقارنة"],
    "error_analysis": ["أخطاء النظام", "system errors", "بيانات خاطئة"],
    "recommend": ["توصية", "اقتراح", "recommend", "ماذا أفعل", "ما التوصية"],
}


def _clean_float(series: pl.Series) -> pl.Series:
    if series.dtype in (pl.Float32, pl.Float64, pl.Int32, pl.Int64):
        return series.cast(pl.Float64).fill_null(0.0)
    return (series.cast(pl.String)
            .str.replace_all(r"[,\s]", "")
            .cast(pl.Float64, strict=False)
            .fill_null(0.0))


def _detect_col(df: pl.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


class AIOperationsCopilot:
    """
    المساعد الذكي لقسم العمليات.
    يفهم الأسئلة باللغة الطبيعية، ينفذ التحليلات، ويولد التوصيات.
    """

    def __init__(
        self,
        portfolio_df: pl.DataFrame | None = None,
        payments_df: pl.DataFrame | None = None,
        kb: CopilotKnowledgeBase | None = None,
    ):
        self.kb = kb or CopilotKnowledgeBase()
        self.schema_engine = SchemaIntelligenceEngine(self.kb)
        self.sup_engine = SupervisorFilterEngine(self.kb)
        self.portfolio = portfolio_df
        self.payments = payments_df
        self._kpi_cache: dict | None = None

    def load_portfolio(self, df: pl.DataFrame):
        self.portfolio = df
        self._kpi_cache = None
        sups = self.sup_engine.get_portfolio_supervisors(df)
        return sups

    def load_payments(self, df: pl.DataFrame):
        self.payments = df

    # ── KPI Calculation ───────────────────────────────────────────────────────
    def _build_kpis(self, df: pl.DataFrame | None = None) -> dict:
        if df is None:
            df = self.portfolio
        if df is None or df.is_empty():
            return {}

        total = len(df)
        sup_col = self.sup_engine.detect_supervisor_column(df)
        collector_col = _detect_col(df, ["اسم المحصل", "المحصل", "الموظف"])
        bal_col = _detect_col(df, ["متبقي سداد موثق", "متبقي السداد", "متبقي سداد العقد"])
        paid_col = _detect_col(df, ["السدادات الموثقة", "مبلغ السداد"])
        status_col = _detect_col(df, ["الحالة الرئيسية", "الحالة"])
        note_col = _detect_col(df, ["المتابعة", "آخر متابعة على العميل", "الملاحظات"])
        portfolio_col = _detect_col(df, ["اسم الحاوية", "المحافظ"])

        # Coverage
        today_str = date.today().strftime("%Y-%m-%d")
        followup_col = _detect_col(df, ["تاريخ المتابعة", "آخر متابعة بعدد الايام من اخر حركة على ملف العميل"])
        covered = 0
        if followup_col:
            f_series = df[followup_col].cast(pl.String).str.slice(0, 10)
            covered = int(f_series.eq(today_str).sum())

        bal_series = _clean_float(df[bal_col]) if bal_col else pl.Series([0.0] * total)
        paid_series = _clean_float(df[paid_col]) if paid_col else pl.Series([0.0] * total)

        total_bal = float(bal_series.sum())
        total_paid = float(paid_series.sum())
        avg_paid = float(paid_series.filter(paid_series > 0).mean() or 0)
        coverage_pct = round(covered / total * 100, 2) if total > 0 else 0.0

        # Supervisors breakdown
        sup_summary = {}
        if sup_col:
            agg_exprs = [pl.len().alias("عدد العملاء")]
            if bal_col:
                agg_exprs.append(pl.col(bal_col).cast(pl.Float64, strict=False).fill_null(0.0).sum().alias("متبقي"))
            else:
                agg_exprs.append(pl.lit(0.0).alias("متبقي"))
            sup_groups = df.group_by(sup_col).agg(agg_exprs)
            sup_summary = {r[sup_col]: {"عدد": r["عدد العملاء"], "متبقي": r["متبقي"]} for r in sup_groups.to_dicts()}

        return {
            "total_customers": total,
            "covered_today": covered,
            "coverage_pct": coverage_pct,
            "total_balance": total_bal,
            "total_paid": total_paid,
            "avg_paid": avg_paid,
            "supervisor_col": sup_col,
            "collector_col": collector_col,
            "portfolio_col": portfolio_col,
            "status_col": status_col,
            "note_col": note_col,
            "sup_summary": sup_summary,
            "date_analyzed": datetime.now().isoformat()
        }

    # ── Intent Detection ──────────────────────────────────────────────────────
    def _detect_intent(self, question: str) -> str | None:
        q = question.strip()
        for intent, patterns in INTENT_PATTERNS.items():
            for p in patterns:
                if p in q:
                    return intent
        return "general"

    # ── Tool Handlers ─────────────────────────────────────────────────────────
    def _handle_coverage(self, kpis: dict) -> str:
        pct = kpis.get("coverage_pct", 0)
        covered = kpis.get("covered_today", 0)
        total = kpis.get("total_customers", 0)
        status = "✅ جيدة" if pct >= 60 else ("⚠️ متوسطة" if pct >= 30 else "🔴 منخفضة - تحتاج تدخل فوري")
        return (
            f"📊 **نسبة التغطية الحالية:** {pct}%\n"
            f"- **مغطى اليوم:** {covered:,} عميل\n"
            f"- **إجمالي العملاء:** {total:,} عميل\n"
            f"- **التقييم:** {status}"
        )

    def _handle_total_customers(self, kpis: dict) -> str:
        total = kpis.get("total_customers", 0)
        sup_summary = kpis.get("sup_summary", {})
        lines = [f"👥 **إجمالي عملاء المحفظة:** {total:,} عميل"]
        if sup_summary:
            lines.append("\n**توزيع المشرفين:**")
            for sup, info in sorted(sup_summary.items(), key=lambda x: -x[1]["عدد"])[:5]:
                lines.append(f"  - {sup}: {info['عدد']:,} عميل")
        return "\n".join(lines)

    def _handle_paid_amount(self, kpis: dict) -> str:
        bal = kpis.get("total_balance", 0)
        paid = kpis.get("total_paid", 0)
        avg = kpis.get("avg_paid", 0)
        collection_rate = round(paid / bal * 100, 2) if bal > 0 else 0
        return (
            f"💰 **إجمالي متبقي السداد الموثق:** {bal:,.2f} ريال\n"
            f"- **إجمالي السدادات الموثقة:** {paid:,.2f} ريال\n"
            f"- **متوسط السداد:** {avg:,.2f} ريال\n"
            f"- **نسبة التحصيل:** {collection_rate}%"
        )

    def _handle_best_supervisor(self, kpis: dict) -> str:
        sup_summary = kpis.get("sup_summary", {})
        if not sup_summary:
            return "⚠️ لا توجد بيانات كافية للمشرفين في هذه المحفظة."
        sorted_sups = sorted(sup_summary.items(), key=lambda x: -x[1]["عدد"])
        top = sorted_sups[:3]
        lines = ["🏆 **أفضل المشرفين حسب عدد العملاء:**"]
        medals = ["🥇", "🥈", "🥉"]
        for i, (name, info) in enumerate(top):
            lines.append(f"{medals[i]} {name}: {info['عدد']:,} عميل | متبقي {info['متبقي']:,.0f} ريال")
        return "\n".join(lines)

    def _handle_recommendations(self, kpis: dict) -> str:
        recs = []
        coverage_pct = kpis.get("coverage_pct", 0)
        total = kpis.get("total_customers", 0)
        sup_summary = kpis.get("sup_summary", {})

        if coverage_pct < 30:
            recs.append("🔴 **تحذير عاجل:** نسبة التغطية منخفضة جداً (أقل من 30%). يُنصح بمراجعة قوائم المتابعة الفورية.")
        if coverage_pct < 60:
            recs.append("⚠️ نسبة التغطية دون المعدل الطبيعي (60%). يُنصح بتوزيع مهام المتابعة بالتساوي.")

        # Imbalanced supervisors
        if sup_summary and len(sup_summary) > 1:
            counts = [v["عدد"] for v in sup_summary.values()]
            max_c, min_c = max(counts), min(counts)
            if max_c > min_c * 2:
                high_sup = max(sup_summary, key=lambda x: sup_summary[x]["عدد"])
                recs.append(f"⚖️ **توزيع غير متوازن:** المشرف '{high_sup}' لديه ضعف عدد العملاء مقارنة بالآخرين. يُوصى بتطبيق موديول التوازن.")

        if not recs:
            recs.append("✅ النظام يعمل بشكل جيد ولا توجد توصيات طارئة حالياً.")

        return "💡 **توصيات AI Operations Copilot:**\n" + "\n".join(recs)

    # ── Main Entry: Ask ───────────────────────────────────────────────────────
    def ask(self, question: str, selected_supervisors: list[str] | None = None) -> str:
        """
        يعالج سؤالاً باللغة الطبيعية ويرجع إجابة تحليلية.
        """
        if self.portfolio is None or self.portfolio.is_empty():
            return "⚠️ الرجاء رفع ملف المحفظة أولاً حتى يتسنى للـ AI تحليل بياناتك."

        # Apply supervisor filter if requested
        df_work = self.portfolio
        if selected_supervisors:
            df_work = self.sup_engine.filter_portfolio(df_work, selected_supervisors)

        kpis = self._build_kpis(df_work)
        intent = self._detect_intent(question)

        if intent == "coverage_rate":
            return self._handle_coverage(kpis)
        elif intent == "total_customers":
            return self._handle_total_customers(kpis)
        elif intent == "paid_amount":
            return self._handle_paid_amount(kpis)
        elif intent == "best_supervisor":
            return self._handle_best_supervisor(kpis)
        elif intent == "recommend":
            return self._handle_recommendations(kpis)
        elif intent == "neglect_count":
            note_col = kpis.get("note_col")
            excl = self.kb.get_rule("neglect_exclusion_keywords", "").split(",")
            if note_col and note_col in df_work.columns:
                excl_mask = pl.lit(False)
                for kw in excl:
                    excl_mask = excl_mask | df_work[note_col].cast(pl.String).str.contains(kw.strip())
                neglect_count = int(excl_mask.not_().sum())
            else:
                neglect_count = 0
            return (f"🔴 **عدد العملاء المهملين:** {neglect_count:,} عميل\n"
                    f"- (مع استبعاد الحالات: {', '.join(excl)})")
        elif intent == "target_customers":
            note_col = kpis.get("note_col")
            kws = self.kb.get_rule("target_customer_keywords", "").split(",")
            if note_col and note_col in df_work.columns:
                mask = pl.lit(False)
                for kw in kws:
                    mask = mask | df_work[note_col].cast(pl.String).str.contains(kw.strip())
                target_count = int(mask.sum())
            else:
                target_count = 0
            return f"🎯 **إجمالي العملاء المستهدفين:** {target_count:,} عميل"
        else:
            # General fallback with comprehensive summary
            recs_text = self._handle_recommendations(kpis)
            cov_text = self._handle_coverage(kpis)
            return (
                f"🤖 **AI Operations Copilot - تحليل شامل للمحفظة**\n\n"
                f"{cov_text}\n\n"
                f"**📊 إجمالي العملاء:** {kpis.get('total_customers', 0):,}\n"
                f"**💰 متبقي السداد الموثق:** {kpis.get('total_balance', 0):,.2f} ريال\n\n"
                f"{recs_text}"
            )
