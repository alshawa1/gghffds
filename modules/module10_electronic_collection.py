import polars as pl
from typing import Dict, Any, List, Optional
import datetime
from .module9_operations_report import _clean_float_val as _clean_float, _detect, _RE_ISO_DATE, _RE_US_DATE

class ElectronicCollectionModule:
    """
    برنامج التحصيل الإلكتروني.
    يعالج بيانات ملف التحصيل الإلكتروني، يقوم بفلترة الفرع والمشرف،
    يحسب التغطية بناءً على تاريخ المتابعة، ويصنف الحالات إلى: (توصل، عدم توصل، لا يرد-مغلق).
    كما يلخص البيانات بناءً على الـ Segment ونوع الخدمة.
    """

    def run(
        self,
        df: pl.DataFrame,
        report_mode: str = "coverage",
        target_date: Optional[datetime.date] = None,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
        branches: Optional[List[str]] = None,
        supervisors: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        تشغيل تقرير التحصيل الإلكتروني.
        """
        # 1. اكتشاف الأعمدة
        branch_col = _detect(df, ["الفرع", "branch"])
        sup_col = _detect(df, ["المشرف", "supervisor"])
        col_col = _detect(df, ["المحصل", "collector"])
        date_col = _detect(df, ["تاريخ المتابعة", "تاريخ المتابعه"])
        main_stat_col = _detect(df, ["الحالة الرئيسية", "الحاله الرئيسيه", "main status"])
        sub_stat_col = _detect(df, ["الحالة الفرعية", "الحاله الفرعيه", "sub status"])
        bal_col = _detect(df, ["متبقي سداد موثق", "متبقي", "balance"])
        segment_col = _detect(df, ["Segment", "segment"])
        service_col = _detect(df, ["نوع الخدمة", "نوع الخدمه"])

        # 2. الفلترة حسب الفرع والمشرف
        df_work = df.clone()
        if branch_col and branches:
            df_work = df_work.filter(pl.col(branch_col).cast(pl.String).is_in(branches))
        if sup_col and supervisors:
            df_work = df_work.filter(pl.col(sup_col).cast(pl.String).is_in(supervisors))

        if len(df_work) == 0:
            return {"error": "لا توجد بيانات مطابقة للفلاتر المحددة."}

        # 3. تجهيز الأعمدة
        # تحويل المتبقي إلى Float
        bal_expr = _clean_float(df_work[bal_col]) if bal_col else pl.Series([0.0] * len(df_work))
        df_work = df_work.with_columns(bal_expr.alias("_clean_bal"))

        # حساب التغطية بناءً على التاريخ
        # تنظيف التاريخ
        if date_col:
            date_expr = df_work[date_col].cast(pl.String, strict=False).fill_null("").str.strip_chars()
        else:
            date_expr = pl.Series([""] * len(df_work))

        # حساب التغطية بناءً على التاريخ
        if date_col and date_col in df_work.columns:
            date_expr = df_work[date_col].cast(pl.String, strict=False).fill_null("").str.strip_chars()
        else:
            date_expr = pl.Series([""] * len(df_work))

        if report_mode == "task2_coverage":
            if target_date:
                m_str = f"{target_date.month}"
                m_pad = f"{target_date.month:02d}"
                d_str = f"{target_date.day}"
                d_pad = f"{target_date.day:02d}"
                y_str = f"{target_date.year}"
                
                # Match M/D/YYYY, MM/DD/YYYY, YYYY-MM-DD, D/M/YYYY
                pattern1 = f"{m_str}/{d_str}/{y_str}"
                pattern2 = f"{m_pad}/{d_pad}/{y_str}"
                pattern3 = f"{y_str}-{m_pad}-{d_pad}"
                pattern4 = f"{d_str}/{m_str}/{y_str}"
                
                is_covered = (
                    date_expr.str.contains(pattern1) |
                    date_expr.str.contains(pattern2) |
                    date_expr.str.contains(pattern3) |
                    date_expr.str.contains(pattern4)
                )
                rep_period = f"يوم {target_date.strftime('%Y-%m-%d')}"
            else:
                is_covered = (date_expr.str.len_chars() > 0)
                rep_period = "تاريخ غير محدد (أول تاريخ متاح)"
            task_title = "2️⃣ تاسك نسبة التغطية والنسب"
        elif report_mode == "task1_contact":
            is_covered = pl.Series([True] * len(df_work))
            rep_period = "المحفظة كاملة"
            task_title = "1️⃣ تاسك حالات التواصل والنسب"
        else:
            # task3_comprehensive
            task_title = "3️⃣ تاسك التقرير الشامل (Segment + Service)"
            if start_date and end_date:
                try:
                    s_str = start_date.strftime("%Y-%m-%d")
                    e_str = end_date.strftime("%Y-%m-%d")
                    rep_period = f"الفترة من {s_str} إلى {e_str}"
                    
                    # Parse M/D/YYYY or YYYY-MM-DD
                    m1 = date_expr.str.extract(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})", 1).cast(pl.Int32, strict=False)
                    d1 = date_expr.str.extract(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})", 2).cast(pl.Int32, strict=False)
                    y1 = date_expr.str.extract(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})", 3).cast(pl.Int32, strict=False)
                    dt1 = pl.date(y1, m1, d1)

                    y2 = date_expr.str.extract(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})", 1).cast(pl.Int32, strict=False)
                    m2 = date_expr.str.extract(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})", 2).cast(pl.Int32, strict=False)
                    d2 = date_expr.str.extract(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})", 3).cast(pl.Int32, strict=False)
                    dt2 = pl.date(y2, m2, d2)

                    parsed_dt = pl.when(dt1.is_not_null()).then(dt1).otherwise(dt2)

                    is_covered = (parsed_dt >= start_date) & (parsed_dt <= end_date)
                    is_covered = is_covered.fill_null(False)
                except:
                    is_covered = (date_expr.str.len_chars() > 0)
                    rep_period = "شامل المحفظة"
            else:
                is_covered = (date_expr.str.len_chars() > 0)
                rep_period = "شامل المحفظة"

        df_work = df_work.with_columns(is_covered.alias("_is_covered"))

        # 4. حالات الاتصال (توصل، عدم توصل، لايرد-مغلق)
        main_stat_expr = df_work[main_stat_col].cast(pl.String, strict=False).fill_null("").str.strip_chars() if main_stat_col and main_stat_col in df_work.columns else pl.Series([""] * len(df_work))
        sub_stat_expr = df_work[sub_stat_col].cast(pl.String, strict=False).fill_null("").str.strip_chars() if sub_stat_col and sub_stat_col in df_work.columns else pl.Series([""] * len(df_work))
        
        main_empty = main_stat_expr.is_in(["", "---", "null", "none", "-"]) | (main_stat_expr.str.len_chars() == 0)
        sub_empty = sub_stat_expr.is_in(["", "---", "null", "none", "-"]) | (sub_stat_expr.str.len_chars() == 0)
        both_empty = main_empty & sub_empty

        status_text = main_stat_expr + " " + sub_stat_expr

        # 1. توصل (Contact): تشمل أي تواصل فعال، أو استجابة، أو طلب مهلة، أو مسدد/مسدد قبل الإسناد
        is_contact = (
            (status_text.str.contains(r"توصل|تتوصل|تواصل|طلب|مهلة|اعفاء|معترف|قريب|مراجعة|منتظم|سداد|وعد|تسوية|متابعه|متابعة|يرد|رافض|مسجون|متوفي|خروج|كامل|جزئى|اقساط|مسدد") |
             main_stat_expr.str.contains(r"مسدد قبل الاسناد|مسدد قبل الإسناد")) &
            ~status_text.str.contains(r"عدم توصل|عدم تتوصل|الرقم لا يخص|لا يوجد ارقام|غير مستعمل|غير صحيح") &
            ~(main_stat_expr.str.contains(r"^(لايرد|لا يرد|مغلق)$") | sub_stat_expr.str.contains(r"^(لايرد|لا يرد|مغلق)$")) &
            ~both_empty
        )
        
        # 2. لايرد - مغلق (No Answer / Closed)
        is_no_ans_closed = (
            (main_stat_expr.str.contains(r"^(لايرد|لا يرد|مغلق)$") | sub_stat_expr.str.contains(r"^(لايرد|لا يرد|مغلق)$") | status_text.str.contains(r"لايرد|مغلق")) &
            ~is_contact & ~both_empty
        )

        # 3. عدم توصل (No Contact): الصفوف الفاضية/الرموز + الحالات الصريحة بعدم التوصل
        is_no_contact = (~is_contact) & (~is_no_ans_closed)

        df_work = df_work.with_columns([
            pl.when(is_contact).then(1).otherwise(0).alias("_contact"),
            pl.when(is_no_contact).then(1).otherwise(0).alias("_no_contact"),
            pl.when(is_no_ans_closed).then(1).otherwise(0).alias("_no_ans_closed"),
        ])

        # 5. بناء جدول (المشرف / المحصل)
        def build_pivot(df: pl.DataFrame, grp_cols: List[str]) -> pl.DataFrame:
            valid_grps = [c for c in grp_cols if c and c in df.columns]
            if not valid_grps:
                return pl.DataFrame()
            
            agg = df.group_by(valid_grps).agg([
                pl.col("_contact").sum().alias("توصل"),
                pl.col("_no_contact").sum().alias("عدم توصل"),
                pl.col("_no_ans_closed").sum().alias("لايرد-مغلق"),
                pl.len().alias("عدد العملاء"),
                pl.col("_is_covered").sum().alias("العملاء المغطين")
            ])
            
            agg = agg.with_columns([
                (pl.col("عدد العملاء") - pl.col("العملاء المغطين")).alias("غير المغطين")
            ])

            agg = agg.with_columns([
                pl.when(pl.col("عدد العملاء") > 0).then((pl.col("توصل") / pl.col("عدد العملاء")) * 100).otherwise(0).round(2).alias("نسبة التوصل %"),
                pl.when(pl.col("عدد العملاء") > 0).then((pl.col("عدم توصل") / pl.col("عدد العملاء")) * 100).otherwise(0).round(2).alias("نسبة عدم التوصل %"),
                pl.when(pl.col("عدد العملاء") > 0).then((pl.col("لايرد-مغلق") / pl.col("عدد العملاء")) * 100).otherwise(0).round(2).alias("نسبة لايرد ومغلق %"),
                pl.when(pl.col("عدد العملاء") > 0).then((pl.col("العملاء المغطين") / pl.col("عدد العملاء")) * 100).otherwise(0).round(2).alias("نسبة التغطية %"),
                pl.when(pl.col("عدد العملاء") > 0).then((pl.col("غير المغطين") / pl.col("عدد العملاء")) * 100).otherwise(0).round(2).alias("نسبة عدم التغطية %")
            ]).sort(valid_grps[0] if valid_grps else "عدد العملاء")
            
            return agg

        pivot_supervisor = build_pivot(df_work, [sup_col] if sup_col else [])
        pivot_collector = build_pivot(df_work, [sup_col, col_col] if sup_col and col_col else ([col_col] if col_col else []))

        # 6. بناء جدول ملخص الـ Segment ونوع الخدمة
        segment_valid = segment_col if segment_col and segment_col in df_work.columns else None
        service_valid = service_col if service_col and service_col in df_work.columns else None
        
        segment_grp = []
        if segment_valid: segment_grp.append(segment_valid)
        if service_valid: segment_grp.append(service_valid)
        
        if segment_grp:
            pivot_segment = df_work.group_by(segment_grp).agg([
                pl.len().alias("عدد العملاء"),
                pl.col("_clean_bal").sum().alias("متبقي سداد موثق"),
                pl.col("_is_covered").sum().alias("تمت التغطية"),
                pl.col("_contact").sum().alias("توصل")
            ]).with_columns([
                pl.when(pl.col("عدد العملاء") > 0).then((pl.col("تمت التغطية") / pl.col("عدد العملاء")) * 100).otherwise(0).round(2).alias("نسبة التغطية %"),
                pl.when(pl.col("عدد العملاء") > 0).then((pl.col("توصل") / pl.col("عدد العملاء")) * 100).otherwise(0).round(2).alias("نسبة التوصل %")
            ]).sort("متبقي سداد موثق", descending=True)
        else:
            pivot_segment = pl.DataFrame()

        # 7. الإحصائيات العامة المخصصة بكل تاسك
        total_cust = len(df_work)
        total_cov = int(df_work["_is_covered"].sum())
        total_cnt = int(df_work["_contact"].sum())
        total_nocnt = int(df_work["_no_contact"].sum())
        total_noans = int(df_work["_no_ans_closed"].sum())
        total_bal = round(float(df_work["_clean_bal"].sum()), 2)

        if report_mode == "task1_contact":
            stats = {
                "المهمة المطلوبة": task_title,
                "إجمالي العملاء": total_cust,
                "إجمالي التوصل": total_cnt,
                "نسبة التوصل": f"{round((total_cnt/total_cust)*100, 2) if total_cust > 0 else 0}%",
                "إجمالي عدم التوصل": total_nocnt,
                "نسبة عدم التوصل": f"{round((total_nocnt/total_cust)*100, 2) if total_cust > 0 else 0}%",
                "إجمالي لايرد ومغلق": total_noans,
                "نسبة لايرد ومغلق": f"{round((total_noans/total_cust)*100, 2) if total_cust > 0 else 0}%",
                "إجمالي متبقي السداد": total_bal,
                "تاريخ التقرير": rep_period,
                "report_mode": report_mode
            }
        elif report_mode == "task2_coverage":
            stats = {
                "المهمة المطلوبة": task_title,
                "إجمالي العملاء": total_cust,
                "العملاء المغطين": total_cov,
                "نسبة التغطية": f"{round((total_cov/total_cust)*100, 2) if total_cust > 0 else 0}%",
                "العملاء غير المغطين": total_cust - total_cov,
                "نسبة عدم التغطية": f"{round(((total_cust - total_cov)/total_cust)*100, 2) if total_cust > 0 else 0}%",
                "إجمالي متبقي السداد": total_bal,
                "تاريخ التقرير": rep_period,
                "report_mode": report_mode
            }
        else:
            stats = {
                "المهمة المطلوبة": task_title,
                "إجمالي العملاء": total_cust,
                "العملاء المغطين": total_cov,
                "نسبة التغطية": f"{round((total_cov/total_cust)*100, 2) if total_cust > 0 else 0}%",
                "إجمالي التوصل": total_cnt,
                "نسبة التوصل": f"{round((total_cnt/total_cust)*100, 2) if total_cust > 0 else 0}%",
                "إجمالي متبقي السداد": total_bal,
                "تاريخ التقرير": rep_period,
                "report_mode": report_mode
            }

        # إلحاق كولومات التغطية والتواصل للشيت الأول (البيانات الأصلية) دون المساس بالبيانات الأصلية
        df_out = df_work.with_columns([
            pl.when(pl.col("_is_covered")).then(pl.lit("مغطي")).otherwise(pl.lit("غير مغطي")).alias("حالة التغطية"),
            pl.when(pl.col("_contact") == 1).then(pl.lit("توصل"))
            .when(pl.col("_no_contact") == 1).then(pl.lit("عدم توصل"))
            .when(pl.col("_no_ans_closed") == 1).then(pl.lit("لايرد-مغلق"))
            .otherwise(pl.lit("لم يتم الفحص")).alias("حالة التواصل")
        ]).drop(["_clean_bal", "_is_covered", "_contact", "_no_contact", "_no_ans_closed"])

        return {
            "data": df_out,
            "pivot_supervisor": pivot_supervisor,
            "pivot_collector": pivot_collector,
            "pivot_segment": pivot_segment,
            "stats": stats
        }
