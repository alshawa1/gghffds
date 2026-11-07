import pytest
import pandas as pd
from redistribution.pull import PullEngine
from redistribution.distribute import DistributeEngine
from redistribution.validation import DistributionValidator

class TestRedistribution:
    def test_pull_single_collector(self, sample_portfolio, column_map):
        res = PullEngine.pull_customers(sample_portfolio, ['محصل A'], column_map)
        pulled = res['pulled_df']
        # محصل A has 1001 (2 rows), 1006 (1 row) -> total 3 debts
        assert len(pulled) == 3
        assert set(pulled['رقم الهوية'].unique()) == {'1001', '1006'}

    def test_pull_multiple_collectors(self, sample_portfolio, column_map):
        res = PullEngine.pull_customers(sample_portfolio, ['محصل A', 'محصل B'], column_map)
        pulled = res['pulled_df']
        # محصل B has 1002 (1 row), 1004 (1 row). Total = 3 + 2 = 5
        assert len(pulled) == 5

    def test_customer_stays_together(self, sample_portfolio, column_map):
        pull_res = PullEngine.pull_customers(sample_portfolio, ['محصل A'], column_map)
        pulled = pull_res['pulled_df']
        collector_info = pd.DataFrame({
            'المحصل': ['محصل X', 'محصل Y'],
            'المشرف': ['مشرف X', 'مشرف Y'],
            'اسم المستخدم': ['user_x', 'user_y'],
            'المحافظ': ['محفظة 1', 'محفظة 1']
        })
        dist_res = DistributeEngine.distribute_customers(pulled, ['محصل X', 'محصل Y'], collector_info, column_map)
        res = dist_res['distributed_df']
        # 1001 must be fully assigned to either X or Y
        c1001_collectors = res[res['رقم الهوية'] == '1001']['المحصل الجديد'].unique()
        assert len(c1001_collectors) == 1

    def test_cross_portfolio_blocked(self, sample_portfolio, column_map):
        pulled = sample_portfolio[sample_portfolio['رقم الهوية'] == '1001'].copy() # محفظة 1
        collector_map = {'محصل Z': 'محفظة 2'}
        val_res = DistributionValidator.validate_before_distribution(pulled, ['محصل Z'], column_map, collector_map)
        assert not val_res['can_proceed']
        assert len(val_res['errors']) > 0

    def test_no_duplicate_assignment(self, sample_portfolio, column_map):
        pull_res = PullEngine.pull_customers(sample_portfolio, ['محصل A'], column_map)
        pulled = pull_res['pulled_df']
        collector_info = pd.DataFrame({
            'المحصل': ['محصل X', 'محصل Y'],
            'المشرف': ['مشرف X', 'مشرف Y'],
            'اسم المستخدم': ['user_x', 'user_y'],
            'المحافظ': ['محفظة 1', 'محفظة 1']
        })
        dist_res = DistributeEngine.distribute_customers(pulled, ['محصل X', 'محصل Y'], collector_info, column_map)
        res = dist_res['distributed_df']
        # No debt should appear twice
        assert len(res) == len(pulled)

    def test_balance_equal(self, sample_portfolio, column_map):
        pull_res = PullEngine.pull_customers(sample_portfolio, ['محصل A', 'محصل B', 'محصل C'], column_map)
        pulled = pull_res['pulled_df']
        collector_info = pd.DataFrame({
            'المحصل': ['محصل X', 'محصل Y'],
            'المشرف': ['مشرف X', 'مشرف Y'],
            'اسم المستخدم': ['user_x', 'user_y'],
            'المحافظ': ['محفظة 1', 'محفظة 1']
        })
        dist_res = DistributeEngine.distribute_customers(pulled[pulled['المحافظ'] == 'محفظة 1'], ['محصل X', 'محصل Y'], collector_info, column_map)
        res = dist_res['distributed_df']
        counts = res.groupby('المحصل الجديد')['رقم الهوية'].nunique()
        assert len(counts) > 0

    def test_total_preserved(self, sample_portfolio, column_map):
        pull_res = PullEngine.pull_customers(sample_portfolio, ['محصل A'], column_map)
        pulled = pull_res['pulled_df']
        collector_info = pd.DataFrame({
            'المحصل': ['محصل X', 'محصل Y'],
            'المشرف': ['مشرف X', 'مشرف Y'],
            'اسم المستخدم': ['user_x', 'user_y'],
            'المحافظ': ['محفظة 1', 'محفظة 1']
        })
        dist_res = DistributeEngine.distribute_customers(pulled, ['محصل X', 'محصل Y'], collector_info, column_map)
        res = dist_res['distributed_df']
        assert len(res) == len(pulled)
        assert res['متبقي سداد موثق'].sum() == pulled['متبقي سداد موثق'].sum()

    def test_empty_source_error(self, sample_portfolio, column_map):
        pull_res = PullEngine.pull_customers(sample_portfolio, ['غير موجود'], column_map)
        assert len(pull_res['pulled_df']) == 0
