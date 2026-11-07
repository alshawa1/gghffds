"""
tests/test_powerbi_export.py
=============================
Unit tests for Power BI Export Module.
Verifies Star Schema creation, DAX generation, Theme JSON, Validation, and ZIP packaging.
"""
import pytest
import pandas as pd
import zipfile
import io
from powerbi_exporter.builder import build_star_schema
from powerbi_exporter.validator import validate_package
from powerbi_exporter.dax_generator import generate_dax_measures
from powerbi_exporter.theme_generator import generate_theme_json
from powerbi_exporter.packager import create_powerbi_zip_package


@pytest.fixture
def sample_portfolio_df():
    return pd.DataFrame({
        '_customer_id': ['CUST001', 'CUST002', 'CUST003', 'CUST001'],
        'رقم الهوية': ['10101', '10102', '10103', '10101'],
        'مبلغ المديونية': [1000.0, 2000.0, 1500.0, 500.0],
        'متبقي سداد موثق': [800.0, 1500.0, 1000.0, 200.0],
        'السدادات الموثقة': [200.0, 500.0, 500.0, 300.0],
        'المحافظ': ['المحفظة الأولى', 'المحفظة الثانية', 'المحفظة الأولى', 'المحفظة الأولى'],
        'المحصل': ['أحمد', 'محمد', 'أحمد', 'أحمد'],
        'المشرف': ['علي', 'عمر', 'علي', 'علي'],
        'الحالة الرئيسية': ['تم السداد', 'طلب مهله', 'لا يرد', 'تم السداد'],
        'الحالة الفرعية': ['سداد كامل', 'مهلة 3 أيام', 'عدم الرد', 'سداد جزئي'],
        'تاريخ المتابعة': ['2026-08-01', '2026-08-02', '2026-08-03', '2026-08-04']
    })


@pytest.fixture
def sample_payment_df():
    return pd.DataFrame({
        '_customer_id': ['CUST001', 'CUST002'],
        'رقم الهوية': ['10101', '10102'],
        'مبلغ السداد': [200.0, 500.0],
        'تاريخ السداد': ['2026-08-05', '2026-08-06'],
        'المحصل': ['أحمد', 'محمد']
    })


def test_build_star_schema(sample_portfolio_df, sample_payment_df):
    col_map = {'customer_id': 'رقم الهوية', 'debt_amount': 'مبلغ المديونية', 'remaining_doc': 'متبقي سداد موثق'}
    pay_map = {'customer_id': 'رقم الهوية', 'payment_amount': 'مبلغ السداد'}

    schema = build_star_schema(sample_portfolio_df, col_map, sample_payment_df, pay_map)

    assert 'DimCustomer' in schema
    assert 'FactDebt' in schema
    assert 'FactPayment' in schema
    assert 'DimCollector' in schema
    assert 'DimSupervisor' in schema
    assert 'DimPortfolio' in schema
    assert 'DimDate' in schema

    # Check unique Customer ID in DimCustomer
    assert schema['DimCustomer']['Customer_ID'].is_unique


def test_validator(sample_portfolio_df, sample_payment_df):
    col_map = {'customer_id': 'رقم الهوية', 'debt_amount': 'مبلغ المديونية', 'remaining_doc': 'متبقي سداد موثق'}
    schema = build_star_schema(sample_portfolio_df, col_map, sample_payment_df)
    report = validate_package(schema)

    assert report['is_valid'] is True
    assert report['total_customers'] > 0
    assert report['total_debts'] == len(sample_portfolio_df)


def test_dax_and_theme():
    dax = generate_dax_measures()
    assert 'Core_Measures.txt' in dax
    assert 'Total Debt =' in dax['Core_Measures.txt']

    theme = generate_theme_json()
    assert '"name": "Maharah Corporate BI Theme"' in theme


def test_zip_package_creation(sample_portfolio_df, sample_payment_df):
    col_map = {'customer_id': 'رقم الهوية', 'debt_amount': 'مبلغ المديونية'}
    zip_bytes, report = create_powerbi_zip_package(sample_portfolio_df, col_map, sample_payment_df)

    assert len(zip_bytes) > 0
    assert report['is_valid'] is True

    # Read zip entries
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        namelist = zf.namelist()
        assert "PowerBI_Export/README.txt" in namelist
        assert "PowerBI_Export/Theme/PowerBI_Theme.json" in namelist
        assert "PowerBI_Export/Data/DimCustomer.xlsx" in namelist
        assert "PowerBI_Export/DAX/Core_Measures.txt" in namelist
