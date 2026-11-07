import pandas as pd
import numpy as np

class BalanceEngine:
    @staticmethod
    def calculate_optimal_distribution(
        customers_or_df: pd.DataFrame, 
        target_collectors_or_ports: list = None,
        collector_portfolios_or_colmap: dict = None,
        method: str = 'remaining_balance'
    ) -> dict:
        """
        Calculates optimal load distribution per portfolio for collectors.
        Handles both call signatures:
        1. From DistributeEngine: (cust_agg_df, target_collectors_list, collector_portfolio_map, method) -> returns dict {collector: list_of_customer_ids}
        2. From UI Page 06: (full_df, selected_portfolios_list, column_map, method) -> returns dict {'success': True, 'balanced_df': ..., 'comparison': ...}
        """
        if customers_or_df.empty:
            if isinstance(collector_portfolios_or_colmap, dict) and 'customer_id' in collector_portfolios_or_colmap:
                return {'success': False, 'message': 'بيانات فارغة', 'balanced_df': pd.DataFrame()}
            return {}

        # Signature 1: DistributeEngine call (has 'customer_id' column in DataFrame)
        if 'customer_id' in customers_or_df.columns and 'portfolio' in customers_or_df.columns:
            customers = customers_or_df
            target_collectors = target_collectors_or_ports or []
            collector_portfolios = collector_portfolios_or_colmap or {}
            
            distribution = {collector: [] for collector in target_collectors}
            if customers.empty or not target_collectors:
                return distribution
                
            # Organize target collectors by portfolio
            portfolio_collectors = {}
            for coll in target_collectors:
                port = collector_portfolios.get(coll)
                if port not in portfolio_collectors:
                    portfolio_collectors[port] = []
                portfolio_collectors[port].append(coll)
                
            # Process each portfolio independently
            unassigned_customers = []
            for port in customers['portfolio'].unique():
                p_customers = customers[customers['portfolio'] == port].copy()
                p_collectors = portfolio_collectors.get(port, [])

                if not p_collectors:
                    unassigned_customers.append(p_customers)
                    continue

                if p_customers.empty:
                    continue

                # Determine metric to sort and balance by
                if method == 'equal' or method == 'customer_count':
                    p_customers['metric'] = 1.0
                elif method == 'debt_count':
                    p_customers['metric'] = p_customers['debt_count'].astype(float)
                elif method == 'dual_balance':
                    max_rem = p_customers['remaining_balance'].max() or 1.0
                    max_cnt = p_customers['debt_count'].max() or 1.0
                    p_customers['metric'] = (p_customers['remaining_balance'] / max_rem) + (p_customers['debt_count'] / max_cnt)
                else: # 'remaining_balance'
                    p_customers['metric'] = p_customers['remaining_balance'].astype(float)

                sorted_custs = p_customers.sort_values(by='metric', ascending=False)
                collector_loads = {c: 0.0 for c in p_collectors}

                for _, row in sorted_custs.iterrows():
                    min_coll = min(collector_loads, key=collector_loads.get)
                    distribution[min_coll].append(row['customer_id'])
                    collector_loads[min_coll] += row['metric']

            # If cross portfolio allowed, distribute unassigned customers across all target collectors
            if unassigned_customers and target_collectors:
                remaining_df = pd.concat(unassigned_customers, ignore_index=True)
                if not remaining_df.empty:
                    if method == 'equal' or method == 'customer_count':
                        remaining_df['metric'] = 1.0
                    elif method == 'debt_count':
                        remaining_df['metric'] = remaining_df['debt_count'].astype(float)
                    elif method == 'dual_balance':
                        max_rem = remaining_df['remaining_balance'].max() or 1.0
                        max_cnt = remaining_df['debt_count'].max() or 1.0
                        remaining_df['metric'] = (remaining_df['remaining_balance'] / max_rem) + (remaining_df['debt_count'] / max_cnt)
                    else:
                        remaining_df['metric'] = remaining_df['remaining_balance'].astype(float)

                    sorted_unassigned = remaining_df.sort_values(by='metric', ascending=False)
                    all_coll_loads = {c: len(distribution[c]) for c in target_collectors}
                    for _, row in sorted_unassigned.iterrows():
                        min_coll = min(all_coll_loads, key=all_coll_loads.get)
                        distribution[min_coll].append(row['customer_id'])
                        all_coll_loads[min_coll] += 1
            return distribution

        # Signature 2: Page 06 UI call (full DataFrame)
        df = customers_or_df
        selected_portfolios = target_collectors_or_ports or []
        column_map = collector_portfolios_or_colmap or {}

        col_cust = column_map.get('customer_id', 'رقم الهوية')
        if col_cust not in df.columns: col_cust = '_customer_id'
        col_debt = column_map.get('debt_amount', 'مبلغ الميدونية')
        if col_debt not in df.columns: col_debt = 'مبلغ المديونية' if 'مبلغ المديونية' in df.columns else 'مبلغ الميدونية'
        col_rem = column_map.get('remaining_doc', 'متبقي سداد موثق')
        if col_rem not in df.columns: col_rem = '_remaining_doc'
        col_port = column_map.get('portfolio', 'المحافظ')
        if col_port not in df.columns: col_port = '_portfolio'
        col_coll = column_map.get('collector', 'المحصل')
        if col_coll not in df.columns: col_coll = '_collector'
        col_sup = column_map.get('supervisor', 'المشرف')
        col_user = column_map.get('username', 'اسم المستخدم')

        sub_df = df[df[col_port].isin(selected_portfolios)].copy()
        if sub_df.empty:
            return {'success': False, 'message': 'لا توجد بيانات للمحافظ المختارة', 'balanced_df': pd.DataFrame()}

        balanced_rows = []

        for port in selected_portfolios:
            port_df = sub_df[sub_df[col_port] == port].copy()
            if port_df.empty:
                continue

            collectors = [c for c in port_df[col_coll].unique() if pd.notna(c) and str(c).strip()]
            if not collectors:
                continue

            cust_summary = port_df.groupby(col_cust).agg(
                remaining_balance=(col_rem, 'sum'),
                debt_count=(col_rem, 'count')
            ).reset_index()

            if method == 'customer_count':
                cust_summary['weight'] = 1.0
            elif method == 'remaining_balance':
                cust_summary['weight'] = cust_summary['remaining_balance']
            else: # dual_balance
                max_rem = cust_summary['remaining_balance'].max() or 1.0
                max_cnt = cust_summary['debt_count'].max() or 1.0
                cust_summary['weight'] = (cust_summary['remaining_balance'] / max_rem) + (cust_summary['debt_count'] / max_cnt)

            cust_summary = cust_summary.sort_values('weight', ascending=False)

            coll_loads = {c: 0.0 for c in collectors}
            coll_assignment = {}

            for _, row in cust_summary.iterrows():
                cid = row[col_cust]
                target_c = min(coll_loads, key=coll_loads.get)
                coll_assignment[cid] = target_c
                coll_loads[target_c] += row['weight']

            for cid, new_coll in coll_assignment.items():
                c_rows = port_df[port_df[col_cust] == cid].copy()
                c_rows['المحصل الجديد'] = new_coll
                
                tc_rows = port_df[port_df[col_coll] == new_coll]
                if not tc_rows.empty:
                    if col_sup in tc_rows.columns: c_rows['المشرف الجديد'] = tc_rows[col_sup].iloc[0]
                    if col_user in tc_rows.columns: c_rows['اسم المستخدم الجديد'] = tc_rows[col_user].iloc[0]
                
                balanced_rows.append(c_rows)

        if not balanced_rows:
            return {'success': False, 'message': 'تعذر إعادة التوازن', 'balanced_df': pd.DataFrame()}

        final_balanced_df = pd.concat(balanced_rows, ignore_index=True)

        before_summary = sub_df.groupby([col_port, col_coll]).agg(
            العملاء=(col_cust, 'nunique'),
            المديونيات=(col_rem, 'count'),
            المتبقي=(col_rem, 'sum')
        ).reset_index()
        before_summary.columns = ['المحفظة', 'المحصل', 'العملاء (قبل)', 'المديونيات (قبل)', 'المتبقي (قبل)']

        after_summary = final_balanced_df.groupby([col_port, 'المحصل الجديد']).agg(
            العملاء_بعد=(col_cust, 'nunique'),
            المديونيات_بعد=(col_rem, 'count'),
            المتبقي_بعد=(col_rem, 'sum')
        ).reset_index()
        after_summary.columns = ['المحفظة', 'المحصل', 'العملاء (بعد)', 'المديونيات (بعد)', 'المتبقي (بعد)']

        comparison = pd.merge(before_summary, after_summary, on=['المحفظة', 'المحصل'], how='outer').fillna(0)

        return {
            'success': True,
            'balanced_df': final_balanced_df,
            'comparison': comparison,
            'selected_portfolios': selected_portfolios
        }
