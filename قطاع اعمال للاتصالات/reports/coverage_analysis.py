"""
Coverage Analysis Engine
Analyzes follow-up dates, contact statuses, and collection by date for daily/period reports.
"""
import pandas as pd
import warnings
from typing import Optional

# Status groups for contact categorization
REACHED_KEYWORDS = ['تم السداد', 'سداد جزئي', 'واعد بالسداد', 'طلب مهله', 'معاودة اتصال', 'متابعة', 'رفض السداد', 'لا يوجد رد', 'مسجون', 'متوفي', 'خروج نهائي', 'تسوية', 'اعتراض', 'مقطوع', 'الرقم غير صحيح', 'مسدد قبل الإسناد', 'العميل وعد', 'وعد', 'جدولة']
NO_ANSWER_KEYWORDS = ['لا يرد', 'لايرد', 'لم يرد', 'لم يرد']
SWITCHED_OFF_KEYWORDS = ['مغلق', 'موقف', 'محجوب', 'محجوز']
NOT_REACHED_KEYWORDS = ['عدم توصل', 'عدم التوصل', 'لم يتم التوصل']


def classify_contact_status(main_status: str, sub_status: str) -> str:
    """
    Classify a row's contact status into one of 4 categories:
    - توصل (Reached - contact made)
    - عدم توصل (Not Reached)
    - لا يرد (No Answer)
    - مغلق (Switched Off / Out of Service)
    """
    combined = f"{main_status} {sub_status}".strip().lower()
    main_str = str(main_status).strip()
    sub_str = str(sub_status).strip()
    
    # Check for "not reached" first
    for kw in NOT_REACHED_KEYWORDS:
        if kw in main_str or kw in sub_str:
            return 'عدم توصل'
    
    # Check for "no answer"
    for kw in NO_ANSWER_KEYWORDS:
        if kw in main_str or kw in sub_str:
            return 'لا يرد'
    
    # Check for "switched off"
    for kw in SWITCHED_OFF_KEYWORDS:
        if kw in main_str or kw in sub_str:
            return 'مغلق'
    
    # Anything with a valid status = reached
    if main_str and main_str not in ('', 'nan', '---', 'None'):
        return 'توصل'
    
    return 'عدم توصل'


def build_coverage_report(df: pd.DataFrame, col_map: dict,
                           selected_date=None,
                           payment_df: pd.DataFrame = None,
                           payment_map: dict = None,
                           target_coverage_count: int = 0,
                           target_collection_amount: float = 0.0,
                           report_mode: str = "daily",
                           start_date: str = None,
                           end_date: str = None,
                           selected_month: str = None) -> pd.DataFrame:
    """
    Build coverage/contact/collection report grouped by Supervisor → Collector.

    Rules:
    - يشمل جميع المشرفين والمحصلين الموجودين في المحفظة حتى لو لم يقدموا متابعات في اليوم المحدد (تظهر 0).
    - التغطية: عدد العملاء الفريدين (nunique بحسب رقم الهوية) الذين لديهم متابعة في التاريخ/الفترة المحددة.
    - مستهدف التغطية: المستهدف المدخل لكل محصل.
    - نسبة التغطية %: (العملاء المغطين / مستهدف التغطية) * 100 إذا وجد مستهدف، وإلا (العملاء المغطين / إجمالي عملاء المحصل) * 100.
    - التحصيل: مجموع مبالغ السداد من ملف السدادات مفلترة بنفس الفترة.
    - مستهدف التحصيل: المستهدف المدخل لكل محصل.
    - نسبة التحصيل %: (التحصيل / مستهدف التحصيل) * 100 إذا وجد مستهدف.
    """
    work_df = df.copy()

    def _resolve_col(work, col_map, eng_key, ar_key, fallback):
        """يبحث عن الكولوم بالمفتاح الإنجليزي ثم العربي ثم الاسم المباشر."""
        # 1) مفتاح إنجليزي
        val = col_map.get(eng_key)
        if val and val in work.columns:
            return val
        # 2) مفتاح عربي
        val = col_map.get(ar_key)
        if val and val in work.columns:
            return val
        # 3) الاسم المباشر كـ fallback
        if fallback in work.columns:
            return fallback
        return None

    cust_col        = _resolve_col(work_df, col_map, 'customer_id',    'رقم الهوية',       'رقم الهوية')
    sup_col         = _resolve_col(work_df, col_map, 'supervisor',      'المشرف',           'المشرف')
    coll_col        = _resolve_col(work_df, col_map, 'collector',       'المحصل',           'المحصل')
    date_col        = _resolve_col(work_df, col_map, 'followup_date',   'تاريخ المتابعة',   'تاريخ المتابعة')
    main_status_col = _resolve_col(work_df, col_map, 'main_status',     'الحالة الرئيسية',  'الحالة الرئيسية')
    sub_status_col  = _resolve_col(work_df, col_map, 'sub_status',      'الحالة الفرعية',   'الحالة الفرعية')

    # fallback آمن لو ما وجدناش الكولوم خالص
    if not cust_col:        cust_col        = '_customer_id'
    if not sup_col:         sup_col         = '_supervisor'
    if not coll_col:        coll_col        = '_collector'
    if not date_col:        date_col        = '_followup_date'
    if not main_status_col: main_status_col = '_main_status'
    if not sub_status_col:  sub_status_col  = '_sub_status'

    group_cols = [c for c in [sup_col, coll_col] if c in df.columns]
    if not group_cols:
        return pd.DataFrame()

    # ── 1. جميع مجموعات (المشرف، المحصل) في المحفظة
    all_collector_groups = list(df.groupby(group_cols).groups.keys())

    # ── 2. إجمالي العملاء الفريدين لكل محصل بالمحفظة الكلية
    total_collector_customers = df.groupby(group_cols)[cust_col].nunique().to_dict() if cust_col in df.columns else {}

    # ── 3. تحويل تاريخ المتابعة إلى string موحد YYYY-MM-DD
    if date_col in work_df.columns:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            # التواريخ بصيغة M/DD/YYYY (أمريكي) — لا نستخدم dayfirst=True
            parsed = pd.to_datetime(work_df[date_col], errors='coerce', dayfirst=False)
            # لو جزء كبير مش اتحول، نجرب dayfirst=True
            if parsed.isna().mean() > 0.5:
                parsed = pd.to_datetime(work_df[date_col], errors='coerce', dayfirst=True)
            work_df['_date_str'] = parsed.dt.strftime('%Y-%m-%d').fillna('')
    else:
        work_df['_date_str'] = ''

    # ── 4. فلترة بالتاريخ حسب نوع التقرير
    if selected_date:
        sel_clean = str(selected_date)[:10]
        covered_df = work_df[work_df['_date_str'] == sel_clean].copy()
    elif start_date and end_date:
        covered_df = work_df[
            (work_df['_date_str'] >= str(start_date)[:10]) &
            (work_df['_date_str'] <= str(end_date)[:10])
        ].copy()
    elif selected_month:
        covered_df = work_df[work_df['_date_str'].fillna('').str.startswith(str(selected_month)[:7])].copy()
    else:
        covered_df = work_df.copy()

    # ── 5. تصنيف حالة التواصل للمحتوى المغطى
    main_col = main_status_col if main_status_col in covered_df.columns else '_main_status'
    sub_col_name = sub_status_col if sub_status_col in covered_df.columns else '_sub_status'

    if not covered_df.empty:
        covered_df['فئة التواصل'] = covered_df.apply(
            lambda r: classify_contact_status(
                str(r.get(main_col, '')),
                str(r.get(sub_col_name, ''))
            ), axis=1
        )

    def count_category(grp, cat):
        if grp.empty or 'فئة التواصل' not in grp.columns:
            return 0
        sub = grp[grp['فئة التواصل'] == cat]
        return sub[cust_col].nunique() if cust_col in sub.columns else len(sub)

    # ── 6. فلترة ملف السدادات بنفس الفترة ──
    coll_per_group: dict = {}
    if payment_df is not None and not payment_df.empty and payment_map:
        pay_amount_col = payment_map.get('مبلغ السداد', payment_map.get('payment_amount', '_payment_amount'))
        if pay_amount_col not in payment_df.columns: pay_amount_col = '_payment_amount'
        pay_date_col = payment_map.get('تاريخ السداد', payment_map.get('payment_date', '_payment_date'))
        if pay_date_col not in payment_df.columns: pay_date_col = '_payment_date'

        # عمود المحصل في شيت السدادات (لو موجود)
        pay_coll_col = payment_map.get('المحصل', payment_map.get('collector', None))
        if pay_coll_col and pay_coll_col not in payment_df.columns:
            pay_coll_col = None

        # عمود المشرف في شيت السدادات (لو موجود)
        pay_sup_col = payment_map.get('المشرف', payment_map.get('supervisor', None))
        if pay_sup_col and pay_sup_col not in payment_df.columns:
            pay_sup_col = None

        pay_work = payment_df.copy()

        # ── فلترة التاريخ
        if pay_date_col in pay_work.columns:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                parsed_pay = pd.to_datetime(pay_work[pay_date_col], errors='coerce', dayfirst=False)
                if parsed_pay.isna().mean() > 0.5:
                    parsed_pay = pd.to_datetime(pay_work[pay_date_col], errors='coerce', dayfirst=True)
                pay_work['_pdate_str'] = parsed_pay.dt.strftime('%Y-%m-%d').fillna('')
            
            if selected_date:
                pay_work = pay_work[pay_work['_pdate_str'] == str(selected_date)[:10]]
            elif start_date and end_date:
                pay_work = pay_work[
                    (pay_work['_pdate_str'] >= str(start_date)[:10]) &
                    (pay_work['_pdate_str'] <= str(end_date)[:10])
                ]
            elif selected_month:
                pay_work = pay_work[pay_work['_pdate_str'].fillna('').str.startswith(str(selected_month)[:7])]

        def _to_clean_num(val):
            if pd.isna(val) or val is None:
                return 0.0
            if isinstance(val, (int, float)):
                return float(val)
            s = str(val).replace(',', '').replace(' ', '').replace('﷼', '').strip()
            try:
                return float(s)
            except:
                return 0.0

        pay_work[pay_amount_col] = pay_work[pay_amount_col].apply(_to_clean_num)

        if not pay_work.empty and pay_amount_col in pay_work.columns:

            # ── الطريقة الأولى (الأفضل): Group By اسم المحصل مباشرة من شيت السدادات
            if pay_coll_col and pay_coll_col in pay_work.columns:
                grp_cols_pay = []
                if pay_sup_col and pay_sup_col in pay_work.columns and sup_col in df.columns:
                    grp_cols_pay.append(pay_sup_col)
                if pay_coll_col in pay_work.columns and coll_col in df.columns:
                    grp_cols_pay.append(pay_coll_col)

                if grp_cols_pay:
                    pay_agg = pay_work.groupby(grp_cols_pay)[pay_amount_col].sum()
                    for k, v in pay_agg.items():
                        k_tuple = k if isinstance(k, tuple) else (k,)
                        matched_key = None
                        for portfolio_key in all_collector_groups:
                            pk = portfolio_key if isinstance(portfolio_key, tuple) else (portfolio_key,)
                            pay_coll_name = str(k_tuple[-1]).strip()
                            port_coll_name = str(pk[-1]).strip()
                            if pay_coll_name == port_coll_name:
                                if len(k_tuple) >= 2 and len(pk) >= 2:
                                    if str(k_tuple[0]).strip() == str(pk[0]).strip():
                                        matched_key = pk
                                        break
                                else:
                                    matched_key = pk
                                    break
                        if matched_key:
                            coll_per_group[matched_key] = coll_per_group.get(matched_key, 0.0) + _to_clean_num(v)

            # ── الطريقة الثانية (احتياطية): Join عن طريق رقم الهوية
            else:
                pay_cust_col = payment_map.get('رقم الهوية', payment_map.get('customer_id', '_customer_id'))
                if pay_cust_col not in pay_work.columns: pay_cust_col = '_customer_id'

                if cust_col in work_df.columns and pay_cust_col in pay_work.columns:
                    cust_coll_map = work_df[[cust_col] + group_cols].drop_duplicates()
                    cust_coll_map = cust_coll_map.rename(columns={cust_col: pay_cust_col})
                    pay_merged = pd.merge(
                        pay_work[[pay_cust_col, pay_amount_col]],
                        cust_coll_map, on=pay_cust_col, how='inner'
                    )
                    if not pay_merged.empty:
                        pay_agg = pay_merged.groupby(group_cols)[pay_amount_col].sum()
                        for k, v in pay_agg.items():
                            coll_per_group[k if isinstance(k, tuple) else (k,)] = _to_clean_num(v)

    # ── 7. تجميع بيانات العملاء المغطين لكل مجموعة محصلين
    covered_dict = {}
    if not covered_df.empty:
        for keys, grp in covered_df.groupby(group_cols):
            k_tuple = keys if isinstance(keys, tuple) else (keys,)
            covered_dict[k_tuple] = grp

    # ── 8. بناء صفوف النتائج لجميع المحصلين بالترتيب
    # تحويل جميع مفاتيح المجموعات إلى tuple من strings لتجنب خطأ المقارنة بين float وstr
    def _key_to_str_tuple(k):
        if isinstance(k, tuple):
            return tuple(str(x) if x is not None and not (isinstance(x, float) and pd.isna(x)) else '' for x in k)
        return (str(k) if k is not None and not (isinstance(k, float) and pd.isna(k)) else '',)

    all_collector_groups_clean = [
        k for k in all_collector_groups
        if not any(
            (isinstance(v, float) and pd.isna(v)) or str(v).strip() in ('', 'nan', 'None')
            for v in (k if isinstance(k, tuple) else (k,))
        )
    ]

    rows = []
    for keys in sorted(all_collector_groups_clean, key=_key_to_str_tuple):
        k_tuple = keys if isinstance(keys, tuple) else (keys,)
        grp = covered_dict.get(k_tuple, pd.DataFrame())

        tot_all_cust = total_collector_customers.get(k_tuple, 0)
        covered_cust = grp[cust_col].nunique() if (not grp.empty and cust_col in grp.columns) else 0

        reached      = count_category(grp, 'توصل')
        not_reached  = count_category(grp, 'عدم توصل')
        no_answer    = count_category(grp, 'لا يرد')
        switched_off = count_category(grp, 'مغلق')
        total_contact = reached + not_reached + no_answer + switched_off

        # نسبة التغطية: تقسم العملاء المغطين على مستهدف التغطية إذا وجد، وإلا على إجمالي العملاء
        if target_coverage_count > 0:
            coverage_rate = round((covered_cust / float(target_coverage_count)) * 100.0, 1)
        else:
            coverage_rate = round((covered_cust / float(tot_all_cust) * 100.0), 1) if tot_all_cust > 0 else 0.0

        coll_amt = coll_per_group.get(k_tuple, 0.0)

        # نسبة التحصيل
        if target_collection_amount > 0:
            coll_rate = round((coll_amt / float(target_collection_amount)) * 100.0, 1)
        else:
            coll_rate = 0.0

        row = {col: key for col, key in zip(group_cols, k_tuple)}
        row['إجمالي العملاء']         = tot_all_cust
        row['العملاء المغطين']        = covered_cust
        row['مستهدف التغطية']          = target_coverage_count
        row['نسبة التغطية %']         = coverage_rate
        row['إجمالي التحصيل']         = round(coll_amt, 2)
        row['مستهدف التحصيل']          = target_collection_amount
        row['نسبة التحصيل %']         = coll_rate
        row['توصل']                    = reached
        row['عدم توصل']               = not_reached
        row['لا يرد']                 = no_answer
        row['مغلق']                    = switched_off
        row['إجمالي المتابعة اليومية'] = total_contact
        row['نسبة التوصل %']          = round(reached / total_contact * 100.0, 1) if total_contact > 0 else 0.0
        row['نسبة تحقيق التغطية %']   = coverage_rate
        row['نسبة تحقيق التحصيل %']   = coll_rate

        rows.append(row)

    if not rows:
        return pd.DataFrame()

    coverage_df = pd.DataFrame(rows)

    # ── 9. صف الإجمالي المجمع
    total_row = {col: 'الإجمالي' for col in group_cols}
    sum_cols = ['إجمالي العملاء', 'العملاء المغطين', 'توصل', 'عدم توصل',
                'لا يرد', 'مغلق', 'إجمالي المتابعة اليومية', 'إجمالي التحصيل']
    for c in sum_cols:
        if c in coverage_df.columns:
            total_row[c] = coverage_df[c].sum()

    tot_cov = total_row.get('العملاء المغطين', 0)
    tot_all = total_row.get('إجمالي العملاء', 1)
    tot_col = total_row.get('إجمالي التحصيل', 0.0)
    tot_contact = total_row.get('إجمالي المتابعة اليومية', 1)

    n_collectors = len(rows)
    tot_target_cov = target_coverage_count * n_collectors
    tot_target_coll = target_collection_amount * n_collectors

    total_row['مستهدف التغطية'] = tot_target_cov
    if tot_target_cov > 0:
        total_row['نسبة التغطية %'] = round((tot_cov / float(tot_target_cov)) * 100.0, 1)
    else:
        total_row['نسبة التغطية %'] = round((tot_cov / float(tot_all)) * 100.0, 1) if tot_all > 0 else 0.0

    total_row['مستهدف التحصيل'] = tot_target_coll
    if tot_target_coll > 0:
        total_row['نسبة التحصيل %'] = round((tot_col / float(tot_target_coll)) * 100.0, 1)
    else:
        total_row['نسبة التحصيل %'] = 0.0

    total_row['نسبة تحقيق التغطية %'] = total_row['نسبة التغطية %']
    total_row['نسبة تحقيق التحصيل %'] = total_row['نسبة التحصيل %']
    total_row['نسبة التوصل %'] = round(total_row.get('توصل', 0) / tot_contact * 100.0, 1) if tot_contact > 0 else 0.0

    coverage_df = pd.concat([coverage_df, pd.DataFrame([total_row])], ignore_index=True)
    return coverage_df





def build_status_payment_report(df: pd.DataFrame, col_map: dict,
                                 payment_df: pd.DataFrame = None,
                                 payment_map: dict = None,
                                 date_from: str = None, date_to: str = None) -> pd.DataFrame:
    """
    Build payment-by-status report (like photo 2):
    الحالة الرئيسية | عدد الحسابات | المبلغ | السداد | النسبة | نسبة من إجمالي السداد
    """
    cust_col = col_map.get('customer_id', 'رقم الهوية')
    if cust_col not in df.columns: cust_col = '_customer_id'
    debt_col = col_map.get('debt_amount', 'مبلغ الميدونية')
    if debt_col not in df.columns: debt_col = 'مبلغ المديونية' if 'مبلغ المديونية' in df.columns else 'مبلغ الميدونية'
    rem_col = col_map.get('remaining_doc', 'متبقي سداد موثق')
    if rem_col not in df.columns: rem_col = '_remaining_doc'
    main_status_col = col_map.get('main_status', 'الحالة الرئيسية')
    if main_status_col not in df.columns: main_status_col = '_main_status'
    
    # Unique customers per status (dedup by customer + status)
    cust_status = df.drop_duplicates(subset=[cust_col]).copy() if cust_col in df.columns else df.copy()
    
    if debt_col in cust_status.columns:
        cust_status[debt_col] = pd.to_numeric(cust_status[debt_col], errors='coerce').fillna(0.0)
    
    group_result = cust_status.groupby(main_status_col).agg(
        عدد_الحسابات=(cust_col, 'count'),
        المبلغ=(debt_col, 'sum') if debt_col in cust_status.columns else (main_status_col, 'count'),
    ).reset_index()
    group_result.columns = ['الحالة الرئيسية', 'عدد الحسابات', 'المبلغ']
    
    # If payment file provided, match payments
    group_result['السداد'] = 0.0
    if payment_df is not None and not payment_df.empty:
        pay_cust_col = payment_map.get('customer_id', '_customer_id') if payment_map else '_customer_id'
        if pay_cust_col not in payment_df.columns: pay_cust_col = '_customer_id'
        pay_amount_col = payment_map.get('payment_amount', '_payment_amount') if payment_map else '_payment_amount'
        if pay_amount_col not in payment_df.columns: pay_amount_col = '_payment_amount'
        pay_date_col = payment_map.get('payment_date', '_payment_date') if payment_map else '_payment_date'
        
        pay_work = payment_df.copy()
        if date_from and pay_date_col in pay_work.columns:
            pay_work['_d'] = pay_work[pay_date_col].astype(str).str[:10]
            if date_to:
                pay_work = pay_work[(pay_work['_d'] >= str(date_from)[:10]) & (pay_work['_d'] <= str(date_to)[:10])]
            else:
                pay_work = pay_work[pay_work['_d'] == str(date_from)[:10]]
        
        # Aggregate payments per customer
        if pay_cust_col in pay_work.columns and pay_amount_col in pay_work.columns:
            pay_per_cust = pay_work.groupby(pay_cust_col)[pay_amount_col].sum().reset_index()
            pay_per_cust.columns = [cust_col, 'مبلغ_السداد']
            
            # Merge status info from portfolio
            status_cust = df[[cust_col, main_status_col]].drop_duplicates(subset=[cust_col]) if cust_col in df.columns else df[[main_status_col]]
            merged_pay = pd.merge(pay_per_cust, status_cust, on=cust_col, how='inner')
            
            if not merged_pay.empty:
                pay_by_status = merged_pay.groupby(main_status_col)['مبلغ_السداد'].sum().reset_index()
                pay_by_status.columns = ['الحالة الرئيسية', 'السداد']
                group_result = pd.merge(group_result, pay_by_status, on='الحالة الرئيسية', how='left')
                group_result['السداد'] = group_result['السداد_y'].fillna(0.0) if 'السداد_y' in group_result.columns else group_result['السداد'].fillna(0.0)
                if 'السداد_y' in group_result.columns:
                    group_result.drop(columns=['السداد_x', 'السداد_y'], inplace=True, errors='ignore')
    
    # Calculate percentages
    group_result['السداد'] = pd.to_numeric(group_result['السداد'], errors='coerce').fillna(0.0)
    group_result['النسبة %'] = (group_result['السداد'] / group_result['المبلغ'] * 100).replace([float('inf'), -float('inf')], 0.0).fillna(0.0).round(2)
    
    total_payment = group_result['السداد'].sum()
    group_result['نسبة من إجمالي السداد %'] = (group_result['السداد'] / total_payment * 100).replace([float('inf'), -float('inf')], 0.0).fillna(0.0).round(2) if total_payment > 0 else 0.0
    
    group_result = group_result.sort_values('السداد', ascending=False)
    
    # Add totals row
    total = {
        'الحالة الرئيسية': 'الإجمالي',
        'عدد الحسابات': group_result['عدد الحسابات'].sum(),
        'المبلغ': group_result['المبلغ'].sum(),
        'السداد': total_payment,
        'النسبة %': round(total_payment / group_result['المبلغ'].sum() * 100, 2) if group_result['المبلغ'].sum() > 0 else 0.0,
        'نسبة من إجمالي السداد %': 100.0
    }
    group_result = pd.concat([group_result, pd.DataFrame([total])], ignore_index=True)
    
    return group_result


def build_monthly_report(df: pd.DataFrame, col_map: dict,
                          payment_df: pd.DataFrame = None,
                          payment_map: dict = None,
                          selected_month: str = None) -> pd.DataFrame:
    """
    Build monthly summary report per portfolio (like photo 4).
    """
    cust_col = col_map.get('customer_id', 'رقم الهوية')
    if cust_col not in df.columns: cust_col = '_customer_id'
    debt_col = col_map.get('debt_amount', 'مبلغ الميدونية')
    if debt_col not in df.columns: debt_col = 'مبلغ المديونية' if 'مبلغ المديونية' in df.columns else 'مبلغ الميدونية'
    rem_col = col_map.get('remaining_doc', 'متبقي سداد موثق')
    if rem_col not in df.columns: rem_col = '_remaining_doc'
    port_col = col_map.get('portfolio', 'المحافظ')
    if port_col not in df.columns: port_col = '_portfolio'
    date_col = col_map.get('followup_date', 'تاريخ المتابعة')
    if date_col not in df.columns: date_col = '_followup_date'
    main_status_col = col_map.get('main_status', 'الحالة الرئيسية')
    
    for c in [debt_col, rem_col]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    
    # Portfolio-level summary
    port_summary = df.groupby(port_col).agg(
        عدد_العملاء=(cust_col, 'nunique') if cust_col in df.columns else (port_col, 'count'),
        إجمالي_المحفظة=(debt_col, 'sum') if debt_col in df.columns else (rem_col, 'sum'),
    ).reset_index()
    
    # Count successful contacts (المكالمات الناجحة) = rows where followup date is in the month and status != عدم توصل
    port_summary['إجمالي_التحصيل_الشهري'] = 0.0
    port_summary['المكالمات_الناجحة'] = 0
    
    # Payment collection per portfolio
    if payment_df is not None and not payment_df.empty and payment_map:
        pay_cust_col = payment_map.get('customer_id', '_customer_id')
        if pay_cust_col not in payment_df.columns: pay_cust_col = '_customer_id'
        pay_amount_col = payment_map.get('payment_amount', '_payment_amount')
        if pay_amount_col not in payment_df.columns: pay_amount_col = '_payment_amount'
        pay_date_col = payment_map.get('payment_date', '_payment_date')
        
        pay_work = payment_df.copy()
        if selected_month and pay_date_col in pay_work.columns:
            pay_work['_month'] = pay_work[pay_date_col].astype(str).str[:7]
            pay_work = pay_work[pay_work['_month'] == str(selected_month)[:7]]
        
        if not pay_work.empty and cust_col in df.columns and pay_cust_col in pay_work.columns:
            cust_port = df[[cust_col, port_col]].drop_duplicates(subset=[cust_col])
            cust_port.columns = [pay_cust_col, port_col]
            pay_merged = pd.merge(pay_work[[pay_cust_col, pay_amount_col]], cust_port, on=pay_cust_col, how='inner')
            if not pay_merged.empty:
                pay_by_port = pay_merged.groupby(port_col)[pay_amount_col].sum().reset_index()
                pay_by_port.columns = [port_col, 'إجمالي_التحصيل_الشهري']
                port_summary = pd.merge(port_summary, pay_by_port, on=port_col, how='left')
                port_summary['إجمالي_التحصيل_الشهري'] = port_summary['إجمالي_التحصيل_الشهري_y'].fillna(0.0) if 'إجمالي_التحصيل_الشهري_y' in port_summary.columns else port_summary['إجمالي_التحصيل_الشهري'].fillna(0.0)
                port_summary.drop(columns=[c for c in ['إجمالي_التحصيل_الشهري_x', 'إجمالي_التحصيل_الشهري_y'] if c in port_summary.columns], inplace=True)
    
    # نسبة التحصيل
    port_summary['إجمالي_التحصيل_الشهري'] = pd.to_numeric(port_summary.get('إجمالي_التحصيل_الشهري', 0), errors='coerce').fillna(0.0)
    port_summary['نسبة_التحصيل_%'] = (port_summary['إجمالي_التحصيل_الشهري'] / port_summary['إجمالي_المحفظة'] * 100).round(2).where(port_summary['إجمالي_المحفظة'] > 0, 0.0)
    
    # Rename columns to match the expected report format
    port_summary.columns = [c.replace('_', ' ') for c in port_summary.columns]
    
    # Add totals
    total = {port_col: 'الإجمالي'}
    for c in port_summary.columns[1:]:
        try:
            total[c] = port_summary[c].sum() if 'نسبة' not in c else port_summary[c].mean().round(2)
        except:
            total[c] = 0
    port_summary = pd.concat([port_summary, pd.DataFrame([total])], ignore_index=True)
    
    return port_summary
