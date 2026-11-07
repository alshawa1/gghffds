import pandas as pd
from core import config

def validate_portfolio(df: pd.DataFrame) -> dict:
    errors = []
    warnings = []
    
    for col in config.REQUIRED_COLS:
        pass
            
    missing_id = (df['_customer_id'] == '').sum() if '_customer_id' in df.columns else 0
    missing_portfolio = (df['_portfolio'] == '').sum() if '_portfolio' in df.columns else 0
    
    if missing_id > 0:
        errors.append({'field': 'رقم الهوية', 'message': 'يوجد صفوف بدون رقم هوية', 'count': int(missing_id), 'severity': 'high'})
        
    if missing_portfolio > 0:
        errors.append({'field': 'المحافظ', 'message': 'يوجد صفوف بدون محفظة', 'count': int(missing_portfolio), 'severity': 'high'})
        
    neg_remaining = (df['_remaining_doc'] < 0).sum() if '_remaining_doc' in df.columns else 0
    if neg_remaining > 0:
        warnings.append({'field': 'متبقي سداد موثق', 'message': 'يوجد متبقي بالسالب', 'count': int(neg_remaining)})
        
    is_valid = len(errors) == 0
    
    return {
        'is_valid': is_valid,
        'errors': errors,
        'warnings': warnings,
        'stats': {
            'total_rows': len(df),
            'missing_id': int(missing_id),
            'missing_portfolio': int(missing_portfolio)
        }
    }
