# -*- coding: utf-8 -*-
import streamlit as st
import sys
import os

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)

st.set_page_config(
    page_title="شركة مهاره للتحصيل - stc #1",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 DESIGN SYSTEM & CLASSIC PROFESSIONAL THEME (RTL - CAIRO)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Cairo', sans-serif !important;
        direction: RTL;
        background-color: #f8fafc !important;
        color: #0f172a !important;
    }
    
    .stApp {
        background-color: #f8fafc !important;
    }
    
    /* Classic Sidebar Styling */
    [data-testid="stSidebar"] {
        background: #ffffff !important;
        border-left: 1px solid #e2e8f0 !important;
    }
    [data-testid="stSidebar"] * {
        color: #1e293b !important;
    }
    
    .login-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        padding-top: 45px;
        padding-bottom: 25px;
    }
    
    .login-card {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 16px;
        padding: 40px 36px;
        max-width: 480px;
        width: 100%;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    }
    
    .brand-badge {
        display: inline-block;
        background: #f1f5f9;
        border: 1px solid #cbd5e1;
        color: #475569;
        padding: 4px 16px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 14px;
    }
    
    .logo-text {
        font-size: 34px;
        font-weight: 900;
        color: #0f172a;
        line-height: 1.3;
        margin-bottom: 6px;
    }
    
    .subtitle {
        color: #334155;
        font-size: 18px;
        font-weight: 800;
        margin-top: 0;
        margin-bottom: 14px;
        display: inline-block;
        background: #f1f5f9;
        border: 1px solid #e2e8f0;
        padding: 4px 18px;
        border-radius: 8px;
    }
    
    .classic-divider {
        height: 1px;
        background: #e2e8f0;
        margin: 18px 0;
    }
    
    .sector-chips {
        display: flex;
        justify-content: center;
        gap: 12px;
        margin-bottom: 24px;
    }
    
    .chip {
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        padding: 7px 16px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 700;
        color: #334155;
    }
    
    .sidebar-logo-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        margin-bottom: 20px;
    }
    
    .sidebar-logo-title {
        font-size: 20px;
        font-weight: 900;
        color: #0f172a;
        margin-bottom: 2px;
    }
    
    .sidebar-logo-sub {
        font-size: 14px;
        font-weight: 800;
        color: #475569;
    }
    
    .footer {
        color: #64748b;
        font-size: 13px;
        margin-top: 24px;
        font-weight: 600;
    }
    
    /* Input & Button Styling */
    .stTextInput > div > div > input {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #0f172a !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        font-size: 14px !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #475569 !important;
        box-shadow: 0 0 0 2px rgba(71, 85, 105, 0.15) !important;
    }
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 700 !important;
        background: #ffffff !important;
        color: #1e293b !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        background: #f1f5f9 !important;
        border-color: #94a3b8 !important;
        color: #0f172a !important;
    }
    .stButton > button[kind="primary"] {
        background: #1e293b !important;
        color: #ffffff !important;
        border: none !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #0f172a !important;
        color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

# 🔐 AUTHENTICATION GATE
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "sector" not in st.session_state:
    st.session_state.sector = None

if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("""
            <div class="login-wrapper">
                <div class="login-card">
                    <div class="brand-badge">⭐ نظام التحصيل الموحد</div>
                    <div class="logo-text">شركة مهاره للتحصيل</div>
                    <div class="subtitle">stc #1</div>
                    <div class="classic-divider"></div>
                    <div class="sector-chips">
                        <div class="chip">👥 قطاع الأفراد</div>
                        <div class="chip">🏢 قطاع الأعمال</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        pwd = st.text_input("كلمة المرور", type="password", label_visibility="collapsed", placeholder="أدخل كلمة المرور لدخول المنصة...")
        if st.button("🔓 دخول المنصة", use_container_width=True, type="primary"):
            if pwd in ("333", "افراد", "1234"):
                st.session_state.authenticated = True
                st.session_state.sector = "افراد"
                st.session_state.sector_display = "قطاع الأفراد"
                st.rerun()
            elif pwd in ("444", "اعمال"):
                st.session_state.authenticated = True
                st.session_state.sector = "اعمال"
                st.session_state.sector_display = "قطاع الأعمال"
                st.rerun()
            else:
                st.error("❌ كلمة المرور غير صحيحة. حاول مرة أخرى.")
        
        st.markdown('<div class="footer" style="text-align:center;">شركة مهاره للتحصيل © 2026 جميع الحقوق محفوظة</div>', unsafe_allow_html=True)
    st.stop()

# 🚀 LOGGED IN - SIDEBAR & SYSTEM ROUTING
with st.sidebar:
    st.markdown(f"""
        <div class="sidebar-logo-card">
            <div class="sidebar-logo-title">شركة مهاره للتحصيل</div>
            <div class="sidebar-logo-sub">stc #1</div>
            <div style="margin-top:10px;">
                <span class="chip">{'👥 ' if st.session_state.sector == 'افراد' else '🏢 '}{st.session_state.get('sector_display', 'النظام')}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.sector = None
        st.rerun()

# Run the selected sector app
import importlib
if st.session_state.sector == "افراد":
    import افراد_app
    importlib.reload(افراد_app)
    افراد_app.run_afrad_app()
elif st.session_state.sector == "اعمال":
    import اعمال_app
    importlib.reload(اعمال_app)
    اعمال_app.run_aamal_app()

