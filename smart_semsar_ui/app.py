# import streamlit as st

# from components.sidebar import render_sidebar
# from utils.navigation import get_current_page
# from utils.session import initialize_session_state
# from views.dashboard import render_dashboard
# from views.voice_analysis import render_voice_analysis
# from views.customer_profile import render_customer_profile
# from views.properties import render_properties
# from views.recommendations import render_recommendations
# from views.alternatives import render_alternatives
# from views.virtual_staging import render_virtual_staging
# from views.booking import render_booking

# st.set_page_config(
#     page_title="Smart Semsar",
#     page_icon="🏡",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )

# initialize_session_state()
# render_sidebar()

# page = get_current_page()
# routes = {
#     "Dashboard": render_dashboard,
#     "Voice Analysis": render_voice_analysis,
#     "Customer Profile": render_customer_profile,
#     "Properties": render_properties,
#     "Recommendations": render_recommendations,
#     "Alternatives": render_alternatives,
#     "Virtual Staging": render_virtual_staging,
#     "Booking": render_booking,
# }
# routes.get(page, render_dashboard)()
import streamlit as st
import base64
import os

st.set_page_config(page_title="Smart Semsar - AI Platform", page_icon="🏡", layout="wide")

# دالة لتحويل الصورة إلى Base64 عشان الـ CSS يقراها بدون أخطاء
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# تهيئة حالة الجلسة
if "splash_done" not in st.session_state:
    st.session_state.splash_done = False

if not st.session_state.splash_done:
    # تحديد مسار الصورة
    image_path = "assets/SmartSemsarIntroScreen.png"
    
    page_bg_img = ""
    if os.path.exists(image_path):
        bin_str = get_base64_of_bin_file(image_path)
        page_bg_img = f"data:image/png;base64,{bin_str}"

    st.markdown(f"""
        <style>
        /* إخفاء الهيدر والـ Sidebar في صفحة الترحيب */
        header {{visibility: hidden;}}
        [data-testid="stSidebar"] {{display: none;}}
        
        .stApp {{
            background: linear-gradient(rgba(0,0,0,0.35), rgba(0,0,0,0.35)), url("{page_bg_img}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }}

        /* الحاوية الرئيسية لتوسيط كل شيء تماماً في المنتصف (رأسياً وأفقياً) */
        .hero-container {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 100%;
            max-width: 900px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            color: white;
            padding: 20px;
            z-index: 998;
        }}

        /* تصميم ذهبي لامع لـ Smart Semsar */
        .hero-title {{
            font-size: 4rem;
            font-weight: 900;
            background: linear-gradient(to bottom, #ffffff, #ffffff, #ffffff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            color: transparent;
            # text-shadow: 2px 2px 18px rgba(255, 255, 255, 0.7);
            margin-bottom: 12px;
            letter-spacing: 1.5px;
            animation: fadeIn 2s ease-in-out;
        }}

        .hero-subtitle {{
            font-size: 1.4rem;
            color: #ffffff;
            text-shadow: 1px 1px 6px rgba(0,0,0,0.9);
            margin-bottom: 35px;
            animation: fadeIn 2.5s ease-in-out;
        }}
        
        /* تصميم الزرار "أصفر أكتر وشيك وفي السنتر" */
        div.stButton > button {{
        
            background: linear-gradient(to right, #f1c40f, #e67e22) !important;
            color: white !important;
            font-size: 1.2rem !important;
            font-weight: 800 !important;
            border-radius: 50px !important;
            border: 2px solid #f1c40f !important;
            padding: 12px 45px !important;
            box-shadow: 0 4px 20px rgba(241, 196, 15, 0.7) !important;
            transition: all 0.3s ease-in-out !important;
            display: block !important;
            margin: 0 auto !important;
            
            
        }}
        
        div.stButton > button:hover {{
            background: linear-gradient(to right, #f39c12, #f1c40f) !important;
            transform: scale(1.08) !important;
            box-shadow: 0 6px 25px rgba(241, 196, 15, 0.9) !important;
        }}

        @keyframes fadeIn {{
            0% {{ opacity: 0; }}
            100% {{ opacity: 1; }}
        }}
        </style>
    """, unsafe_allow_html=True)

    # دمج العنوان والوصف والزرار داخل حاوية واحدة متسنترة تماماً رأسياً وأفقياً
    st.markdown("""
        <div class="hero-container">
            <div class="hero-title">Smart Semsar</div>
            <div class="hero-subtitle">Match • Visualize • Design - رحلتك العقارية الذكية تبدأ هنا</div>
        </div>
    """, unsafe_allow_html=True)

    # الزرار هنا على ارتفاع 70% من فوق (يعني 30% من أسفل الشاشة)
    st.markdown('<div style="position: fixed; top: 70%; left: 50%; transform: translate(-50%, -50%); z-index: 999;">', unsafe_allow_html=True)
    if st.button("🚀 Start your Journey!"):
        st.session_state.splash_done = True
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
else:
    # --- التطبيق الرئيسي بعد الدخول ---
    st.title("🏡 Smart Semsar - لوحة التحكم الرئيسية")
    st.write("أهلاً بكِ يا نوران، تم الدخول بنجاح! الشات والبايبلاين هنا...")
    
    if st.sidebar.button("🔄 العودة لصفحة الترحيب"):
        st.session_state.splash_done = False
        st.rerun()
    # وضع الزرار في المنتصف تماماً بطريقة تتجاوز قيود أعمدة Streamlit
    