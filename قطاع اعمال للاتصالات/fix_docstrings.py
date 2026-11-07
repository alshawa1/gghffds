import os
import sys

base = r'c:\Users\dell\Downloads\فايلات مهاره\قطاع اعمال للاتصالات\business_rules'
files = ['neglect_rules.py', 'payment_rules.py', 'portfolio_rules.py', 'system_errors.py']
for fname in files:
    fpath = os.path.join(base, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    bad = '\\"\\"\\"'
    good = '"""'
    fixed = content.replace(bad, good)
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(fixed)
    sys.stderr.write(f'Fixed: {fname}\n')
sys.stderr.write('All fixed.\n')
