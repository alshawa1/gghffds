import pytest
import pandas as pd
from datetime import datetime, timedelta
from business_rules.neglect_rules import NeglectEngine

class TestNeglect:
    @pytest.fixture
    def setup_data(self):
        base_date = pd.to_datetime('2026-08-07')
        return pd.DataFrame({
            'رقم الهوية': ['101', '102', '103', '104', '105', '106', '107', '108'],
            'رقم المديونية': ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8'],
            'الحالة الرئيسية': ['سداد جزئي', 'واعد بالسداد', 'واعد بالسداد', 'معاودة اتصال', 'متابعة', 'عدم توصل', 'متابعة', '---'],
            'الحالة الفرعية': ['منتظم', 'طلب مهلة للسداد', 'مستمر', 'لايرد', 'متجاوب', 'مقطوع', 'متجاوب', ''],
            'تاريخ المتابعة': [
                base_date - timedelta(days=12), # > 10 -> neglected
                base_date - timedelta(days=8),  # > 7 -> neglected
                base_date - timedelta(days=4),  # > 3 -> neglected
                base_date - timedelta(days=2),  # > 1 -> neglected
                base_date - timedelta(days=6),  # > 5 -> neglected
                base_date - timedelta(days=20), # excluded
                base_date - timedelta(days=10), # low balance (<50) -> excluded
                base_date - timedelta(days=1)   # undefined -> neglected
            ],
            'متبقي سداد موثق': [1000, 1000, 1000, 1000, 1000, 1000, 40, 1000],
            'المحصل': ['Col1'] * 8,
            'المشرف': ['Sup1'] * 8
        })

    def test_saad_jazzi_10_days(self, setup_data, column_map):
        engine = NeglectEngine()
        result = engine.calculate(setup_data, column_map, today='2026-08-07')
        df_res = result['data']
        row = df_res[df_res['رقم المديونية'] == 'D1'].iloc[0]
        assert row['حالة الإهمال'] == 'مهمل'

    def test_waad_mehla_7_days(self, setup_data, column_map):
        engine = NeglectEngine()
        result = engine.calculate(setup_data, column_map, today='2026-08-07')
        df_res = result['data']
        row = df_res[df_res['رقم المديونية'] == 'D2'].iloc[0]
        assert row['حالة الإهمال'] == 'مهمل'

    def test_waad_no_mehla_3_days(self, setup_data, column_map):
        engine = NeglectEngine()
        result = engine.calculate(setup_data, column_map, today='2026-08-07')
        df_res = result['data']
        row = df_res[df_res['رقم المديونية'] == 'D3'].iloc[0]
        assert row['حالة الإهمال'] == 'مهمل'

    def test_moawadat_1_day(self, setup_data, column_map):
        engine = NeglectEngine()
        result = engine.calculate(setup_data, column_map, today='2026-08-07')
        df_res = result['data']
        row = df_res[df_res['رقم المديونية'] == 'D4'].iloc[0]
        assert row['حالة الإهمال'] == 'مهمل'

    def test_other_followup_5_days(self, setup_data, column_map):
        engine = NeglectEngine()
        result = engine.calculate(setup_data, column_map, today='2026-08-07')
        df_res = result['data']
        row = df_res[df_res['رقم المديونية'] == 'D5'].iloc[0]
        assert row['حالة الإهمال'] == 'مهمل'

    def test_excluded_adam_tawasol(self, setup_data, column_map):
        engine = NeglectEngine()
        result = engine.calculate(setup_data, column_map, today='2026-08-07')
        df_res = result['data']
        row = df_res[df_res['رقم المديونية'] == 'D6'].iloc[0]
        assert row['حالة الإهمال'] == 'مستثنى'

    def test_excluded_low_balance(self, setup_data, column_map):
        engine = NeglectEngine()
        result = engine.calculate(setup_data, column_map, today='2026-08-07')
        df_res = result['data']
        row = df_res[df_res['رقم المديونية'] == 'D7'].iloc[0]
        assert row['حالة الإهمال'] == 'مستثنى'

    def test_undefined_status_neglected(self, setup_data, column_map):
        engine = NeglectEngine()
        result = engine.calculate(setup_data, column_map, today='2026-08-07')
        df_res = result['data']
        row = df_res[df_res['رقم المديونية'] == 'D8'].iloc[0]
        assert row['حالة الإهمال'] == 'مهمل'

    def test_days_calculation_correct(self, setup_data, column_map):
        engine = NeglectEngine()
        result = engine.calculate(setup_data, column_map, today='2026-08-07')
        df_res = result['data']
        row = df_res[df_res['رقم المديونية'] == 'D1'].iloc[0]
        assert row['عدد أيام الإهمال'] == 12

    def test_stats_correct(self, setup_data, column_map):
        engine = NeglectEngine()
        result = engine.calculate(setup_data, column_map, today='2026-08-07')
        stats = result['stats']
        assert 'total_neglected' in stats
        assert 'total_excluded' in stats
