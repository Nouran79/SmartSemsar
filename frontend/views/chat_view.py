import streamlit as st
from langgraph.types import Command
import os
from dotenv import load_dotenv, find_dotenv
import uuid

load_dotenv(find_dotenv())

def render_chat_flow():
    # --- تخصيص الـ CSS لترتيب السايدبار وثبات العناصر ---
    st.markdown("""
        <style>
            /* 1. اتجاه الصفحة من اليمين لليسار */
            html, body, [data-testid="stAppViewContainer"] {
                direction: rtl;
                text-align: right;
            }

            /* 2. تثبيت السايدبار على اليمين */
            section[data-testid="stSidebar"] > div:first-child {
                display: flex;
                flex-direction: column;
                height: 100vh;
                position: relative;
                padding-top: 4rem !important;
                padding-bottom: 0px !important;
                overflow: hidden !important;
            }

            /* 3. ضبط مساحة الصفحة الرئيسية على الشمال */
            div[data-testid="stAppViewContainer"] > section:nth-child(2) {
                margin-right: 21rem !important;
                margin-left: 0 !important;
            }

            /* 4. تصميم رسائل العميل */
            div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) {
                background-color: #FDFaf6 !important;
                border: 1px solid #F3EFEA !important;
                border-radius: 15px 15px 5px 15px !important;
                padding: 10px;
                margin-bottom: 2px;
            }

            /* 5. تصميم رسائل المساعد */
            div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) {
                background-color: #F0F4F8 !important;
                border: 1px solid #E1E8ED !important;
                border-radius: 15px 15px 15px 5px !important;
                padding: 10px;
                margin-bottom: 5px;
            }

            /* كارد عقاري فخم ومودرن بمقاس موحد */
            .property-card {
                background: #ffffff;
                border: 1px solid #eaeaea;
                border-radius: 16px;
                padding: 18px;
                margin-bottom: 15px;
                height: 220px;
                position: relative; /* عشان نقدر نثبت الزرار جواه بدقة */
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            .property-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.06);
            }
            .prop-title {
                font-size: 1.05rem;
                font-weight: 700;
                color: #1f2937;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                margin-bottom: 4px;
                max-width: 75%; /* عشان نسيب مساحة للزرار المربع فوق */
            }
            .prop-location {
                color: #6b7280;
                font-size: 0.85rem;
                margin-bottom: 8px;
            }
            .prop-price {
                font-size: 1.05rem;
                font-weight: 700;
                color: #008069;
            }
            /* تنسيق زرار 3D Design المربع الصغير جوه الكارد */
            .btn-3d-container {
                position: absolute;
                top: 15px;
                left: 15px; /* عشان يناسب الـ RTL (في الشمال فوق جوه الكارد) */
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

    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    # ==================== 📱 الـ SIDEBAR ====================
    with st.sidebar:
        col_title, col_btn = st.columns([3, 1], vertical_alignment="center")
        with col_title:
            st.markdown("### 💬 سمسار الذكي")
        with col_btn:
            if st.button("➕", help="بحث عقاري جديد", type="primary"):
                st.session_state.messages = []
                st.session_state.thread_id = str(uuid.uuid4())
                st.session_state.browse_page = 0
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

    # معالجة إرسال الرسالة من الشات
    if submit_button and user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
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
                    for node_name, output in event.items():
                        pass

                updated_state = the_Orchestrator.get_state(config)
                if updated_state.tasks and any(task.interrupts for task in updated_state.tasks):
                    interrupt_payload = updated_state.tasks[0].interrupts[0].value
                    if not (isinstance(interrupt_payload, dict) and interrupt_payload.get("type") in ["property_selection", "general_browse"]):
                        interrupt_msg = str(interrupt_payload) if not isinstance(interrupt_payload, dict) else interrupt_payload.get("message", "")
                        st.session_state.messages.append({"role": "assistant", "content": interrupt_msg})
                else:
                    st.session_state.messages.append({"role": "assistant", "content": "✅ تم تنفيذ الطلب بنجاح."})
                
                st.rerun()
            except Exception as ex:
                st.error(f"❌ حدث خطأ: {ex}")

    # دالة موحدة لاستخراج العقارات بأمان
    def extract_all_properties():
        if current_state.tasks and any(task.interrupts for task in current_state.tasks):
            int_val = current_state.tasks[0].interrupts[0].value
            if isinstance(int_val, dict) and int_val.get("properties"):
                return int_val.get("properties")

        from_graph = graph_values.get("top_properties") or graph_values.get("properties") or graph_values.get("filtered_properties")
        if from_graph:
            return from_graph

        try:
            from services.property_service import search_properties
            return search_properties("All locations", "All types", None, 0)
        except Exception:
            return []

    all_props = extract_all_properties()
    has_interrupt = current_state.tasks and any(task.interrupts for task in current_state.tasks)
    model_state = graph_values.get("model_state")

    # ----------------------------------------------------
    # 1. الأولوية القصوى: عرض الـ 3D Staging لو الجولة جاهزة
    # ----------------------------------------------------
    # ----------------------------------------------------
    # 1. الأولوية القصوى: عرض الـ 3D Staging لو الجولة جاهزة
    # ----------------------------------------------------
    if model_state and getattr(model_state, "status", None) == "ready":
        # st.success("🎉 تم توليد نموذج الـ 3D و Walkthrough بنجاح!")
        walkthrough_path = getattr(model_state, "walkthrough_path", None)
        glb_path = getattr(model_state, "glb_path", None)
        
        if walkthrough_path and os.path.exists(walkthrough_path):
            # st.markdown("### 🌐 المعاينة التفاعلية ثلاثية الأبعاد:")
            try:
                with open(walkthrough_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                st.components.v1.html(html_content, height=600, scrolling=True)
            except Exception as e:
                st.error(f"❌ تعذر العرض: {e}")
                
        if glb_path and os.path.exists(glb_path):
            with open(glb_path, "rb") as file_to_download:
                st.download_button(
                    label="📥 تحميل ملف الـ 3D (GLB)",
                    data=file_to_download,
                    file_name=os.path.basename(glb_path),
                    mime="model/gltf-binary"
                )

        st.markdown("---")
        
        # ==================== الأزرار الإضافية (تقرير + رجوع) ====================
        col_rep, col_back_prop = st.columns(2) #, col_back_browse
        
        with col_rep:
            if st.button("📊 إرسال/عرض التقرير", use_container_width=True, type="primary"):
                # هنا بنوجهه لصفحة التقرير أو بنسجل الحالة في الـ session_state
                st.session_state["current_page"] = "Report" # لو صاحبتك مسمياها كدة، أو بنعرض رسالة مؤقتة
                st.info("🚀 صفحة التقرير قيد التجهيز بواسطة زميلتك، ترقبها قريباً!")
                
        with col_back_prop:
            if st.button("⬅️ اختيار شقة أخرى", use_container_width=True):
                # بنصفر الـ model_state ونرجع حالة الـ macro_intent لـ property_selection عشان تظهر قائمة الشقق المقترحة تاني
                try:
                    the_Orchestrator.update_state(config, {
                        "model_state": None,
                        "macro_intent": "property_selection"
                    }, as_node="select_property")
                except Exception:
                    # لو الـ update_state طلبت اسم نود معين مش متاح، بنصفر الـ model_state ونعمل rerun مباشر
                    if "model_state" in graph_values:
                        graph_values["model_state"] = None
                st.rerun()
                
        # with col_back_browse:
        #     if st.button("🏠 العودة للتصفح العام", use_container_width=True):
        #         # مسح الـ thread أو إعادة تعيين الـ macro_intent لـ general_browse
        #         st.session_state.browse_page = 0
        #         # لو حابة نرجع للتصفح العام مباشرة
        #         try:
        #             for event in the_Orchestrator.stream(Command(resume="general_browse"), config=config):
        #                 pass
        #         except Exception:
        #             pass
        #         st.rerun()
    # ----------------------------------------------------
    # 2. حالة الـ Selection أو الـ Interrupt (اختيار شقة معينة)
    # ----------------------------------------------------
    elif has_interrupt or (macro_intent in ["property_selection", "recommendation", "search_by_reqs"]):
        st.markdown("### 🎯 العقارات المقترحة والمطابقة لطلبك:")
        
        if all_props:
            columns = st.columns(2)
            for idx, prop in enumerate(all_props):
                p_id = getattr(prop, 'property_id', None) or (prop.get('id') if isinstance(prop, dict) else (prop.get('property_id') if isinstance(prop, dict) else idx))
                p_title = getattr(prop, 'title', None) or (prop.get('title') if isinstance(prop, dict) else 'عقار فاخر')
                p_price = getattr(prop, 'price', None) or (prop.get('price') if isinstance(prop, dict) else 0)
                p_location = getattr(prop, 'location', None) or (prop.get('location') if isinstance(prop, dict) else 'مصر')
                p_bedrooms = getattr(prop, 'bedrooms', None) or (prop.get('bedrooms') if isinstance(prop, dict) else 3)
                p_area = getattr(prop, 'area_sqm', None) or (prop.get('area_sqm') if isinstance(prop, dict) else 180)

                with columns[idx % 2]:
                    # الكارد مع زرار 3D Design صغير جواه
                    st.markdown(f"""
                        <div class="property-card">
                            <div>
                                <div style="font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;">ID: #{p_id}</div>
                                <div class="prop-title" title="{p_title}">🏠 {p_title}</div>
                                <div class="prop-location">📍 {p_location}</div>
                            </div>
                            <div>
                                <div class="prop-price">EGP {p_price:,.0f}</div>
                                <div style="font-size: 0.8rem; color: #4b5563;">
                                    🛏️ {p_bedrooms} غرف &nbsp;&nbsp;·&nbsp;&nbsp; 📐 {p_area} م²
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    col_dummy, col_btn = st.columns([2, 1])
                    with col_btn:
                        if st.button("🧊 3D Design", key=f"sel_prop_{p_id}_{idx}", use_container_width=True):
                            with st.spinner("جاري معالجة الاختيار وتوليد نموذج الـ 3D..."):
                                try:
                                    for event in the_Orchestrator.stream(Command(resume=p_id), config=config):
                                        pass
                                    st.rerun()
                                except Exception as ex:
                                    st.error(f"❌ حدث خطأ: {ex}")
        else:
            st.warning("⚠️ لم يتم العثور على عقارات مطابقة حالياً.")

    # ----------------------------------------------------
    # 3. حالة الـ General Browse (تصفح جميع العقارات بالـ Pagination)
    # ----------------------------------------------------
    elif macro_intent == "general_browse":
        st.markdown("### 🌐 كافة العقارات المتاحة (General Browse):")
        if all_props:
            ITEMS_PER_PAGE = 12
            total_props = len(all_props)
            total_pages = (total_props + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if total_props > 0 else 1

            start_idx = st.session_state.browse_page * ITEMS_PER_PAGE
            end_idx = min(start_idx + ITEMS_PER_PAGE, total_props)
            current_page_props = all_props[start_idx:end_idx]

            columns = st.columns(4)
            for idx, prop in enumerate(current_page_props):
                global_idx = start_idx + idx
                p_id = getattr(prop, 'property_id', None) or (prop.get('id') if isinstance(prop, dict) else (prop.get('property_id') if isinstance(prop, dict) else global_idx))
                p_title = getattr(prop, 'title', None) or (prop.get('title') if isinstance(prop, dict) else 'عقار فاخر')
                p_price = getattr(prop, 'price', None) or (prop.get('price') if isinstance(prop, dict) else 0)
                p_location = getattr(prop, 'location', None) or (prop.get('location') if isinstance(prop, dict) else 'مصر')
                p_bedrooms = getattr(prop, 'bedrooms', None) or (prop.get('bedrooms') if isinstance(prop, dict) else 3)
                p_area = getattr(prop, 'area_sqm', None) or (prop.get('area_sqm') if isinstance(prop, dict) else 180)

                with columns[idx % 4]:
                    st.markdown(f"""
                        <div class="property-card">
                            <div>
                                <div style="font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;">ID: #{p_id}</div>
                                <div class="prop-title" title="{p_title}">🏠 {p_title}</div>
                                <div class="prop-location">📍 {p_location}</div>
                            </div>
                            <div>
                                <div class="prop-price">EGP {p_price:,.0f}</div>
                                <div style="font-size: 0.8rem; color: #4b5563;">
                                    🛏️ {p_bedrooms} غرف &nbsp;&nbsp;·&nbsp;&nbsp; 📐 {p_area} م²
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    col_dummy, col_btn = st.columns([2, 1])
                    with col_btn:
                        if st.button("🧊 3D Design", key=f"gb_p_{global_idx}", use_container_width=True):
                            with st.spinner("جاري تجهيز جولة الـ 3D Staging..."):
                                try:
                                    # لو الجراف واقف في interrupt نبعث resume، لو في التصفح العام نبعث رسالة اختيار للشقة
                                    current_state = the_Orchestrator.get_state(config)
                                    has_active_interrupt = current_state.tasks and any(task.interrupts for task in current_state.tasks)
                                    
                                    if has_active_interrupt:
                                        exec_payload = Command(resume=p_id)
                                    else:
                                        # لو في التصفح العام، بنبعث طلب اختيار هذه الشقة مباشرة للجراف
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
                        if st.button("➡️ الصفحة السابقة", use_container_width=True):
                            st.session_state.browse_page -= 1
                            st.rerun()
                with col_info:
                    st.markdown(f"<p style='text-align: center; margin:0;'>صفحة <b>{st.session_state.browse_page + 1}</b> من <b>{total_pages}</b></p>", unsafe_allow_html=True)
                with col_next:
                    if st.session_state.browse_page < total_pages - 1:
                        if st.button("الصفحة التالية ⬅️", use_container_width=True):
                            st.session_state.browse_page += 1
                            st.rerun()

    # ----------------------------------------------------
    # 4. الحالة الافتراضية (Home): الترحيب + أول 5 عقارات
    # ----------------------------------------------------
    else:
        col1, col2 = st.columns([1, 6])
        with col1:
            st.markdown("# 🏡")
        with col2:
            st.title("Smart Semsar AI")
        
        st.markdown("""
        ### مرحبًا بك في منصة سمسار الذكية 🌟
        منصتك الذكية للبحث عن العقار المناسب ومعاينته تفاعلياً بتقنيات الـ 3D. 
        اكتب طلبك في القائمة الجانبية أو تصفح عينة من العقارات المميزة أدناه:
        """)
        st.markdown("---")
        st.markdown("### 🔥 عقارات مميزة مقترحة لك:")

        home_props = all_props[:5] if all_props else []
        if home_props:
            columns = st.columns(2)
            for idx, prop in enumerate(home_props):
                p_id = getattr(prop, 'property_id', None) or (prop.get('id') if isinstance(prop, dict) else (prop.get('property_id') if isinstance(prop, dict) else idx))
                p_title = getattr(prop, 'title', None) or (prop.get('title') if isinstance(prop, dict) else 'عقار فاخر')
                p_price = getattr(prop, 'price', None) or (prop.get('price') if isinstance(prop, dict) else 0)
                p_location = getattr(prop, 'location', None) or (prop.get('location') if isinstance(prop, dict) else 'مصر')
                p_bedrooms = getattr(prop, 'bedrooms', None) or (prop.get('bedrooms') if isinstance(prop, dict) else 3)
                p_area = getattr(prop, 'area_sqm', None) or (prop.get('area_sqm') if isinstance(prop, dict) else 180)

                with columns[idx % 2]:
                    st.markdown(f"""
                        <div class="property-card">
                            <div>
                                <div style="font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;">ID: #{p_id}</div>
                                <div class="prop-title" title="{p_title}">🏠 {p_title}</div>
                                <div class="prop-location">📍 {p_location}</div>
                            </div>
                            <div>
                                <div class="prop-price">EGP {p_price:,.0f}</div>
                                <div style="font-size: 0.8rem; color: #4b5563;">
                                    🛏️ {p_bedrooms} غرف &nbsp;&nbsp;·&nbsp;&nbsp; 📐 {p_area} م²
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    col_dummy, col_btn = st.columns([2, 1])
                    with col_btn:
                        if st.button("🧊 3D Design", key=f"hm_p_{p_id}_{idx}", use_container_width=True):
                            with st.spinner("جاري تجهيز جولة الـ 3D Staging..."):
                                try:
                                    for event in the_Orchestrator.stream(Command(resume=p_id), config=config):
                                        pass
                                    st.rerun()
                                except Exception as ex:
                                    st.error(f"❌ حدث خطأ: {ex}")