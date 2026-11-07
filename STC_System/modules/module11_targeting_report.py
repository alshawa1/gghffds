"""
modules/module7_targets.py
──────────────────────────
Module 7 — العملاء المستهدفة (Target Customers) using Polars.

تعديلات جوهرية:
1. التصفية المسبقة الصارمة بناءً على الحالات الرئيسية والفرعية قبل فحص النصوص.
2. إنشاء شيت/جدول مخصص للمستهدفين فقط (Targets Only) يتضمن تفاصيل الحالات والكلمات المستهدفة.
3. استبعاد تام لكافة الكلمات الإيجابية الخاطئة ("رد", "متابعة", "متهرب", "رد وسكت", إلخ).
"""
from __future__ import annotations

import logging
from typing import Dict, Any

import polars as pl

_log = logging.getLogger("Module7_Targets")

POSITIVE = "مستهدف"
NEGATIVE = "غير مستهدف"

# ── 1. Full Payment Disqualification ───────────────────────────────────────────
FULLY_PAID_KEYWORDS = [
    "تم السداد", "سدد كامل", "كامل المديونية", "كامل المديونيه", "كامل المبلغ",
    "سداد كامل", "مسدد بالكامل", "سدد المديونية كامله", "سدد المديونية كاملة",
    "تم سداد كامل", "خلاص سدد", "تم سداد المبلغ كاملا", "مسدد كامل"
]

# ── 2. Strict Positive Keyword Dictionaries (NO SINGLE GENERIC WORDS) ─────────
TARGET_CATEGORIES = {
    "💰 مرتبطة بالراتب": [
        "أول الشهر", "اول الشهر", "على الراتب", "ع الراتب", "علي الراتب",
        "بعد نزول الراتب", "بعد تحويل الراتب", "نهاية الشهر", "بانتظار الراتب",
        "مع راتب", "الراتب", "معاش", "تقاعد", "التقاعد", "بينزل الراتب", "ع الراتب", " الراتب", " علراتب", " منتظر الراتب"
        , " راتب", "رواتب ", 
        "أول الشهر", "اول الشهر", "بداية الشهر", "بدايه الشهر",
        "نهاية الشهر", "آخر الشهر", "اخر الشهر", "اخر الشهر الحالي",
        "على الراتب", "ع الراتب", "علي الراتب", "عالراتب", "علراتب", "عال راتب",
        "بعد الراتب", "مع الراتب", "مع راتب", "عند الراتب",
        "بعد نزول الراتب", "بعد تحويل الراتب", "بعد استلام الراتب",
        "بعد استلام راتبه", "بعد استلام الراتب مباشرة",
        "بينزل الراتب", "ينزل الراتب", "اذا نزل الراتب", "لما ينزل الراتب",
        "وقت الراتب", "موعد الراتب",
        "استلم الراتب", "استلام الراتب",
        "راتب", "راتبي", "راتبه", "الراتب", "رواتب",
        "معاش", "المعاش", "بعد المعاش", "بعد نزول المعاش",
        "تقاعد", "التقاعد", "راتب التقاعد",
        "بانتظار الراتب", "منتظر الراتب", "ينتظر الراتب","يقول على الرواتب ","قال على الراتب","قال علي اخر الشهر","تواصل خلال اليوم"
        ,"مهله","يقول اتواصلي بكره","على اخر الشهر","يقول ان شاء الله ان شاء الله","دقي بعد نص ساع","دقي بعد","وارجع لي"
    ],
    "🏛️ مرتبطة بالدعم الحكومي": [
        "حساب المواطن", "حساب مواطن", "الضمان", "ضمان", "دعم حكومي", " منتظر دعم", "بخصم ", "ع مواطن ", "منتظم ", "منتظممم "
        , " ع مواطن", 
        "حساب المواطن", "حساب مواطن",
        "الضمان", "الضمان الاجتماعي", "ضمان",
        "دعم", "دعم حكومي",
        "منتظر دعم", "ينزل الدعم", "بعد الدعم",
        "حافز", "ساند", "ريف", "تمهير",
        "ع مواطن", "على المواطن", "المواطن",
        "خصم المواطن", "خصم الضمان"
    ],
    "🤝 وعود بالسداد ومنتظمين": [
        "منتظم بالسداد", "منتظم شهريا", "منتظم بالسداد شهريا",
        "تم الاتفاق على السداد", "وعد بالسداد", "سداد قريب", "سيتم السداد",
        "وعد سداد", "واعد بالسداد", "جدولة", "ابشر بالسداد", "أبشر بالسداد", "متعاون بالسداد",
        "اتفقت معه", "سدد منها", "وضح له وسيسدد", "ان شاء الله ", "انشاء الله "
        "وعد", "واعد", "واعدني", "وعدني",
        "وعد بالسداد", "واعد بالسداد",
        "وعد سداد", "واعد سداد",

        "تم الاتفاق", "تم الاتفاق على السداد",
        "تم الوعد",

        "أكد", "اكد", "أكد السداد", "اكد السداد",

        "ملتزم", "ملتزم بالسداد",
        "منتظم", "منتظم بالسداد",
        "منتظم شهريا", "منتظم بالسداد شهريا",

        "سداد قريب",
        "سيتم السداد",
        "سيقوم بالسداد",

        "هيسدد", "حيسدد",
        "بيسدد", "بسدد",
        "سيسدد", "يسدد", "سدد",

        "هدفع", "يدفع", "دفع",

        "ان شاء الله", "إن شاء الله",
        "انشالله", "انشاء الله",
        "باذن الله", "بإذن الله",

        "أكيد", "اكيد",

        "ابشر", "أبشر",
        "ابشر بالسداد", "أبشر بالسداد",

        "تم التواصل وتم الاتفاق",
        "تم التواصل وسيتم السداد",

        "وضح له وسيسدد",
        "اتفقت معه",
        "اتفقنا",

        "سدد منها",
        "راجع ويسدد",
        "كلمني ويسدد",

        "بعد المهلة يسدد",
        "بعد الاجازة يسدد",

        "متعاون",
        "متجاوب"
    ],
    "📅 مرتبطة بتاريخ أو وقت محدد": [
        "يوم الخميس", "يوم الاحد", "يوم الأحد", "يوم الاثنين", "يوم الإثنين",
        "يوم الثلاثاء", "يوم الاربعاء", "يوم الأربعاء", "يوم الجمعة", "يوم السبت",
        "يوم 1", "يوم الاول", "شهر 7", "شهر 8", "شهر 9", "شهر 10", "شهر 11", "شهر 12",
        "شهر 1", "شهر 2", "شهر 3", "شهر 4", "شهر 5", "شهر 6", "بكره يسدد", "بكرة يسدد", "اليوم يسدد", "يوم 27 ", "يوم27 ", "يوم28 "
        , "يوم10 ", "يوم1 ", "اليوم", "اليوم يسدد",
        "غدا", "غداً",
        "بكره", "بكرة", "باجر",

        "بعد ساعة", "بعد ساعتين",

        "العصر", "بعد العصر",
        "المغرب", "بعد المغرب",
        "العشاء", "بعد العشاء",

        "هذا الاسبوع", "هالاسبوع",
        "بداية الاسبوع", "منتصف الاسبوع", "نهاية الاسبوع",
        "الاسبوع القادم", "الاسبوع الجاي",

        "الشهر القادم", "الشهر الجاي",

        "يوم الخميس",
        "يوم الاحد", "يوم الأحد",
        "يوم الاثنين", "يوم الإثنين",
        "يوم الثلاثاء",
        "يوم الاربعاء", "يوم الأربعاء",
        "يوم الجمعة",
        "يوم السبت",

        "يوم الاول",
        "يوم 1", "يوم1",
        "يوم 10", "يوم10",
        "يوم 15", "يوم15",
        "يوم 20", "يوم20",
        "يوم 25", "يوم25",
        "يوم 27", "يوم27",
        "يوم 28", "يوم28",
        "يوم 30", "يوم30",

        "شهر 1", "شهر 2", "شهر 3",
        "شهر 4", "شهر 5", "شهر 6",
        "شهر 7", "شهر 8", "شهر 9",
        "شهر 10", "شهر 11", "شهر 12",

        "بتاريخ",
        "موعد السداد"
    ],
    "💼 مرتبطة بدخل أو بيع أو مستحقات": [
        "بانتظار المستحقات", "المستحقات", "مستحقات", "بعد البيع", "بيع العقار", "بيع السيارة", "بيتصرف ", "ابشر ", "منتظم "
        ,         "بانتظار المستحقات",
        "المستحقات",
        "مستحقات",

        "المكافأة", "المكافاه",
        "الحافز",

        "العمولة", "العموله",

        "البدل", "بدل",

        "بعد البيع",
        "بيع العقار",
        "بيع السيارة",

        "بعد التحصيل",

        "دخل",
        "دخله",

        "فلوس",
        "معايا فلوس",
        "معاه فلوس",
        "توفرت السيولة",
        "سيولة",

        "قبض",
        "يقبض",
        "هيقبض",

        "بيتصرف",
        "تصريف"

    ],
    "💳 مرتبطة بتحويل أو إيداع أو دفعات": [
        "بعد التحويل", "بعد الإيداع", "بعد الايداع", "سدد دفعه", "سدد دفعة", "سدد دفعه الشهر", "سدد دفعة الشهر",
        "على دفعات", "علي دفعات", "تحويل المبلغ", "إيداع المبلغ", "ايداع المبلغ",
        "بسدد", "بيسدد", "سيسدد", "سدد جزئي","تحويل",
        "تحويل بنكي",
        "بعد التحويل",

        "إيداع",
        "ايداع",
        "بعد الإيداع",
        "بعد الايداع",

        "حوالة",
        "حواله",

        "تحويل المبلغ",
        "إيداع المبلغ",
        "ايداع المبلغ",
        "حول المبلغ",

        "دفعة",
        "دفعه",

        "سدد دفعة",
        "سدد دفعه",
        "سدد دفعة الشهر",
        "سدد دفعه الشهر",

        "دفعة أولى",
        "دفعة اولى",
        "دفعة ثانية",

        "على دفعات",
        "علي دفعات",

        "قسط",
        "القسط",
        "الاقساط",

        "سداد جزئي",
        "جزئي",

        "بسدد",
        "بيسدد",
        "سيسدد",
        "هيسدد",
        "حيسدد"
    ]
}

# ── 3. Disqualifying Negative Keywords inside Follow-ups (المتابعة) ─────────────
DISQUALIFY_KEYWORDS = [
    # نفي ومماطلة وهروب
    "متهرب", "تهرب", "ما بسدد", "افاد انو ما بسدد", "افاد انه ما بسدد", "ما يسدد", "افاد انو ما يسدد",
    "ما عندي وماني مسدد", "ما عندي وماني", "ماني مسدد", "ومصر يسدد", "ومصر ما يسدد",
    "مماطل", "ماطل", "رافض", "رفض", "رفض السداد", "رافض السداد", "انكر", "أنكر", "ينكر",
    "تنازل", "سحب", "مريض", "مسافر", "مسافر بمصر", "لا تتم",
    
    # عدم الرد والإغلاق
    "لايرد", "لا يرد", "لا يررد", "لابرد", "مايرد", "مايردش", "ما يرد", "لم يرد", "لا ترد", "لا رد", "ما ترد",
    "لم يتم الرد", "لمم يتم الرد", "لم يتم رد", "ولا ترد", "م بيشبك", "م يشبك", "م ىيشبك", "ما يشبك", "مبيشبك", "لا يجيب",
    "بريد", "بريد صوتي", "بيزي", "مشغول", "ما يمسك", "مغلق", "قفل", "قفل الخط", "يسكر الخط", "سكر الخط", "قفلت",
    "ردت وقفلت", "يكنسل", "كنسل", "خارج التغطية", "اخوه مو موجود", "أخوه مو موجود", "قال اخوه",
    "اجتماع", "في اجتماع", "الوقت غير مناسب", "غير مناسب", "يفصل", "فصل", "بيفصل", "عدم تجاوب", "لعدم التجاوب",
    
    # رد وسكت وتحديثات المتابعة العامة
    "رد وسكت", "رد و ساكت", "رد ويسكت", "رد بدون تجاوب", "يرد وما يتكلم", "يرد وساكته", "ردت وساكته", "ساكت", "ساكته",
    "تحديث متابعه", "تحديث متابعة", "على نفس الحالة", "علي نفس الحالة", "على نفس الحاله"
]


class TargetCustomersModule:
    CLASS_COL    = "العملاء المستهدفة"
    CATEGORY_COL = "تصنيف الاستهداف"
    PRIORITY_COL = "أولوية التحصيل"
    REASON_COL   = "سبب التصنيف"

    def run(
        self,
        portfolio: pl.DataFrame,
        promise: pl.DataFrame | None = None,
        maharah: pl.DataFrame | None = None,
        payments: pl.DataFrame | None = None,
        report_mode: str = "daily",
        target_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        month: str | int | None = None,
        year: str | int | None = None,
        supervisor_targets: dict | None = None,
        **kwargs,
    ) -> Dict[str, Any]:
        _log.info("▶ بدء تحديد العملاء المستهدفة")

        # ── الخطوة 1: الفلترة الصارمة المسبقة بالحالة الرئيسية والفرعية ───────────
        filtered_portfolio = self._filter_by_status_first(portfolio)

        if filtered_portfolio.is_empty():
            _log.warning("لا توجد سجلات تطابق شروط الحالة الرئيسية والفرعية!")
            empty_df = portfolio.head(0)
            return {
                "data": empty_df,
                "target_only_sheet": empty_df, # شيت المستهدفين فارغ
                "pivot_supervisor": pl.DataFrame(),
                "pivot_collector": pl.DataFrame(),
                "stats": {"إجمالي العملاء المقبولين بالحالة": 0, "مستهدف": 0, "غير مستهدف": 0, "نسبة المستهدفين %": 0.0}
            }

        # حساب وزن العملاء (عدد العملاء)
        id_col = next((c for c in ["رقم الهوية", "الهوية"] if c in filtered_portfolio.columns), None)
        if id_col:
            filtered_portfolio = filtered_portfolio.with_columns(
                (pl.lit(1.0) / pl.col(id_col).count().over(id_col).cast(pl.Float64)).alias("عدد العملاء")
            )
        else:
            filtered_portfolio = filtered_portfolio.with_columns(pl.lit(1.0).alias("عدد العملاء"))

        # ── الخطوة 2: فحص الكلمات المستهدفة بعد التأكد من صحة الحالة ─────────────
        classified_df = self._classify_notes(filtered_portfolio)

        # ── الخطوة 3: إنتاج شيت المستهدفين فقط ──────────────────────────────────
        targets_only_df = classified_df.filter(pl.col(self.CLASS_COL) == POSITIVE)

        # الجداول المحورية
        piv_sup = self._build_pivot(classified_df, "المشرف")
        collector = next((c for c in ["المحصل", "الموظف"] if c in classified_df.columns), "")
        piv_col   = self._build_pivot(classified_df, collector) if collector else pl.DataFrame()

        total = len(classified_df)
        pos_count = targets_only_df.height
        neg_count = total - pos_count

        category_counts: Dict[str, int] = {}
        if pos_count > 0:
            cat_df = targets_only_df.group_by(self.CATEGORY_COL).len()
            for r in cat_df.iter_rows(named=True):
                category_counts[str(r[self.CATEGORY_COL])] = int(r["len"])

        stats: Dict[str, Any] = {
            "إجمالي العملاء بعد فلترة الحالة": total,
            "مستهدف":                          pos_count,
            "غير مستهدف":                      neg_count,
            "نسبة المستهدفين %":              round(pos_count / total * 100, 1) if total else 0.0,
        }
        stats.update(category_counts)

        return {
            "data":              classified_df,       # السجلات المفحوصة
            "target_only_sheet": targets_only_df,     # 🎯 الشيت الخالص للمستهدفين بالحالة والكلمات
            "positive_data":     targets_only_df,
            "pivot_supervisor":  piv_sup,
            "pivot_collector":   piv_col,
            "stats":             stats,
        }

    @staticmethod
    def _normalize_text_str(s: str) -> str:
        return (
            s.replace("أ", "ا")
            .replace("إ", "ا")
            .replace("آ", "ا")
            .replace("ة", "ه")
            .replace("ى", "ي")
            .strip()
            .lower()
        )

    def _normalize_text(self, text_col: str) -> pl.Expr:
        return (
            pl.col(text_col)
            .fill_null("")
            .cast(pl.String)
            .str.strip_chars()
            .str.to_lowercase()
            .str.replace_all("أ", "ا")
            .str.replace_all("إ", "ا")
            .str.replace_all("آ", "ا")
            .str.replace_all("ة", "ه")
            .str.replace_all("ى", "ي")
        )

    def _filter_by_status_first(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        [التصفية الأولية المقيدة للحالات]:
        يتم استبعاد أي عميل قبل الوصول لفحص الكلمات إن لم يطابق:
        - الحالة الرئيسية: ("سداد جزئي"، "واعد بالسداد"، "متابعه")
        - OR (الحالة الرئيسية = "متوفي" AND الحالة الفرعية تحتوي على "واعد")
        """
        main_col = next((c for c in ["الحالة الرئيسية", "الحالة"] if c in df.columns), None)
        sub_col  = next((c for c in ["الحالة الفرعية"] if c in df.columns), None)

        if not main_col:
            _log.warning("لم يتم العثور على عمود الحالة الرئيسية!")
            return df

        main_expr = self._normalize_text(main_col)
        sub_expr  = self._normalize_text(sub_col) if sub_col else pl.lit("")

        ALLOWED_EXACT_MAIN = ["سداد جزئي", "واعد بالسداد", "متابعه"]

        # 1. مطابقة الحالة الرئيسية الصريحة
        exact_main_match = main_expr.is_in(ALLOWED_EXACT_MAIN)

        # 2. حالة المتوفي المشترطة بشرط وجود "واعد" في الحالة الفرعية
        deceased_match = (main_expr == "متوفي") & (sub_expr.str.contains("واعد"))

        filtered_df = df.filter(exact_main_match | deceased_match)
        _log.info(f"إجمالي المحفظة: {len(df)} | المقبول بحسب الحالة الرئيسية/الفرعية: {len(filtered_df)}")
        return filtered_df

    def _classify_notes(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        [فحص الكلمات المستهدفة]: يُنفذ فقط على العينات المقبولة من مرحلة الحالة.
        """
        note_col = next((c for c in ["المتابعة", "الملاحظة", "الملاحظات", "ملاحظة"] if c in df.columns), None)

        if not note_col:
            return df.with_columns([
                pl.lit(NEGATIVE).alias(self.CLASS_COL),
                pl.lit("❌ غير مستهدف").alias(self.CATEGORY_COL),
                pl.lit("لا يوجد عمود متابعة").alias(self.REASON_COL),
                pl.lit(2).cast(pl.Int32).alias(self.PRIORITY_COL),
            ])

        note_expr = self._normalize_text(note_col)

        # 1. فحص سداد كامل المديونية
        has_fully_paid = pl.lit(False)
        for kw in FULLY_PAID_KEYWORDS:
            kw_norm = self._normalize_text_str(kw)
            has_fully_paid = has_fully_paid | note_expr.str.contains(kw_norm, literal=True)

        # 2. فحص كلمات الاستبعاد والتهرب والرد الساكت
        has_disqualify = pl.lit(False)
        disqualify_reasons = []
        for kw in DISQUALIFY_KEYWORDS:
            kw_norm = self._normalize_text_str(kw)
            match_cond = note_expr.str.contains(kw_norm, literal=True)
            has_disqualify = has_disqualify | match_cond
            disqualify_reasons.append(
                pl.when(match_cond).then(pl.lit(f"مستبعد: {kw}")).otherwise(pl.lit(None))
            )

        disqualify_reason_expr = pl.coalesce(disqualify_reasons).fill_null("استبعاد / عدم تجاوب")

        # 3. فحص الكلمات الإيجابية الصريحة والتصنيف
        category_expr_list = []
        has_any_positive = pl.lit(False)

        for cat_name, kw_list in TARGET_CATEGORIES.items():
            cat_match = pl.lit(False)
            for kw in kw_list:
                kw_norm = self._normalize_text_str(kw)
                cat_match = cat_match | note_expr.str.contains(kw_norm, literal=True)
            
            has_any_positive = has_any_positive | cat_match
            category_expr_list.append(
                pl.when(cat_match).then(pl.lit(cat_name)).otherwise(pl.lit(None))
            )

        pos_category_expr = pl.coalesce(category_expr_list)

        # القرار النهائي
        is_targeted = (~has_fully_paid) & (~has_disqualify) & has_any_positive

        class_expr = pl.when(is_targeted).then(pl.lit(POSITIVE)).otherwise(pl.lit(NEGATIVE))
        
        category_result_expr = (
            pl.when(is_targeted)
            .then(pos_category_expr)
            .otherwise(pl.lit("❌ غير مستهدف"))
        )

        reason_result_expr = (
            pl.when(has_fully_paid)
            .then(pl.lit("✅ تم سداد كامل المديونية"))
            .otherwise(
                pl.when(is_targeted)
                .then(pl.lit("مطابق للحالات والكلمات الإيجابية"))
                .otherwise(
                    pl.when(has_disqualify)
                    .then(disqualify_reason_expr)
                    .otherwise(pl.lit("لا تتوفر عبارات سداد إيجابية"))
                )
            )
        )

        return df.with_columns([
            class_expr.alias(self.CLASS_COL),
            category_result_expr.alias(self.CATEGORY_COL),
            reason_result_expr.alias(self.REASON_COL),
            pl.when(is_targeted).then(pl.lit(1)).otherwise(pl.lit(2)).cast(pl.Int32).alias(self.PRIORITY_COL)
        ])

    def _build_pivot(self, df: pl.DataFrame, group_col: str) -> pl.DataFrame:
        if not group_col or group_col not in df.columns:
            return pl.DataFrame()

        try:
            pivot = (
                df.group_by([group_col, self.CLASS_COL])
                .len()
                .pivot(on=self.CLASS_COL, index=group_col, values="len")
                .fill_null(0)
            )
            for col in [POSITIVE, NEGATIVE]:
                if col not in pivot.columns:
                    pivot = pivot.with_columns(pl.lit(0).alias(col))
            
            return pivot.with_columns(
                (pl.col(POSITIVE) + pl.col(NEGATIVE)).alias("الإجمالي")
            )
        except Exception as e:
            _log.warning("فشل إنشاء جدول المحور لـ %s: %s", group_col, e)
            return pl.DataFrame()

    @staticmethod
    def get_supervisors_and_collectors(df: pl.DataFrame) -> dict:
        """
        يُرجع dict: {اسم المشرف: [قائمة المحصلين]}
        يُستخدم في واجهة Streamlit لعرض خيارات التصفية في تقرير الاستهداف.
        """
        try:
            # الأعمدة المحتملة للمشرف والمحصل
            sup_col = next(
                (c for c in ["المشرف", "supervisor", "Supervisor"] if c in df.columns),
                None
            )
            col_col = next(
                (c for c in ["المحصل", "الموظف", "collector", "Collector"] if c in df.columns),
                None
            )

            if not sup_col or not col_col:
                # لو مفيش عمود مشرف، نرجع dict بمشرف واحد "كل المحصلين"
                if col_col:
                    collectors = (
                        df.select(col_col).unique().to_series()
                        .cast(pl.String).str.strip_chars()
                        .drop_nulls().sort().to_list()
                    )
                    return {"الكل": [c for c in collectors if c.strip()]}
                return {}

            result = {}
            supervisors = (
                df.select(sup_col).unique().to_series()
                .cast(pl.String).str.strip_chars()
                .drop_nulls().sort().to_list()
            )
            for sup in supervisors:
                if not sup.strip():
                    continue
                collectors = (
                    df.filter(
                        pl.col(sup_col).cast(pl.String).str.strip_chars() == sup
                    )
                    .select(col_col).unique().to_series()
                    .cast(pl.String).str.strip_chars()
                    .drop_nulls().sort().to_list()
                )
                result[sup] = [c for c in collectors if c.strip()]
            return result
        except Exception as e:
            _log.warning("get_supervisors_and_collectors error: %s", e)
            return {}


# ── Backward-compatible alias ─────────────────────────────────────────────────
# streamlit_app.py imports TargetingReportModule from this file.
TargetingReportModule = TargetCustomersModule