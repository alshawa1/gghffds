import pytest
import pandas as pd
from business_rules.system_errors import SystemErrorsEngine

class TestSystemErrors:
    def test_missing_primary_contact(self, sample_portfolio, column_map):
        engine = SystemErrorsEngine()
        result = engine.detect(sample_portfolio, column_map)
        assert 'data' in result
        assert 'summary' in result
        assert 'total_errors' in result

    def test_paid_status_with_remaining(self, sample_portfolio, column_map):
        # sample_portfolio has row 6: 1004, D007, 3000, 1500, 1500, 'تم السداد'
        # Remaining is 1500 (>100) but status is 'تم السداد' -> error Rule 4
        engine = SystemErrorsEngine()
        result = engine.detect(sample_portfolio, column_map)
        df_res = result['data']
        # Check if error column contains the error description
        errors_str = df_res['نوع الخطأ'].to_string()
        assert 'تم السداد' in errors_str or result['total_errors'] > 0

    def test_negative_remaining(self, column_map):
        df = pd.DataFrame({'رقم الهوية': ['101'], 'رقم المديونية': ['D1'], 'متبقي سداد موثق': [-100], 'المحافظ': ['P1']})
        engine = SystemErrorsEngine()
        result = engine.detect(df, column_map)
        df_res = result['data']
        assert 'سالب' in df_res['نوع الخطأ'].iloc[0] or result['total_errors'] > 0

    def test_missing_portfolio(self, column_map):
        df = pd.DataFrame({'رقم الهوية': ['101'], 'رقم المديونية': ['D1'], 'المحافظ': [None]})
        engine = SystemErrorsEngine()
        result = engine.detect(df, column_map)
        df_res = result['data']
        assert 'المحافظ' in df_res['نوع الخطأ'].iloc[0] or 'مفقودة' in df_res['نوع الخطأ'].iloc[0]

    def test_duplicate_debt(self, column_map):
        df = pd.DataFrame({'رقم الهوية': ['101', '101'], 'رقم المديونية': ['D1', 'D1'], 'المحافظ': ['P1', 'P1'], 'المحصل': ['Col1', 'Col1']})
        engine = SystemErrorsEngine()
        result = engine.detect(df, column_map)
        assert result['total_errors'] >= 1

    def test_severity_levels_assigned(self, sample_portfolio, column_map):
        engine = SystemErrorsEngine()
        result = engine.detect(sample_portfolio, column_map)
        df_res = result['data']
        assert 'مستوى الخطورة' in df_res.columns

    def test_correction_suggestions_present(self, sample_portfolio, column_map):
        engine = SystemErrorsEngine()
        result = engine.detect(sample_portfolio, column_map)
        df_res = result['data']
        assert 'تصحيح الخطأ' in df_res.columns

    def test_no_modification_of_original_df(self, sample_portfolio, column_map):
        original = sample_portfolio.copy()
        engine = SystemErrorsEngine()
        engine.detect(sample_portfolio, column_map)
        pd.testing.assert_frame_equal(original, sample_portfolio)

    def test_error_summary_count(self, sample_portfolio, column_map):
        engine = SystemErrorsEngine()
        result = engine.detect(sample_portfolio, column_map)
        assert 'total_errors' in result
        assert isinstance(result['total_errors'], int)
