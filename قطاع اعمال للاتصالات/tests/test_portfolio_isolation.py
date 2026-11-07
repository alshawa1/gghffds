import pytest
import pandas as pd
from business_rules.portfolio_rules import PortfolioRules

class TestPortfolioIsolation:
    def test_same_portfolio_allowed(self):
        col_map = {'collector': 'محصل', 'portfolio': 'محفظة'}
        collector_portfolio_map = {'محصل A': 'محفظة 1'}
        is_valid, msg = PortfolioRules.validate_transfer('1001', 'محفظة 1', 'محصل A', collector_portfolio_map)
        assert is_valid == True

    def test_cross_portfolio_blocked(self):
        collector_portfolio_map = {'محصل B': 'محفظة 2'}
        is_valid, msg = PortfolioRules.validate_transfer('1001', 'محفظة 1', 'محصل B', collector_portfolio_map)
        assert is_valid == False
        assert len(msg) > 0  # any non-empty error message

    def test_get_customer_portfolio(self, sample_portfolio, column_map):
        port = PortfolioRules.get_customer_portfolio('1001', sample_portfolio, column_map)
        assert port == 'محفظة 1'
        port2 = PortfolioRules.get_customer_portfolio('1003', sample_portfolio, column_map)
        assert port2 == 'محفظة 2'

    def test_group_by_portfolio_no_mixing(self, sample_portfolio, column_map):
        grouped = PortfolioRules.group_by_portfolio(sample_portfolio, column_map)
        assert 'محفظة 1' in grouped
        assert 'محفظة 2' in grouped
        assert '1001' in grouped['محفظة 1']['رقم الهوية'].values
        assert '1001' not in grouped['محفظة 2']['رقم الهوية'].values

    def test_portfolio_stats_correct(self, sample_portfolio, column_map):
        df_stats = PortfolioRules.get_portfolio_stats(sample_portfolio, column_map)
        assert len(df_stats) == 2
        assert 'عدد العملاء' in df_stats.columns
