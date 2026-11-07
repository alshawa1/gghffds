import pandas as pd
import streamlit as st
from typing import Dict, Any, Tuple
from core import constants
import io

def detect_columns(df: pd.DataFrame, target_lists: Dict[str, list]) -> Dict[str, str]:
    mapping = {}
    df_cols = [str(c).strip() for c in df.columns]
    
    for key, aliases in target_lists.items():
        found = None
        # Pass 1: Exact match
        for alias in aliases:
            for c in df_cols:
                if c.lower() == alias.lower():
                    found = c
                    break
            if found:
                break
        
        # Pass 2: Substring match (alias in column name)
        if not found:
            for alias in aliases:
                for c in df_cols:
                    if alias.lower() in c.lower():
                        found = c
                        break
                if found:
                    break
        
        if found:
            mapping[key] = found
            
    return mapping

@st.cache_data
def load_portfolio_file(uploaded_file) -> Dict[str, Any]:
    warnings_list = []
    try:
        if isinstance(uploaded_file, str) or hasattr(uploaded_file, 'read'):
            # calamine أسرع بكثير من openpyxl في القراءة (3-5x)
            try:
                xls = pd.ExcelFile(uploaded_file, engine='calamine')
            except Exception:
                xls = pd.ExcelFile(uploaded_file)
            sheet_names = xls.sheet_names

            target_sheet = sheet_names[0]
            if 'XlsxTable' in sheet_names:
                target_sheet = 'XlsxTable'

            # dtype=str يمنع pandas من تخمين الأنواع → أسرع بكثير
            df = pd.read_excel(xls, sheet_name=target_sheet, dtype=str)
            # تحويل الكولومات الرقمية يتم لاحقاً في cleaner
        else:
            raise ValueError("Invalid file object")
            
        target_lists = {
            'رقم الهوية': constants.CUSTOMER_ID_COLS,
            'رقم المديونية': constants.DEBT_ID_COLS,
            'المحافظ': constants.PORTFOLIO_COLS,
            'المحصل': constants.COLLECTOR_COLS,
            'المشرف': constants.SUPERVISOR_COLS,
            'اسم المستخدم': constants.USERNAME_COLS,
            'مبلغ الميدونية': constants.DEBT_AMOUNT_COLS,
            'السدادات الموثقة': constants.PAID_DOC_COLS,
            'متبقي سداد موثق': constants.REMAINING_DOC_COLS,
            'الحالة الرئيسية': constants.MAIN_STATUS_COLS,
            'الحالة الفرعية': constants.SUB_STATUS_COLS,
            'تاريخ المتابعة': constants.FOLLOWUP_DATE_COLS,
            'المتابعة': constants.FOLLOWUP_NOTE_COLS,
        }
        
        column_map = detect_columns(df, target_lists)
        
        return {
            'raw_df': df,
            'column_map': column_map,
            'sheet_name': target_sheet,
            'row_count': len(df),
            'warnings': warnings_list,
            'error': None
        }
        
    except Exception as e:
        return {'error': str(e), 'raw_df': pd.DataFrame()}

@st.cache_data
def load_payment_file(uploaded_file) -> Dict[str, Any]:
    try:
        if isinstance(uploaded_file, str) or hasattr(uploaded_file, 'read'):
            try:
                df = pd.read_excel(uploaded_file, engine='calamine', dtype=str)
            except Exception:
                df = pd.read_excel(uploaded_file, dtype=str)
        else:
            raise ValueError("Invalid file object")
            
        target_lists = {
            'رقم الهوية': constants.CUSTOMER_ID_COLS,
            'رقم المديونية': constants.DEBT_ID_COLS,
            'مبلغ السداد': constants.PAYMENT_AMOUNT_COLS,
            'تاريخ السداد': constants.PAYMENT_DATE_COLS,
            'المحصل':      constants.COLLECTOR_COLS,
            'المشرف':      constants.SUPERVISOR_COLS,
        }
        
        column_map = detect_columns(df, target_lists)
        
        return {
            'raw_df': df,
            'column_map': column_map,
            'row_count': len(df),
            'error': None
        }
    except Exception as e:
        return {'error': str(e), 'raw_df': pd.DataFrame()}
