import streamlit as st
import base64
import os

def get_base64_of_bin_file(bin_file):
    if not os.path.exists(bin_file):
        return ""
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def render_splash():
    # تحديد المسار المطلق (Absolute Path) بصورة آمنة تماماً
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "..", "assets", "SmartSemsarIntroScreen.png")

    page_bg_img = ""
    if os.path.exists(image_path):
        bin_str = get_base64_of_bin_file(image_path)
        page_bg_img = f"data:image/jpeg;base64,{bin_str}"

    st.markdown(f"""
        <style>
            header {{visibility: hidden;}}
            
            .stApp {{
                background: linear-gradient(rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.5)), url("{page_bg_img}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-color: #1a1a1a;
            }}

            @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap');

            html, body, [class*="st-"] {{
                font-family: 'Tajawal', sans-serif;
            }}

            .splash-container {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 60vh;
                text-align: center;
                animation: fadeIn 1.5s ease-in-out;
            }}

            .splash-title {{
                font-size: 3.8rem;
                font-weight: 900;
                color: #f3e5ab;
                text-shadow: 0 4px 25px rgba(0, 0, 0, 0.9);
                margin-bottom: 5px;
                letter-spacing: 1.5px;
            }}

            .splash-subtitle {{
                font-size: 1.25rem;
                font-weight: 500;
                color: #e0e0e0;
                text-shadow: 0 2px 12px rgba(0, 0, 0, 0.9);
                letter-spacing: 2.5px;
                text-transform: uppercase;
            }}

            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(-15px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}

            /* تصميم الزرار الذهبي الفخم في مكانه */
            .stButton > button {{
                background: linear-gradient(135deg, #d4af37 0%, #aa771c 100%) !important;
                color: #ffffff !important;
                font-size: 1.15rem !important;
                font-weight: 700 !important;
                border-radius: 40px !important;
                border: 1px solid rgba(255, 255, 255, 0.4) !important;
                padding: 14px 40px !important;
                box-shadow: 0 8px 25px rgba(212, 175, 55, 0.4) !important;
                transition: all 0.3s ease-in-out !important;
                display: block !important;
                margin: 0 auto !important;
            }}

            .stButton > button:hover {{
                background: linear-gradient(135deg, #e6c547, #bc8420) !important;
                transform: translateY(-3px) scale(1.03) !important;
                box-shadow: 0 12px 30px rgba(212, 175, 55, 0.7) !important;
            }}
        </style>

        <div class="splash-container">
            <div class="splash-title">Smart Semsar</div>
            <div class="splash-subtitle">Match • Visualize • Design</div>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("ابدأ رحلتك معنا", use_container_width=True, type="primary"):
            st.session_state.started_journey = True
            st.rerun()