"""
modules/module2_contact.py
──────────────────────────
Module 2 — التوصل وعدم التوصل (Contact Status) using Polars.
Fully vectorized — zero map_elements / Python loops.
"""
from __future__ import annotations

import logging
from typing import Dict

import polars as pl

from core.utils import CONTACTED_STATUSES, NOT_CONTACTED_STATUSES

_log = logging.getLogger("Module2_Contact")

CONTACTED     = "تم التوصل"
NOT_CONTACTED = "عدم التوصل"
NOT_CONTACT_CLOSED = "لا يرد ومغلق"  # تصنيف فرعي: الرئيسية لا يرد + الفرعية مقطوع/مغلق/لا يرد

# قوائم ثابتة للمقارنة
_CONTACTED_LIST     = list(CONTACTED_STATUSES)
_NOT_CONTACTED_LIST = list(NOT_CONTACTED_STATUSES)

# كلمات مفتاحية للتوصل في نص الحالة
_CONTACT_KEYWORDS = ["وعد", "سداد", "رد", "قسط", "تسوية", "جدولة", "مسدد"]

# قيم فارغة/لا معنى لها
_BLANK_VALUES = ["", "nan", "none", "null", "-", "..", "...", "لا يوجد",
                 "بدون", "لايوجد", "تم التواصل", "تواصل", "ok", "okay", "n/a", "na"]

# ── الحالات التي تدل على التوصل الفعلي (العميل رد) — تشمل الرئيسية والفرعية ─────
# حتى لو الحالة الرئيسية تبدو غريبة — هذه الحالات تعني أن الموظف
# تكلم مع العميل فعلاً (اعتراض / أسلوب / الباقة ... إلخ)
_FORCE_CONTACTED_VALUES = [
    "أسلوب الموظف", "اسلوب الموظف",
    "اعتراض", "اعتراضات",          # ← مفرد وجمع
    "جودة الخدمة", "جوده الخدمه",
    "الباقة", "الباقه",
    "تأسيس وبداية خدمة", "تاسيس وبدايه خدمه", "تأسيس وبداية الخدمة",
    "مبلغ الفاتورة", "مبلغ الفاتوره",
]
# الاسم القديم للتوافق مع بقية الكود
_SUB_FORCE_CONTACTED = _FORCE_CONTACTED_VALUES

# ── حالات الفرعية التي تعني مغلق/مقطوع ضمن لا يرد ──────────────────────────
_SUB_CLOSED_VALUES = [
    "مقطوع", "مغلق", "لا يرد", "لايرد", "ما يرد", "مايرد",
]

# قيم "عدم توصل" الصريحة في الحالة الرئيسية — أعلى أولوية لا تُتجاوز أبداً
_EXPLICIT_NOT_CONTACT = [
    "عدم توصل", "عدم التوصل", "لا يرد", "لايرد",
    "مغلق", "خارج التغطية", "لا يوجد رد",
    "رسالة صوتية", "خط معطل", "لا يتم الاتصال",
    "لم يرد", "لم نتمكن من التواصل", "ارجاء",
    "ما يرد", "مايرد", "بيزي", "مجدول الاتصال",
    "لا يخص", "لايخص", "رقم خطأ", "الارقام لا تخص",
    "يرد وما يتكلم", "يرد وساكته", "ردت وساكته",
    "بريد صوتي", "بريد صوتيه", "لم يرد منذ امد",
    "ما رد", "لا يتكلم",
]

# كلمات عدم توصل في عمود المتابعة (تعطي خلاصة عملية الاتصال)
_FOLLOWUP_NOT_CONTACT_KW = [
    "لا يرد", "لايرد", "ما يرد", "مايرد", "مايردش",
    "مغلق", "خارج التغطية", "بيزي", "رسالة صوتية", "بريد صوتي",
    "لا يتكلم", "يرد وما يتكلم", "يرد وساكته", "ردت وساكته",
    "مجدول الاتصال", "خط معطل",
]


class ContactStatusModule:
    OUTPUT_COL = "حالة التوصل"

    def run(self, portfolio: pl.DataFrame) -> Dict:
        # إضافة كولوم عدد العملاء = 1 / countif(رقم الهوية)
        id_col = next((c for c in ["رقم الهوية", "الهوية"] if c in portfolio.columns), None)
        if id_col:
            portfolio = portfolio.with_columns(
                (pl.lit(1.0) / pl.col(id_col).count().over(id_col).cast(pl.Float64)).alias("عدد العملاء")
            )
        else:
            portfolio = portfolio.with_columns(pl.lit(1.0).alias("عدد العملاء"))

        df = portfolio.clone()

        main_col     = "الحالة الرئيسية" if "الحالة الرئيسية" in df.columns else None
        sub_col      = "الحالة الفرعية"  if "الحالة الفرعية"  in df.columns else None
        followup_col = next((c for c in ["آخر متابعة على العميل","تاريخ المتابعة","تاريخ الحالة","تاريخ ووقت الحالة"] if c in df.columns), None)
        note_col     = next((c for c in ["الملاحظة","الملاحظات","ملاحظة"] if c in df.columns), None)
        # عمود المتابعة (يحتوي على نص ملخص الاتصال)
        followup_text_col = next((c for c in ["المتابعة", "آخر متابعة", "متابعة", "نتيجة الاتصال"] if c in df.columns), None)

        # ── خطوة 1: تنظيف الأعمدة ────────────────────────────────────────
        main_expr = (pl.col(main_col) if main_col else pl.lit("")).cast(pl.String, strict=False).str.strip_chars().str.to_lowercase().fill_null("")
        sub_expr  = (pl.col(sub_col)  if sub_col  else pl.lit("")).cast(pl.String, strict=False).str.strip_chars().str.to_lowercase().fill_null("")
        note_expr = (pl.col(note_col) if note_col else pl.lit("")).cast(pl.String, strict=False).str.strip_chars().str.to_lowercase().fill_null("")
        date_expr = (pl.col(followup_col) if followup_col else pl.lit("")).cast(pl.String, strict=False).str.strip_chars().str.replace(r"\s+.*$", "").fill_null("")
        # عمود المتابعة النصي — لكشف عدم التوصل من خلال ملخص الاتصال
        followup_text_expr = (pl.col(followup_text_col) if followup_text_col else pl.lit("")).cast(pl.String, strict=False).str.strip_chars().str.to_lowercase().fill_null("").str.replace_all("أ", "ا").str.replace_all("إ", "ا").str.replace_all("آ", "ا").str.replace_all("ة", "ه").str.replace_all("ى", "ي")

        df = df.with_columns([
            main_expr.alias("_m"),
            sub_expr.alias("_s"),
            note_expr.alias("_n"),
            date_expr.alias("_d"),
            followup_text_expr.alias("_ft"),
        ])

        # ── خطوة 2: التصنيف الـ vectorized بالأولوية الصحيحة ──────────────
        #
        # الأولوية (من الأعلى للأدنى):
        # 1. الحالة الرئيسية "عدم توصل" صراحةً → عدم التوصل (لا تُتجاوز أبداً)
        # 2. الحالة الرئيسية في قائمة التوصل → تم التوصل
        # 3. الحالة الرئيسية في قائمة عدم التوصل → عدم التوصل
        # 4. الحالة الفرعية في قائمة التوصل → تم التوصل
        # 5. الحالة الفرعية في قائمة عدم التوصل → عدم التوصل
        # 6. كلمات مفتاحية توصل في (الرئيسية + الفرعية) → تم التوصل
        # 7. تاريخ متابعة صالح + ملاحظة ذات معنى → تم التوصل
        # 8. الافتراضي → عدم التوصل

        # 1. الحالة الرئيسية "عدم توصل" صريح — أعلى أولوية
        is_explicit_not_main = pl.col("_m").is_in(
            [s.lower() for s in _EXPLICIT_NOT_CONTACT]
        )

        # 2. الحالة الرئيسية توصل
        is_contacted_main = pl.col("_m").is_in(
            [s.lower() for s in _CONTACTED_LIST]
        )

        # 3. الحالة الرئيسية عدم توصل (القائمة الكاملة)
        is_not_main = pl.col("_m").is_in(
            [s.lower() for s in _NOT_CONTACTED_LIST]
        )

        # 4. الحالة الفرعية توصل
        is_contacted_sub = pl.col("_s").is_in(
            [s.lower() for s in _CONTACTED_LIST]
        )

        # 4b. الحالة الرئيسية أو الفرعية تفرض التوصل
        # (أسلوب الموظف / اعتراض / اعتراضات / جودة الخدمة ...)
        _force_vals = [
            s.replace("أ","ا").replace("إ","ا").replace("آ","ا")
             .replace("ة","ه").replace("ى","ي").lower()
            for s in _FORCE_CONTACTED_VALUES
        ]
        is_sub_force_contacted = (
            pl.col("_s").is_in(_force_vals) |
            pl.col("_m").is_in(_force_vals)
        )

        # 5. الحالة الفرعية عدم توصل
        is_not_sub = pl.col("_s").is_in(
            [s.lower() for s in _NOT_CONTACTED_LIST]
        )

        # 5b. تصنيف "لا يرد ومغلق"
        # الشرط الجديد: لو الحالة الرئيسية أو الفرعية تحتوي على
        # أي كلمة من: مقطوع / مغلق / مقفول / لا يرد / لايرد / ما يرد
        # → يُصنَّف كـ "لا يرد ومغلق"
        _CLOSED_PATTERN = r"مقطوع|مغلق|مقفول|لا\s*يرد|لايرد|ما\s*يرد|مايرد"
        # نستخدم الأعمدة المنظّفة بعد normalise (استبدال ا/ه/ي)
        _m_norm = pl.col("_m").str.replace_all("أ", "ا").str.replace_all("إ", "ا").str.replace_all("ة", "ه").str.replace_all("ى", "ي")
        _s_norm = pl.col("_s").str.replace_all("أ", "ا").str.replace_all("إ", "ا").str.replace_all("ة", "ه").str.replace_all("ى", "ي")
        is_not_contact_closed = (
            _m_norm.str.contains(_CLOSED_PATTERN) |
            _s_norm.str.contains(_CLOSED_PATTERN)
        )

        # 6. كلمات مفتاحية توصل في نص الحالة فقط
        combined = pl.concat_str([pl.col("_m"), pl.lit(" "), pl.col("_s")], ignore_nulls=True)
        kw_contacted = pl.lit(False)
        for kw in _CONTACT_KEYWORDS:
            kw_contacted = kw_contacted | combined.str.contains(kw, literal=True)

        # 7. عمود المتابعة يحتوي على كلمة عدم توصل (لا يرد / مغلق)
        is_followup_not_contact = pl.lit(False)
        for kw in _FOLLOWUP_NOT_CONTACT_KW:
            kw_norm = kw.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
            is_followup_not_contact = is_followup_not_contact | pl.col("_ft").str.contains(kw_norm, literal=True)

        # 8. تاريخ متابعة صالح
        d_parsed = (
            pl.col("_d").str.to_date("%m/%d/%Y", strict=False)
            .fill_null(pl.col("_d").str.to_date("%Y-%m-%d", strict=False))
            .fill_null(pl.col("_d").str.to_date("%d/%m/%Y", strict=False))
            .fill_null(pl.col("_d").str.to_date("%Y/%m/%d", strict=False))
            .fill_null(pl.col("_d").str.to_date("%d-%m-%Y", strict=False))
            .fill_null(pl.col("_d").str.to_date("%m-%d-%Y", strict=False))
        )
        has_date = d_parsed.is_not_null()

        # 8. ملاحظة ذات معنى
        has_note = ~pl.col("_n").is_in(_BLANK_VALUES) & (pl.col("_n") != "")

        # 9. عمود المتابعة يحتوي على كلمة عدم توصل
        is_followup_not_contact = pl.lit(False)
        for kw in _FOLLOWUP_NOT_CONTACT_KW:
            kw_norm = kw.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
            is_followup_not_contact = is_followup_not_contact | pl.col("_ft").str.contains(kw_norm, literal=True)

        # ── التصنيف النهائي بالأولوية الدقيقة ────────────────────────────
        # الأولوية:
        # 0. [جديد] الفرعية = أسلوب الموظف/اعتراض/جودة الخدمة/الباقة/... → تم التوصل (أعلى أولوية)
        # 1. [جديد] لا يرد ومغلق (رئيسية=لا يرد + فرعية=مقطوع/مغلق/لا يرد) → لا يرد ومغلق
        # 2. الحالة الرئيسية أو الفرعية تدل على التواصل الفعال → تم التوصل
        # 3. الحالة صريحة بعدم التوصل → عدم التوصل
        # 4. الكلمات المفتاحية للتوصل → تم التوصل
        # 5. تاريخ صالح + ملاحظة → تم التوصل
        # 6. الافتراضي = عدم التوصل

        status_text = combined

        is_contact_status = (
            status_text.str.contains(r"توصل|تتوصل|تواصل|طلب|مهلة|اعفاء|معترف|قريب|مراجعة|منتظم|سداد|وعد|تسوية|متابعه|متابعة|يرد|رافض|مسجون|متوفي|خروج|كامل|جزئى|اقساط") &
            ~status_text.str.contains(r"عدم توصل|عدم تتوصل|الرقم لا يخص|لا يوجد ارقام|غير مستعمل|غير صحيح") &
            ~(main_expr.str.contains(r"^(لايرد|لا يرد|مغلق)$") | sub_expr.str.contains(r"^(لايرد|لا يرد|مغلق)$"))
        )

        is_explicit_not_contact = (
            status_text.str.contains(r"عدم توصل|عدم تتوصل|غير مستعمل|لا يوجد|لايوجد|لا يخص|غير صحيح|لايرد|لا يرد|مغلق|قفل|بريد|بيزي|يكنسل|كنسل")
        )

        status_expr = (
            # 0. [جديد] الفرعية تفرض التوصل (أسلوب/اعتراض/جودة/الباقة/...) — أعلى أولوية
            pl.when(is_sub_force_contacted).then(pl.lit(CONTACTED))
            # 1. [جديد] لا يرد ومغلق (رئيسية=لا يرد + فرعية=مقطوع/مغلق/لا يرد)
            .when(is_not_contact_closed).then(pl.lit(NOT_CONTACT_CLOSED))
            # 2. الحالة الرئيسية أو الفرعية تدل على التواصل الفعال
            .when(is_contact_status).then(pl.lit(CONTACTED))
            # 3. الحالة صريحة بعدم التوصل
            .when(is_explicit_not_contact).then(pl.lit(NOT_CONTACTED))
            # 4. الحالة الرئيسية / الفرعية صريحة في قوائم التوصل
            .when(is_contacted_main | is_contacted_sub | kw_contacted).then(pl.lit(CONTACTED))
            # 5. تاريخ صالح + ملاحظة ذات معنى
            .when(has_date & has_note & ~is_followup_not_contact).then(pl.lit(CONTACTED))
            # 6. الافتراضي = عدم التوصل
            .otherwise(pl.lit(NOT_CONTACTED))
        )

        df = df.with_columns(status_expr.alias(self.OUTPUT_COL))
        df = df.drop(["_m", "_s", "_n", "_d", "_ft"])

        # ── Pivots ────────────────────────────────────────────────────────
        piv_sup  = self._build_pivot(df, "المشرف")
        piv_col  = self._build_pivot(df, self._collector_col(df))
        piv_stat = self._build_pivot(df, "الحالة الرئيسية")

        total              = len(df)
        contacted_cnt      = df.filter(pl.col(self.OUTPUT_COL) == CONTACTED).height
        closed_cnt         = df.filter(pl.col(self.OUTPUT_COL) == NOT_CONTACT_CLOSED).height
        not_cnt            = df.filter(pl.col(self.OUTPUT_COL) == NOT_CONTACTED).height
        total_not          = not_cnt + closed_cnt

        stats = {
            "إجمالي العملاء":        total,
            "تم التوصل":             contacted_cnt,
            "عدم التوصل":            not_cnt,
            "لا يرد ومغلق":          closed_cnt,
            "إجمالي عدم التوصل":     total_not,
            "نسبة التوصل %":         round(contacted_cnt / total * 100, 1) if total else 0.0,
            "نسبة عدم التوصل %":     round(total_not     / total * 100, 1) if total else 0.0,
        }

        return {
            "data":             df,
            "pivot_supervisor": piv_sup,
            "pivot_collector":  piv_col,
            "pivot_status":     piv_stat,
            "stats":            stats,
        }

    def _build_pivot(self, df: pl.DataFrame, group_col: str) -> pl.DataFrame:
        if not group_col or group_col not in df.columns:
            return pl.DataFrame()
        try:
            pivot = (
                df.group_by([group_col, self.OUTPUT_COL])
                .len()
                .pivot(on=self.OUTPUT_COL, index=group_col, values="len")
                .fill_null(0)
            )
            for col in [CONTACTED, NOT_CONTACTED, NOT_CONTACT_CLOSED]:
                if col not in pivot.columns:
                    pivot = pivot.with_columns(pl.lit(0).alias(col))
            pivot = pivot.with_columns(
                (pl.col(CONTACTED) + pl.col(NOT_CONTACTED) + pl.col(NOT_CONTACT_CLOSED)).alias("الإجمالي")
            )
            pivot = pivot.with_columns([
                (pl.col(CONTACTED)          / pl.col("الإجمالي") * 100).round(1).alias("نسبة التوصل %"),
                ((pl.col(NOT_CONTACTED) + pl.col(NOT_CONTACT_CLOSED)) / pl.col("الإجمالي") * 100).round(1).alias("نسبة عدم التوصل %"),
            ])
            return pivot
        except Exception as e:
            _log.warning("فشل إنشاء المحور لـ %s: %s", group_col, e)
            return pl.DataFrame()

    @staticmethod
    def _collector_col(df: pl.DataFrame) -> str:
        for c in ["المحصل", "الموظف", "اسم المحصل"]:
            if c in df.columns:
                return c
        return ""
