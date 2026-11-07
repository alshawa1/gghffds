# Neglect grace periods (days) - configurable
NEGLECT_GRACE_PERIODS = {
    'سداد جزئي': 10,
    'واعد بالسداد مع طلب مهلة': 7, 
    'واعد بالسداد': 3,
    'طلب مهلة للسداد': 7,
    'معاودة اتصال': 1,
    'default': 5,
}
# Columns that are required for basic operation
REQUIRED_COLS = ['رقم الهوية', 'المحافظ']
# Columns that are nice to have
IMPORTANT_COLS = ['رقم المديونية', 'مبلغ الميدونية', 'المحصل', 'المشرف', 'الحالة الرئيسية']
# Minimum remaining balance to consider for neglect
NEGLECT_MIN_BALANCE = 50.0
# App settings
APP_TITLE = 'قطاع أعمال الاتصالات - نظام إدارة المحافظ'
APP_VERSION = '1.0.0'
