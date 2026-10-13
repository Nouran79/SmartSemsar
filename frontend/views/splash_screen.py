import streamlit as st

def render_splash():
    st.markdown("""
        <style>
            .splash-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 70vh;
                text-align: center;
            }
            .splash-title {
                font-size: 3rem;
                font-weight: 700;
                color: #FF4B4B;
                margin-bottom: 10px;
            }
            .splash-subtitle {
                font-size: 1.2rem;
                color: #666;
                margin-bottom: 30px;
            }
        </style>
        <div class="splash-container">
            <div class="splash-title">🏡 Smart Semsar</div>
            <div class="splash-subtitle">منصتك الذكية لاكتشاف، معاينة، وتأثيث عقارك بالذكاء الاصطناعي</div>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 ابدأ رحلتك معنا", use_container_width=True, type="primary"):
            st.session_state.started_journey = True
            st.rerun()