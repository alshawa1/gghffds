import streamlit as st
import pandas as pd
from typing import Optional

def get_portfolio() -> Optional[pd.DataFrame]:
    return st.session_state.get('portfolio_df')

def set_portfolio(df: pd.DataFrame, meta: dict):
    st.session_state['portfolio_df'] = df
    st.session_state['portfolio_meta'] = meta

def get_payments() -> Optional[pd.DataFrame]:
    return st.session_state.get('payment_df')

def set_payments(df: pd.DataFrame, meta: dict):
    st.session_state['payment_df'] = df
    st.session_state['payment_meta'] = meta

def clear_all():
    for key in ['portfolio_df', 'portfolio_meta', 'payment_df', 'payment_meta']:
        st.session_state.pop(key, None)

def has_portfolio() -> bool:
    df = get_portfolio()
    return df is not None and len(df) > 0

def has_payments() -> bool:
    df = get_payments()
    return df is not None and len(df) > 0
