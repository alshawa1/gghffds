import streamlit as st
import pandas as pd
from io import BytesIO

def metric_card(label: str, value: str, delta: str = None, icon: str = ''):
    st.metric(label=f"{icon} {label}", value=value, delta=delta)

def show_error(msg: str):
    st.error(f"❌ {msg}")

def show_success(msg: str):
    st.success(f"✅ {msg}")

def show_warning(msg: str):
    st.warning(f"⚠️ {msg}")

def show_info(msg: str):
    st.info(f"ℹ️ {msg}")

def format_dataframe_arabic(df: pd.DataFrame) -> pd.DataFrame:
    """reorders columns right-to-left for display, practically we just return df or handle alignment in CSS."""
    return df

def download_excel_button(df: pd.DataFrame, filename: str, label: str):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    
    st.download_button(
        label=label,
        data=output.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
