import pytest
import pandas as pd
from business_rules.payment_rules import PaymentMatcher as BusinessPaymentMatcher
from payment_analysis.matching import PaymentMatcher
from payment_analysis.aggregation import PaymentAggregator

class TestPaymentMatching:
    def test_basic_match_by_customer(self, sample_portfolio, sample_payments, column_map):
        pm_map = {'customer_id': 'رقم الهوية', 'payment_amount': 'مبلغ السداد', 'payment_date': 'تاريخ السداد'}
        res = PaymentMatcher.match_payments(sample_portfolio, sample_payments, column_map, pm_map)
        assert 'matched_df' in res
        assert 'unmatched_payments' in res
        assert len(res['unmatched_payments']) == 1

    def test_no_double_counting_multi_debt(self, sample_portfolio, sample_payments, column_map):
        pm_map = {'customer_id': 'رقم الهوية', 'payment_amount': 'مبلغ السداد', 'payment_date': 'تاريخ السداد'}
        res = PaymentMatcher.match_payments(sample_portfolio, sample_payments, column_map, pm_map)
        matched = res['matched_df']
        c1001 = matched[matched['رقم الهوية'] == '1001']
        # Customer 1001 paid 500 total, payment column is 'مبلغ السداد'
        assert c1001['مبلغ السداد'].iloc[0] == 500.0

    def test_unmatched_payments(self, sample_portfolio, sample_payments, column_map):
        pm_map = {'customer_id': 'رقم الهوية', 'payment_amount': 'مبلغ السداد', 'payment_date': 'تاريخ السداد'}
        res = PaymentMatcher.match_payments(sample_portfolio, sample_payments, column_map, pm_map)
        unmatched = res['unmatched_payments']
        assert len(unmatched) == 1
        assert unmatched.iloc[0]['رقم الهوية'] == '9999'

    def test_date_range_filter(self, sample_portfolio, sample_payments, column_map):
        pm_map = {'customer_id': 'رقم الهوية', 'payment_amount': 'مبلغ السداد', 'payment_date': 'تاريخ السداد'}
        res = PaymentMatcher.match_payments(sample_portfolio, sample_payments, column_map, pm_map, date_from='2026-06-01', date_to='2026-06-30')
        assert res['stats']['total_matched'] > 0

    def test_match_by_debt_id(self, sample_portfolio, column_map):
        payments_by_debt = pd.DataFrame({
            'رقم الهوية': ['1001', '1003'],
            'رقم المديونية': ['D001', 'D004'],
            'مبلغ السداد': [200, 300],
            'تاريخ السداد': ['2026-06-14', '2026-06-14']
        })
        pm_map = {'customer_id': 'رقم الهوية', 'debt_id': 'رقم المديونية', 'payment_amount': 'مبلغ السداد', 'payment_date': 'تاريخ السداد'}
        res = PaymentMatcher.match_payments(sample_portfolio, payments_by_debt, column_map, pm_map, match_by_debt=True)
        assert res['stats']['total_matched'] == 500.0

    def test_empty_payments(self, sample_portfolio, column_map):
        empty_payments = pd.DataFrame(columns=['رقم الهوية', 'مبلغ السداد', 'تاريخ السداد'])
        pm_map = {'customer_id': 'رقم الهوية', 'payment_amount': 'مبلغ السداد', 'payment_date': 'تاريخ السداد'}
        res = PaymentMatcher.match_payments(sample_portfolio, empty_payments, column_map, pm_map)
        assert res['stats']['total_matched'] == 0.0

    def test_aggregation_by_collector(self, sample_portfolio, sample_payments, column_map):
        pm_map = {'customer_id': 'رقم الهوية', 'payment_amount': 'مبلغ السداد', 'payment_date': 'تاريخ السداد'}
        res = PaymentMatcher.match_payments(sample_portfolio, sample_payments, column_map, pm_map)
        agg = PaymentAggregator.aggregate_by_collector(res['matched_df'], column_map)
        assert 'محصل A' in agg['المحصل'].values

    def test_collection_rate_calculation(self, sample_portfolio, sample_payments, column_map):
        pm_map = {'customer_id': 'رقم الهوية', 'payment_amount': 'مبلغ السداد', 'payment_date': 'تاريخ السداد'}
        res = PaymentMatcher.match_payments(sample_portfolio, sample_payments, column_map, pm_map)
        stats = res['stats']
        assert 'match_rate' in stats
