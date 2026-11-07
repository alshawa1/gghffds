"""
tests/test_all_modules.py
─────────────────────────
Comprehensive automated test of all 7 business modules plus the data loader,
matcher, formatters, and excel writer. Uses synthetic mini DataFrames so no
real Excel files are needed.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Force UTF-8 stdout on Windows to avoid UnicodeEncodeError with emoji ──
import io
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import polars as pl
import traceback
from datetime import date, timedelta

PASS = "[PASS]"
FAIL = "[FAIL]"
results = []

def run(name, fn):
    try:
        fn()
        results.append((PASS, name))
    except Exception as e:
        results.append((FAIL, f"{name}\n     {e}\n     {traceback.format_exc().splitlines()[-2]}"))


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

TODAY = date.today().strftime("%Y-%m-%d")
YESTERDAY = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
TOMORROW = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
PAST = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")


def make_portfolio(n=10):
    sups = (["تركي"] * (n // 2 + 1) + ["لمياء"] * (n // 2 + 1))[:n]
    cols = (["محصل 1"] * (n // 3 + 1) + ["محصل 2"] * (n // 3 + 1) + ["محصل 3"] * (n // 3 + 1))[:n]
    return pl.DataFrame({
        "رقم الحساب":       [str(i) for i in range(1, n+1)],
        "رقم المديونية":    [str(i*10) for i in range(1, n+1)],
        "رقم الهوية":       [f"10{i:08d}" for i in range(1, n+1)],
        "الهوية":           [f"10{i:08d}" for i in range(1, n+1)],
        "اسم العميل":       [f"عميل {i}" for i in range(1, n+1)],
        "المشرف":           sups,
        "المحصل":           cols,
        "الحالة الرئيسية":  (["وعد بالسداد", "لا يرد", "سداد جزئي", "وعد بالسداد", "لا يرد",
                              "لا يرد", "وعد بالسداد", "غير محدد", "لا يرد", "لا يرد"] * (n // 10 + 1))[:n],
        "الحالة الفرعية":   (["طلب مهلة", "لم يرد", "", "", "",
                              "", "", "", "", ""] * (n // 10 + 1))[:n],
        "الملاحظة":         (["وعد بالسداد يوم الخميس", "لا يرد", "", "سيدفع",
                              "معاودة اتصال", "لا يرد", "تسوية", "", "متابعة", "قسط"] * (n // 10 + 1))[:n],
        "آخر متابعة على العميل": ([TODAY, PAST, TODAY, YESTERDAY, TODAY,
                                    PAST, PAST, PAST, PAST, TODAY] * (n // 10 + 1))[:n],
        "تاريخ التوزيع":    [PAST] * n,
        "مبلغ المديونية":   (["1000", "2000", "500", "3000", "4000",
                              "500", "6000", "700", "800", "900"] * (n // 10 + 1))[:n],
        "السدادات الموثقة": (["0", "0", "0", "0", "0",
                              "0", "0", "0", "0", "0"] * (n // 10 + 1))[:n],
        "متبقي سداد موثق":  (["1000", "2000", "500", "3000", "500",
                              "500", "6000", "700", "800", "900"] * (n // 10 + 1))[:n],
        "الرقم الرئيسي":    ["R"+str(i) if i % 3 != 0 else "" for i in range(1, n+1)],
    })


def make_promise(n=10):
    return pl.DataFrame({
        "رقم الحساب":       [str(i) for i in range(1, n+1)],
        "تاريخ وعد السداد": ([TOMORROW, PAST, TOMORROW, YESTERDAY, TOMORROW,
                              PAST, PAST, TOMORROW, PAST, TOMORROW] * (n // 10 + 1))[:n],
        "المصدر":           ["مهارة"] * n,
        "نوع المديونية":    ["B2C"] * n,
    })


def make_maharah(n=10):
    return pl.DataFrame({
        "رقم الحساب": [str(i) for i in range(1, n+1)],
        "رقم المديونية": [str(i*10) for i in range(1, n+1)],
        "EmpSadad_Id": [f"E{i}" for i in range(1, n+1)],
        "مبلغ السداد": [str(i * 50) for i in range(1, n+1)],
        "تاريخ السداد": [TODAY] * n,
    })


def make_company(n=10):
    return pl.DataFrame({
        "Account No.":    [str(i) for i in range(1, n+1)],
        "Service No.":    [f"S{i}" for i in range(1, n+1)],
        "Payment Amount": [str(i * 40) for i in range(1, n+1)],
        "Current Balance Due": (["100", "0", "200", "0", "0",
                                 "300", "400", "0", "500", "0"] * (n // 10 + 1))[:n],
    })


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

# --- core imports ---
def test_core_utils():
    from core.utils import parse_date, days_since, is_unclear, clean_text, get_today
    assert parse_date(None) is None
    assert parse_date("") is None
    assert parse_date("2025-01-15") is not None
    assert days_since("") is None
    assert isinstance(get_today(), date)
    assert is_unclear("") is True
    assert is_unclear("وعد بالسداد") is False
    assert clean_text("  مرحبا  ") == "مرحبا"

run("core/utils.py – date/text helpers", test_core_utils)


def test_core_data_loader():
    from core.data_loader import ValidationResult, SmartCache, FileClassifier
    vr = ValidationResult()
    assert vr.is_valid
    vr.add_error("test error")
    assert not vr.is_valid
    # Cache should return None for non-existent path
    assert SmartCache.get("nonexistent.xlsx") is None

run("core/data_loader.py – ValidationResult + SmartCache", test_core_data_loader)


def test_core_matcher():
    from core.matcher import Matcher
    left  = make_portfolio(5)
    right = make_promise(5)
    result = Matcher.enrich(left, right, ["تاريخ وعد السداد"])
    assert "تاريخ وعد السداد" in result.columns
    assert len(result) == 5
    # SUMIF test
    sums = Matcher.sumif(make_maharah(5), "رقم الحساب", "مبلغ السداد", left["رقم الحساب"])
    assert len(sums) == 5

run("core/matcher.py – enrich + sumif", test_core_matcher)


# --- Module 1 ---
def test_module1():
    from modules.module1_errors import SystemErrorsModule
    r = SystemErrorsModule().run(make_portfolio(), make_promise())
    assert "data" in r
    assert "stats" in r
    assert "الخطأ" in r["data"].columns, "Missing column: الخطأ"
    assert "تصحيح الخطأ" in r["data"].columns, "Missing column: تصحيح الخطأ"
    assert r["stats"]["إجمالي العملاء"] == 10
    # أكثر من خطأ في نفس الصف يُفصل بـ |
    errors_with_multi = r["data"].filter(pl.col("الخطأ").str.contains(" | ", literal=True))
    # تأكد أن التصحيح يتوافق مع الخطأ
    for row in r["data"].to_dicts():
        e_count = len([x for x in row["الخطأ"].split(" | ") if x]) if row["الخطأ"] else 0
        f_count = len([x for x in row["تصحيح الخطأ"].split(" | ") if x]) if row["تصحيح الخطأ"] else 0
        assert e_count == f_count, f"Mismatch errors vs fixes: {row['الخطأ']!r} vs {row['تصحيح الخطأ']!r}"


run("modules/module1_errors.py – System Errors", test_module1)


# --- Module 2 ---
def test_module2():
    from modules.module2_contact import ContactStatusModule
    r = ContactStatusModule().run(make_portfolio())
    assert "data" in r
    assert "حالة التوصل" in r["data"].columns
    assert r["stats"]["إجمالي العملاء"] == 10
    # Rows with blank statuses but good note/date should be classified
    contacted = r["data"].filter(pl.col("حالة التوصل") == "تم التوصل").height
    assert contacted > 0

run("modules/module2_contact.py – Contact Status + blank handling", test_module2)


# --- Module 3 ---
def test_module3():
    from modules.module3_neglect import NeglectModule
    r = NeglectModule().run(make_portfolio())
    assert "data" in r
    assert "full_analysis" in r, "Missing key: full_analysis"
    assert "stats" in r, "Missing key: stats"
    # عمود حالة الإهمال يجب أن يكون موجوداً في full_analysis
    status_col = "حالة الإهمال"
    assert status_col in r["full_analysis"].columns, f"Missing column: {status_col}"
    # عمود عدد أيام الإهمال يجب أن يكون موجوداً
    days_col = "عدد أيام الإهمال"
    assert days_col in r["full_analysis"].columns, f"Missing column: {days_col}"
    # stats تحتوي على إجمالي العملاء
    assert r["stats"]["إجمالي العملاء"] == len(r["full_analysis"])
    # data (شيت المهملين فقط) يحتوي فقط على المهملين
    if len(r["data"]) > 0:
        assert (r["data"][status_col] == "مهمل").all(), "data sheet should only contain مهمل rows"

run("modules/module3_neglect.py – Neglect Analysis", test_module3)


# --- Module 4 ---
def test_module4():
    from modules.module4_payments import PaymentsModule
    r = PaymentsModule().run(make_portfolio(), make_maharah(), make_company())
    assert "addition_data" in r
    assert "settlement_data" in r
    assert "edit_delete_data" in r
    assert "stats" in r

run("modules/module4_payments.py – Payments & Reconciliation", test_module4)


# --- Module 5 ---
def test_module5():
    from modules.module5_scheduling import SchedulingModule
    r = SchedulingModule().run(make_portfolio(), make_maharah())
    assert "data" in r
    assert "نوع الجدولة" in r["data"].columns
    assert r["stats"]["إجمالي العملاء"] == 10

run("modules/module5_scheduling.py – Scheduling", test_module5)


# --- Module 6 ---
def test_module6():
    from modules.module6_withdrawal import WithdrawalRotationModule
    r = WithdrawalRotationModule().run(make_portfolio(), make_promise())
    assert "data" in r
    assert "توصية السحب" in r["data"].columns
    assert r["stats"]["إجمالي العملاء"] == 10

run("modules/module6_withdrawal.py – Withdrawal & Rotation", test_module6)


# --- Module 7 ---
def test_module7():
    from modules.module7_targets import TargetCustomersModule
    r = TargetCustomersModule().run(make_portfolio(), make_promise(), make_maharah())
    assert "data" in r
    assert "العملاء المستهدفة" in r["data"].columns
    assert r["stats"]["إجمالي العملاء"] == 10

run("modules/module7_targets.py – Target Customers", test_module7)


# --- Excel writer ---
def test_excel_writer():
    import tempfile, os
    from export.excel_writer import ExcelReportWriter
    tmp = os.path.join(tempfile.gettempdir(), "stc_test.xlsx")
    writer = ExcelReportWriter(tmp)

    # Test each write method with synthetic data
    from modules.module1_errors import SystemErrorsModule
    from modules.module2_contact import ContactStatusModule
    from modules.module3_neglect import NeglectModule
    from modules.module4_payments import PaymentsModule
    from modules.module5_scheduling import SchedulingModule
    from modules.module6_withdrawal import WithdrawalRotationModule
    from modules.module7_targets import TargetCustomersModule

    port = make_portfolio()
    prom = make_promise()
    mah  = make_maharah()
    comp = make_company()

    r1 = SystemErrorsModule().run(port, prom)
    writer.write_errors(r1["data"])

    r2 = ContactStatusModule().run(port)
    writer.write_contact(r2["data"], r2["pivot_supervisor"], r2["pivot_collector"], r2["pivot_status"])

    r3 = NeglectModule().run(port)
    writer.write_neglect(r3["data"], r3["full_analysis"], r3["pivot_summary"], r3["pivot_supervisor"], r3["pivot_collector"], r3["pivot_status"], r3["pivot_branch"], r3["pivot_portfolio"], r3["pivot_days"])

    r4 = PaymentsModule().run(port, mah, comp)
    writer.write_addition(r4["addition_data"])
    writer.write_settlement(r4["settlement_data"])
    writer.write_edit_delete(r4["edit_delete_data"])

    r5 = SchedulingModule().run(port, mah)
    writer.write_scheduling(r5["data"], r5["pivot_type"], r5["pivot_month"], r5["pivot_year"], r5["pivot_count"], r5["pivot_supervisor"])

    r6 = WithdrawalRotationModule().run(port, prom)
    writer.write_withdrawal(r6["data"], r6["pivot_supervisor"])

    r7 = TargetCustomersModule().run(port, prom, mah)
    writer.write_targets(r7["data"], r7["pivot_supervisor"])

    all_stats = {**r1["stats"], **r2["stats"], **r3["stats"],
                 **r4["stats"], **r5["stats"], **r6["stats"], **r7["stats"]}

    writer.write_dashboard(all_stats, 8)
    writer.write_summary(all_stats)
    writer.save()

    assert os.path.exists(tmp), "Excel file was not saved!"
    size = os.path.getsize(tmp)
    assert size > 5000, f"Excel file too small ({size} bytes)"
    os.remove(tmp)

run("export/excel_writer.py – Full pipeline write + save", test_excel_writer)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("  STC SYSTEM - COMPREHENSIVE TEST RESULTS")
print("="*65)
for status, name in results:
    try:
        print(f"  {status}  {name}")
    except Exception:
        safe = name.encode('ascii', errors='replace').decode('ascii')
        print(f"  {status}  {safe}")
print("="*65)
passed = sum(1 for s, _ in results if "PASS" in s)
failed = len(results) - passed
print(f"  Total: {len(results)} | Passed: {passed} | Failed: {failed}")
print("="*65)
if failed:
    sys.exit(1)
