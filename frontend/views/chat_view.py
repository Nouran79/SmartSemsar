import streamlit as st
from langgraph.types import Command
import os
from dotenv import load_dotenv, find_dotenv
import uuid

# استيراد خدمات تليجرام والتقسيط
from backend.services.telegram_service import (
    generate_linking_token,
    verify_telegram_linking,
    send_property_report,
)
from backend.services.property_service import calculate_installments
from backend.services.google_calendar_service import create_viewing_event
import datetime

load_dotenv(find_dotenv())

def render_chat_flow():
    # --- تخصيص الـ CSS لترتيب السايدبار وجمال الواجهة بستايل ذهبي فخم ---
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap');

            /* 1. اتجاه الصفحة والخط العام */
            html, body, [data-testid="stAppViewContainer"] {
                direction: rtl;
                text-align: right;
                font-family: 'Tajawal', sans-serif !important;
            }

            /* خلفية التطبيق العامة بدرجة دافئة هادئة */
            [data-testid="stAppViewContainer"] {
                background: linear-gradient(135deg, #fbf9f5 0%, #f4ede2 100%);
            }

            /* 2. تصميم السايدبار الشيك والراقي */
            section[data-testid="stSidebar"] {
                background-color: #ffffff !important;
                border-left: 1px solid #e8dec8 !important;
            }

            section[data-testid="stSidebar"] > div:first-child {
                display: flex;
                flex-direction: column;
                height: 100vh;
                position: relative;
                padding-top: 3.5rem !important;
                padding-bottom: 0px !important;
                overflow: hidden !important;
            }

            /* 3. ضبط مساحة الصفحة الرئيسية على الشمال */
            div[data-testid="stAppViewContainer"] > section:nth-child(2) {
                margin-right: 21rem !important;
                margin-left: 0 !important;
            }

            /* 4. تصميم رسائل العميل بلمسة أنيقة */
            div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) {
                background-color: #fffdf9 !important;
                border: 1px solid #e8dec8 !important;
                border-radius: 16px 16px 4px 16px !important;
                padding: 12px;
                margin-bottom: 8px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
            }

            /* 5. تصميم رسائل المساعد */
            div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) {
                background-color: #f7f3eb !important;
                border: 1px solid #dfd2bc !important;
                border-radius: 16px 16px 16px 4px !important;
                padding: 12px;
                margin-bottom: 8px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
            }

            /* تنسيق أزرار المعاينة الذهبية */
            .stButton > button {
                background: linear-gradient(135deg, #d4af37 0%, #aa771c 100%) !important;
                color: #ffffff !important;
                font-weight: 700 !important;
                border-radius: 10px !important;
                border: none !important;
                padding: 8px 16px !important;
                box-shadow: 0 4px 15px rgba(212, 175, 55, 0.3) !important;
                transition: all 0.3s ease !important;
            }
            .stButton > button:hover {
                background: linear-gradient(135deg, #e6c547, #bc8420) !important;
                box-shadow: 0 6px 20px rgba(212, 175, 55, 0.5) !important;
                transform: translateY(-2px);
            }
        </style>
    """, unsafe_allow_html=True)

    # 1. تحميل الجراف
    @st.cache_resource
    def load_orchestrator():
        from backend.agents.semsar_graph import the_Orchestrator
        return the_Orchestrator

    try:
        the_Orchestrator = load_orchestrator()
    except Exception as e:
        st.error(f"❌ خطأ في تحميل الجراف أو موديلات الباك إند: {e}")
        st.stop()

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "browse_page" not in st.session_state:
        st.session_state.browse_page = 0

    if "show_checkout_page" not in st.session_state:
        st.session_state.show_checkout_page = False

    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    # ==================== 📱 الـ SIDEBAR ====================
    with st.sidebar:
        col_title, col_btn = st.columns([3, 1], vertical_alignment="center")
        with col_title:
            st.markdown("<h3 style='color: #aa771c; margin:0; font-weight: 700;'>Smart Semsar</h3>", unsafe_allow_html=True)
        with col_btn:
            st.markdown("""
                <style>
                div[data-testid="stSidebar"] button[kind="primary"] {
                    background: linear-gradient(135deg, #d4af37 0%, #aa771c 100%) !important;
                    color: white !important;
                    border: 1px solid rgba(255, 255, 255, 0.4) !important;
                    border-radius: 12px !important;
                    box-shadow: 0 4px 15px rgba(212, 175, 55, 0.3) !important;
                    font-weight: bold !important;
                }
                div[data-testid="stSidebar"] button[kind="primary"]:hover {
                    background: linear-gradient(135deg, #e6c547, #bc8420) !important;
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(212, 175, 55, 0.5) !important;
                }
                </style>
            """, unsafe_allow_html=True)
            
            if st.button("➕", help="بحث عقاري جديد", type="primary"):
                st.session_state.messages = []
                st.session_state.thread_id = str(uuid.uuid4())
                st.session_state.browse_page = 0
                st.session_state.show_checkout_page = False
                st.session_state.pop("selected_property_id", None)
                st.session_state.show_installment_plan = False
                st.rerun()

        # عرض الرسائل بانتظام
        chat_container = st.container(height=480)
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # صندوق إدخال الرسائل
        with st.form(key="chat_form", clear_on_submit=True):
            col_input, col_btn_send = st.columns([4, 1])
            with col_input:
                user_query = st.text_input("اكتب طلبك", placeholder="اكتب طلبك هنا...", label_visibility="collapsed")
            with col_btn_send:
                submit_button = st.form_submit_button("إرسال", use_container_width=True)

    # ==================== 🖥️ MAIN AREA ====================
    current_state = the_Orchestrator.get_state(config)
    graph_values = current_state.values if hasattr(current_state, "values") else {}
    macro_intent = graph_values.get("macro_intent", None)

    if submit_button and user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
        st.session_state.show_checkout_page = False
        
        with st.spinner("جاري المعالجة والبحث..."):
            try:
                if current_state.tasks and any(task.interrupts for task in current_state.tasks):
                    execution_input = Command(resume=user_query)
                else:
                    execution_input = {
                        "session_id": st.session_state.thread_id,
                        "user_input_type": "text",
                        "user_query": user_query,
                        "user_text": user_query,
                    }

                for event in the_Orchestrator.stream(execution_input, config=config):
                    pass

                updated_state = the_Orchestrator.get_state(config)
                if updated_state.tasks and any(task.interrupts for task in updated_state.tasks):
                    interrupt_payload = updated_state.tasks[0].interrupts[0].value
                    if not (isinstance(interrupt_payload, dict) and interrupt_payload.get("type") in ["property_selection", "general_browse"]):
                        interrupt_msg = str(interrupt_payload) if not isinstance(interrupt_payload, dict) else interrupt_payload.get("message", "")
                        st.session_state.messages.append({"role": "assistant", "content": interrupt_msg})
                else:
                    st.session_state.messages.append({"role": "assistant", "content": "تم تنفيذ الطلب بنجاح."})
                
                st.rerun()
            except Exception as ex:
                st.error(f"❌ حدث خطأ: {ex}")

    def extract_all_properties():
        if current_state.tasks and any(task.interrupts for task in current_state.tasks):
            int_val = current_state.tasks[0].interrupts[0].value
            if isinstance(int_val, dict) and int_val.get("properties"):
                return int_val.get("properties")

        from_graph = graph_values.get("top_properties") or graph_values.get("properties") or graph_values.get("filtered_properties")
        if from_graph:
            return from_graph

        try:
            from backend.services.property_service import search_properties
            return search_properties({}, "general_browse")
        except Exception:
            return []

    all_props = extract_all_properties()
    has_interrupt = current_state.tasks and any(task.interrupts for task in current_state.tasks)
    model_state = graph_values.get("model_state")
    
    propID = (
        graph_values.get("selected_property_id") or 
        graph_values.get("property_id") or 
        graph_values.get("current_property_id") or 
        st.session_state.get("selected_property_id")
    )

    # ----------------------------------------------------
    # صفحة إكمال العملية (Checkout / Action Hub)
    # ----------------------------------------------------
    if st.session_state.get("show_checkout_page", False):
        st.markdown("## 📋 إكمال عملية الحجز والمعاينة")
        st.markdown("---")
        
        # استخراج بيانات الشقة الحالية لعرضها
        current_prop = None
        for p in all_props:
            p_id = getattr(p, 'property_id', None) or (p.get('id') if isinstance(p, dict) else None)
            if str(p_id) == str(propID):
                current_prop = p
                break
        
        p_title = getattr(current_prop, 'title', None) or (current_prop.get('title') if isinstance(current_prop, dict) else 'عقار فاخر')
        p_price = getattr(current_prop, 'price', None) or (current_prop.get('price') if isinstance(current_prop, dict) else 2500000)
        p_location = getattr(current_prop, 'location', None) or (current_prop.get('location') if isinstance(current_prop, dict) else 'القاهرة الجديدة')
        p_bedrooms = getattr(current_prop, 'bedrooms', None) or (current_prop.get('bedrooms') if isinstance(current_prop, dict) else 3)
        p_area = getattr(current_prop, 'area_sqm', None) or (current_prop.get('area_sqm') if isinstance(current_prop, dict) else 180)

        # صندوق بيانات الشقة
        st.markdown(f"""
            <div style="
                background: #ffffff;
                border: 1px solid #e8dec8;
                border-radius: 16px;
                padding: 24px;
                margin-bottom: 24px;
                box-shadow: 0 4px 15px rgba(180, 150, 100, 0.05);
            ">
                <h3 style="color: #aa771c; margin-top:0;">{p_title} (#{propID})</h3>
                <p><b>الموقع:</b> {p_location} &nbsp;|&nbsp; <b>المساحة:</b> {p_area} متر مربع &nbsp;|&nbsp; <b>عدد الغرف:</b> {p_bedrooms}</p>
                <h4 style="color: #2c2c2c;">السعر الإجمالي: EGP {p_price:,.0f}</h4>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("### اختر الإجراء المطلوب:")
        
        
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            if st.button("1- إرسال التقرير لتليجرام", use_container_width=True):
                chat_id = st.session_state.get("telegram_chat_id")
                if not chat_id:
                    st.warning("⚠️ يرجى ربط حساب تليجرام أولاً أو إدخال الـ Chat ID.")
                else:
                    prop_info = {"id": propID, "title": p_title, "price": p_price, "location": p_location, "area_sqm": p_area, "bedrooms": p_bedrooms}
                    res = send_property_report(chat_id=chat_id, property_info=prop_info, customer_name="نوران أحمد")
                    if res.get("success"):
                        st.success("✅ تم إرسال التقرير لتليجرام بنجاح!")
                    else:
                        st.error(f"❌ خطأ: {res.get('error')}")

        with col_btn2:
            if st.button("2- كشف خطة التقسيط", use_container_width=True):
                st.session_state["show_installment_plan"] = True

        with col_btn3:
            if st.button("3- حجز موعد معاينة", use_container_width=True):
                st.session_state["show_booking_form"] = not st.session_state.get("show_booking_form", False)

        if st.session_state.get("show_booking_form", False):
            st.markdown("---")
            st.markdown("### 📅 تحديد موعد المعاينة على Google Calendar")
            
            col_date, col_time = st.columns(2)
            with col_date:
                booking_date = st.date_input("اختر تاريخ المعاينة", min_value=datetime.date.today())
            with col_time:
                booking_time = st.time_input("اختر وقت المعاينة", value=datetime.time(14, 0))
                
            cust_name = st.text_input("اسم العميل", value="نوران أحمد")
            cust_phone = st.text_input("رقم الهاتف", value="01000000000")
            booking_notes = st.text_area("ملاحظات إضافية للمعاينة", value="معاينة الشقة مع السمسار")

            if st.button("تأكيد الحجز والإضافة للتقويم 🚀", type="primary"):
                with st.spinner("جاري إنشاء الموعد على Google Calendar..."):
                    prop_info = {
                        "id": propID,
                        "title": p_title,
                        "location": p_location,
                        "price": p_price,
                        "bedrooms": p_bedrooms,
                        "area_sqm": p_area
                    }
                    
                    # استدعاء دالة الكاليندر الحقيقية
                    res = create_viewing_event(
                        property_info=prop_info,
                        customer_name=cust_name,
                        customer_phone=cust_phone,
                        appointment_date=booking_date.isoformat(),
                        appointment_time=booking_time.strftime("%H:%M"),
                        notes=booking_notes
                    )

                    if res.get("success"):
                        st.success("✅ تم حجز الموعد بنجاح وإضافته إلى Google Calendar الخاص بك!")
                        if res.get("html_link"):
                            st.markdown(f"[🔗 عرض الموعد في تقويم جوجل]({res.get('html_link')})")
                        st.session_state["show_booking_form"] = False
                    else:
                        st.error(f"❌ حدث خطأ أثناء الحجز: {res.get('error')}")
        # عرض خطة التقسيط لو المستخدم ضغط عليها
        if st.session_state.get("show_installment_plan", False):
            st.markdown("---")
            st.markdown("### 🧮 تفاصيل خطة التقسيط المقترحة")
            plan = calculate_installments(p_price, down_payment_percent=20.0, years=5, annual_interest_rate=0.0)
            st.markdown(f"""
            - **المقدم (20%):** EGP {plan.get('down_payment', 0):,.0f}
            - **القسط الشهري (على 5 سنوات):** EGP {plan.get('monthly_installment', 0):,.0f} / شهرياً
            - **المبلغ المتبقي:** EGP {plan.get('remaining', 0):,.0f}
            """)

        st.markdown("---")
        if st.button("العودة إلى المعاينة ثلاثية الأبعاد 3D", type="secondary"):
            st.session_state.show_checkout_page = False
            st.rerun()

    # ----------------------------------------------------
    # 1. الأولوية القصوى: عرض الـ 3D Staging لو الجولة جاهزة
    # ----------------------------------------------------
    elif model_state and getattr(model_state, "status", None) == "ready":
        walkthrough_path = getattr(model_state, "walkthrough_path", None)
        glb_path = getattr(model_state, "glb_path", None)
        
        if walkthrough_path and os.path.exists(walkthrough_path):
            try:
                with open(walkthrough_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                st.components.v1.html(html_content, height=600, scrolling=True)
            except Exception as e:
                st.error(f"❌ تعذر العرض: {e}")
                
        if glb_path and os.path.exists(glb_path):
            with open(glb_path, "rb") as file_to_download:
                st.download_button(
                    label="تحميل نموذج الـ 3D (GLB)",
                    data=file_to_download,
                    file_name=os.path.basename(glb_path),
                    mime="model/gltf-binary"
                )

        st.markdown("---")
        
        # الأزرار الأربعة تحت الـ 3D Staging
        col_rep, col_furnish, col_checkout, col_back_prop = st.columns(4)
        
        with col_rep:
            if st.button("عرض التقرير", use_container_width=True, type="primary"):
                st.session_state["current_page"] = "Report"
                st.info("صفحة التقرير قيد التجهيز، ترقبها قريباً!")
                
        with col_furnish:
            colab_base_url = "https://83528709e87eb08dbb.gradio.live"
            target_url = f"{colab_base_url}/?property_id={propID}"

            st.markdown(
                f'<a href="{target_url}" target="_blank" style="text-decoration:none;">'
                f'<button style="width:100%; background-color:#aa771c; color:white; border:none; padding:10px; border-radius:8px; font-weight:bold; cursor:pointer;">'
                f'فرش ومعاينة'
                f'</button></a>',
                unsafe_allow_html=True
            )

        with col_checkout:
            if st.button("اكمال العملية", use_container_width=True, type="primary"):
                st.session_state.show_checkout_page = True
                st.rerun()
        
        with col_back_prop:
            if st.button("اختيار شقة أخرى", use_container_width=True):
                # 1. إجبار الواجهة على الخروج من وضع الـ 3D والـ Checkout
                st.session_state.pop("selected_property_id", None)
                st.session_state.show_checkout_page = False
                st.session_state.show_installment_plan = False
                st.session_state.show_booking_form = False
                st.session_state["force_property_selection"] = True
                try:
                    the_Orchestrator.update_state(config, {
                        "model_state": None,
                        "selected_property_id": None,
                        "micro_intent": "property_selection"
                    })
                except Exception:
                    pass
                
                st.rerun()

    # ----------------------------------------------------
    # 2. حالة الـ Selection أو الـ Interrupt (اختيار شقة معينة)
    # ----------------------------------------------------
    elif has_interrupt or (macro_intent in ["property_selection", "recommendation", "search_by_reqs"]):
        st.markdown("### العقارات المقترحة والمطابقة لطلبك")
        
        if all_props:
            for idx, prop in enumerate(all_props):
                p_id = getattr(prop, 'property_id', None) or (prop.get('id') if isinstance(prop, dict) else (prop.get('property_id') if isinstance(prop, dict) else idx))
                p_title = getattr(prop, 'title', None) or (prop.get('title') if isinstance(prop, dict) else 'عقار فاخر')
                p_price = getattr(prop, 'price', None) or (prop.get('price') if isinstance(prop, dict) else 0)
                p_location = getattr(prop, 'location', None) or (prop.get('location') if isinstance(prop, dict) else 'مصر')
                p_bedrooms = getattr(prop, 'bedrooms', None) or (prop.get('bedrooms') if isinstance(prop, dict) else 3)
                p_area = getattr(prop, 'area_sqm', None) or (prop.get('area_sqm') if isinstance(prop, dict) else 180)

                st.markdown(f"""
                    <div style="
                        background: #ffffff;
                        border: 1px solid #e8dec8;
                        border-radius: 16px;
                        padding: 20px 24px;
                        margin-bottom: 12px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        box-shadow: 0 6px 20px rgba(180, 150, 100, 0.06);
                    ">
                        <div>
                            <div style="font-size: 0.75rem; color: #8c7b65; margin-bottom: 4px; font-weight: 600;">رقم المعرف: #{p_id}</div>
                            <div style="font-size: 1.2rem; font-weight: 700; color: #2c2c2c; margin-bottom: 6px;">{p_title}</div>
                            <div style="color: #6c5d47; font-size: 0.9rem; margin-bottom: 8px;">الموقع: {p_location}</div>
                            <div style="font-size: 0.85rem; color: #6b7280; font-weight: 500;">
                                عدد الغرف: {p_bedrooms} &nbsp;&nbsp;|&nbsp;&nbsp; المساحة: {p_area} متر مربع
                            </div>
                        </div>
                        <div style="text-align: left;">
                            <div style="font-size: 1.25rem; font-weight: 800; color: #aa771c; margin-bottom: 10px;">EGP {p_price:,.0f}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                col_space, col_btn = st.columns([4, 1])
                with col_btn:
                    if st.button("معاينة ثلاثية الأبعاد", key=f"sel_prop_{p_id}_{idx}", use_container_width=True):
                        st.session_state["selected_property_id"] = p_id
                        
                        with st.spinner("جاري معالجة الاختيار وتوليد نموذج الـ 3D..."):
                            try:
                                for event in the_Orchestrator.stream(Command(resume=p_id), config=config):
                                    pass
                                st.rerun()
                            except Exception as ex:
                                st.error(f"❌ حدث خطأ: {ex}")

    # ----------------------------------------------------
    # 3. حالة الـ General Browse
    # ----------------------------------------------------
    elif macro_intent == "general_browse":
        st.markdown("### كافة العقارات المتاحة للتصفح")
        if all_props:
            ITEMS_PER_PAGE = 6
            total_props = len(all_props)
            total_pages = (total_props + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if total_props > 0 else 1

            start_idx = st.session_state.browse_page * ITEMS_PER_PAGE
            end_idx = min(start_idx + ITEMS_PER_PAGE, total_props)
            current_page_props = all_props[start_idx:end_idx]

            for idx, prop in enumerate(current_page_props):
                global_idx = start_idx + idx
                p_id = getattr(prop, 'property_id', None) or (prop.get('id') if isinstance(prop, dict) else (prop.get('property_id') if isinstance(prop, dict) else global_idx))
                p_title = getattr(prop, 'title', None) or (prop.get('title') if isinstance(prop, dict) else 'عقار فاخر')
                p_price = getattr(prop, 'price', None) or (prop.get('price') if isinstance(prop, dict) else 0)
                p_location = getattr(prop, 'location', None) or (prop.get('location') if isinstance(prop, dict) else 'مصر')
                p_bedrooms = getattr(prop, 'bedrooms', None) or (prop.get('bedrooms') if isinstance(prop, dict) else 3)
                p_area = getattr(prop, 'area_sqm', None) or (prop.get('area_sqm') if isinstance(prop, dict) else 180)

                st.markdown(f"""
                    <div style="
                        background: #ffffff;
                        border: 1px solid #e8dec8;
                        border-radius: 16px;
                        padding: 20px 24px;
                        margin-bottom: 12px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        box-shadow: 0 6px 20px rgba(180, 150, 100, 0.06);
                    ">
                        <div>
                            <div style="font-size: 0.75rem; color: #8c7b65; margin-bottom: 4px; font-weight: 600;">رقم المعرف: #{p_id}</div>
                            <div style="font-size: 1.2rem; font-weight: 700; color: #2c2c2c; margin-bottom: 6px;">{p_title}</div>
                            <div style="color: #6c5d47; font-size: 0.9rem; margin-bottom: 8px;">الموقع: {p_location}</div>
                            <div style="font-size: 0.85rem; color: #6b7280; font-weight: 500;">
                                عدد الغرف: {p_bedrooms} &nbsp;&nbsp;|&nbsp;&nbsp; المساحة: {p_area} متر مربع
                            </div>
                        </div>
                        <div style="text-align: left;">
                            <div style="font-size: 1.25rem; font-weight: 800; color: #aa771c; margin-bottom: 10px;">EGP {p_price:,.0f}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                col_space, col_btn = st.columns([4, 1])
                with col_btn:
                    if st.button("معاينة ثلاثية الأبعاد", key=f"gb_p_{global_idx}", use_container_width=True):
                        with st.spinner("جاري تجهيز جولة المعاينة..."):
                            try:
                                current_state = the_Orchestrator.get_state(config)
                                has_active_interrupt = current_state.tasks and any(task.interrupts for task in current_state.tasks)
                                
                                if has_active_interrupt:
                                    exec_payload = Command(resume=p_id)
                                else:
                                    exec_payload = {
                                        "session_id": st.session_state.thread_id,
                                        "user_input_type": "text",
                                        "selected_property_id": p_id,
                                        "user_query": f"افرشلي الشقة دي من الرسمة {p_id}"
                                    }

                                for event in the_Orchestrator.stream(exec_payload, config=config):
                                    pass
                                st.rerun()
                            except Exception as ex:
                                st.error(f"❌ حدث خطأ: {ex}")

            if total_pages > 1:
                st.markdown("---")
                col_prev, col_info, col_next = st.columns([1, 2, 1], vertical_alignment="center")
                with col_prev:
                    if st.session_state.browse_page > 0:
                        if st.button("الصفحة السابقة", use_container_width=True):
                            st.session_state.browse_page -= 1
                            st.rerun()
                with col_info:
                    st.markdown(f"<p style='text-align: center; margin:0;'>صفحة <b>{st.session_state.browse_page + 1}</b> من <b>{total_pages}</b></p>", unsafe_allow_html=True)
                with col_next:
                    if st.session_state.browse_page < total_pages - 1:
                        if st.button("الصفحة التالية", use_container_width=True):
                            st.session_state.browse_page += 1
                            st.rerun()

    # ----------------------------------------------------
    # 4. الحالة الافتراضية (Home)
    # ----------------------------------------------------
    else:
        col1, col2 = st.columns([1, 6])
        with col1:
            st.markdown("#")
        with col2:
            st.title("Smart Semsar AI")
        
        st.markdown("""
        ### مرحبًا بك في منصة سمسار الذكية 🌟
        منصتك الذكية للبحث عن العقار المناسب ومعاينته تفاعلياً بتقنيات الـ 3D. 
        اكتب طلبك في القائمة الجانبية بالأسفل للبدء في رحلة البحث والعرض بكل سهولة واحترافية.
        """)
        st.markdown("---")