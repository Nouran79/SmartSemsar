# # [theme]
# # primaryColor = "#C9A227"
# # backgroundColor = "#F7F8FA"
# # secondaryBackgroundColor = "#FFFFFF"
# # textColor = "#172033"
# # font = "sans serif"


# # import streamlit as st
# # from langgraph.types import Command
# # import sys
# # import os
# # from dotenv import load_dotenv, find_dotenv


# # sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# # load_dotenv(find_dotenv())

# # st.set_page_config(page_title="Smart Semsar - AI Platform", page_icon="🏡")

# # st.title("🏡 Smart Semsar - AI Platform")

# # # 1. تحميل الجراف مرة واحدة فقط باستخدام الـ Caching لمنع البطء
# # @st.cache_resource
# # def load_orchestrator():
# #     from backend.agents.semsar_graph import the_Orchestrator
# #     return the_Orchestrator

# # try:
# #     the_Orchestrator = load_orchestrator()
# # except Exception as e:
# #     st.error(f"❌ خطأ في تحميل الجراف أو موديلات الباك إند: {e}")
# #     st.stop()

# # # إعداد الـ thread_id والـ chat history في الـ session state
# # if "thread_id" not in st.session_state:
# #     st.session_state.thread_id = "streamlit_user_session"

# # if "messages" not in st.session_state:
# #     st.session_state.messages = []

# # config = {"configurable": {"thread_id": st.session_state.thread_id}}

# # # عرض سجل المحادثة السابق
# # for message in st.session_state.messages:
# #     with st.chat_message(message["role"]):
# #         st.markdown(message["content"])

# # # --- التعامل مع عرض الـ Interrupts الحالية في بداية الصفحة (مثل أزرار اختيار العقارات) ---
# # current_state = the_Orchestrator.get_state(config)

# # if current_state.tasks and any(task.interrupts for task in current_state.tasks):
# #     interrupt_payload = current_state.tasks[0].interrupts[0].value
    
# #     # لو الـ interrupt خاص باختيار العقارات (يحتوي على dictionary و properties)
# #     if isinstance(interrupt_payload, dict) and interrupt_payload.get("type") == "property_selection":
# #         with st.chat_message("assistant"):
# #             st.markdown(interrupt_payload.get("message", "اختر العقار المناسب:"))
            
# #             props = interrupt_payload.get("properties", [])
# #             for idx, prop in enumerate(props):
# #                 with st.container():
# #                     # عرض تفاصيل العقار (مع دعم استخدام الـ attributes أو الـ dictionary keys بأمان)
# #                     p_title = getattr(prop, 'title', None) or (prop.get('title') if isinstance(prop, dict) else 'عقار')
# #                     p_price = getattr(prop, 'price', None) or (prop.get('price') if isinstance(prop, dict) else 0)
                    
# #                     # استخراج مسارات الصور أو الـ SVG بأمان للعقار المعروض
# #                     p_img = (
# #                         getattr(prop, 'image_path', None) or 
# #                         getattr(prop, 'plan_path', None) or 
# #                         (prop.get('image_path') if isinstance(prop, dict) else None)
# #                     )
                    
# #                     p_id = getattr(prop, 'property_id', None) or (prop.get('property_id') if isinstance(prop, dict) else idx)
                    
# #                     st.write(f"🏠 **{p_title}** - السعر: {p_price:,.0f} جنيه")
# #                     if p_img:
# #                         st.caption(f"📁 مسار الملف/الصورة: `{p_img}`")
                    
# #                     # زرار تفاعلي لاختيار العقار وإرسال الـ ID للجراف واستئناف التنفيذ
# #                     if st.button(f"اختر هذه الشقة (#{idx+1})", key=f"select_prop_{p_id}_{idx}"):
# #                         with st.spinner("جاري تأكيد اختيار العقار وتوليد الـ 3D Staging..."):
# #                             try:
# #                                 for event in the_Orchestrator.stream(Command(resume=p_id), config=config):
# #                                     pass
# #                                 st.rerun()
# #                             except Exception as ex:
# #                                 st.error(f"❌ حدث خطأ أثناء إرسال الاختيار: {ex}")

# # # --- عرض مخرجات الـ 3D Staging Node (لو تم الانتهاء منه) ---
# # graph_values = current_state.values if hasattr(current_state, "values") else {}
# # model_state = graph_values.get("model_state")

# # if model_state and getattr(model_state, "status", None) == "ready":
# #     st.success("🎉 تم توليد جولة الـ 3D و الـ Staging بنجاح!")
    
# #     walkthrough_path = getattr(model_state, "walkthrough_path", None)
# #     glb_path = getattr(model_state, "glb_path", None)
    
# #     # 1. عرض الـ 3D Walkthrough التفاعلي (HTML)
# #     if walkthrough_path and os.path.exists(walkthrough_path):
# #         st.markdown("### 🌐 معاينة الـ 3D Walkthrough التفاعلية:")
# #         try:
# #             with open(walkthrough_path, "r", encoding="utf-8") as f:
# #                 html_content = f.read()
# #             st.components.v1.html(html_content, height=600, scrolling=True)
# #         except Exception as e:
# #             st.error(f"❌ تعذر عرض ملف الـ Walkthrough: {e}")
            
# #     # 2. زرار تحميل ملف الـ GLB ثلاثي الأبعاد
# #     if glb_path and os.path.exists(glb_path):
# #         with open(glb_path, "rb") as file_to_download:
# #             st.download_button(
# #                 label="📥 تحميل نموذج الـ 3D (GLB)",
# #                 data=file_to_download,
# #                 file_name=os.path.basename(glb_path),
# #                 mime="model/gltf-binary"
# #             )

# # elif model_state and getattr(model_state, "status", None) == "failed":
# #     error_msg = getattr(model_state, "error", "Unknown error")
# #     st.error(f"❌ فشل توليد الـ 3D Staging: {error_msg}")

# # # استقبال إدخال اليوزر الجديد (للاستعلامات العادية أو التوجيه)
# # user_query = st.chat_input("اكتب طلبك هنا (مثلاً: عايز شقة في التجمع)...")

# # if user_query:
# #     # عرض وطباعة رسالة المستخدم
# #     st.chat_message("user").write(user_query)
# #     st.session_state.messages.append({"role": "user", "content": user_query})
    
# #     with st.spinner("جاري المعالجة..."):
# #         try:
# #             # التحقق هل الجراف واقف وبيستنى استئناف (Interrupt)؟
# #             current_state = the_Orchestrator.get_state(config)
            
# #             if current_state.tasks and any(task.interrupts for task in current_state.tasks):
# #                 execution_input = Command(resume=user_query)
# #             else:
# #                 execution_input = {
# #                     "session_id": st.session_state.thread_id,
# #                     "user_input_type": "text",
# #                     "user_query": user_query,
# #                     "user_text": user_query,
# #                 }

# #             # تشغيل الجراف
# #             for event in the_Orchestrator.stream(execution_input, config=config):
# #                 for node_name, output in event.items():
# #                     pass

# #             # التحقق من حالة الجراف بعد التنفيذ
# #             updated_state = the_Orchestrator.get_state(config)
            
# #             if updated_state.tasks and any(task.interrupts for task in updated_state.tasks):
# #                 interrupt_payload = updated_state.tasks[0].interrupts[0].value
                
# #                 # لو الـ interrupt الجديد مش أزرار عقارات، نعرضه كنص عادي
# #                 if not (isinstance(interrupt_payload, dict) and interrupt_payload.get("type") == "property_selection"):
# #                     interrupt_msg = str(interrupt_payload) if not isinstance(interrupt_payload, dict) else interrupt_payload.get("message", "")
# #                     with st.chat_message("assistant"):
# #                         st.markdown(interrupt_msg)
# #                     st.session_state.messages.append({"role": "assistant", "content": interrupt_msg})
# #                     st.rerun()
# #             else:
# #                 success_msg = "✅ تم الانتهاء من المعالجة بنجاح!"
# #                 with st.chat_message("assistant"):
# #                     st.markdown(success_msg)
# #                 st.session_state.messages.append({"role": "assistant", "content": success_msg})
                
# #         except Exception as e:
# #             error_msg = f"❌ حدث خطأ أثناء تشغيل الجراف: {e}"
# #             st.error(error_msg)
# #             st.session_state.messages.append({"role": "assistant", "content": error_msg})


# ################################################################################################################################################
# ################################################################################################################################################
# ################################################################################################################################################


# # import streamlit as st
# # import os
# # import base64

# # # استيراد المكونات والـ Views اللي عملناها
# # from frontend.components.chat_sidebar import render_chat_sidebar
# # from frontend.views.default_home import render_default_home

# # st.set_page_config(page_title="Smart Semsar - AI Platform", page_icon="🏡", layout="wide")

# # def get_base64_of_bin_file(bin_file):
# #     with open(bin_file, 'rb') as f:
# #         data = f.read()
# #     return base64.b64encode(data).decode()

# # if "splash_done" not in st.session_state:
# #     st.session_state.splash_done = False

# # # ==================== 1. صفحة الترحيب (Splash Screen) ====================
# # if not st.session_state.splash_done:
# #     image_path = "assets/SmartSemsarIntro.png"
    
# #     page_bg_img = ""
# #     if os.path.exists(image_path):
# #         bin_str = get_base64_of_bin_file(image_path)
# #         page_bg_img = f"data:image/png;base64,{bin_str}"

# #     st.markdown(f"""
# #         <style>
# #         header {{visibility: hidden;}}
# #         [data-testid="stSidebar"] {{display: none;}}
        
# #         .stApp {{
# #             background: linear-gradient(rgba(0,0,0,0.35), rgba(0,0,0,0.35)), url("{page_bg_img}");
# #             background-size: cover;
# #             background-position: center;
# #             background-repeat: no-repeat;
# #         }}

# #         .hero-container {{
# #             position: fixed;
# #             top: 45%;
# #             left: 50%;
# #             transform: translate(-50%, -50%);
# #             width: 100%;
# #             max-width: 900px;
# #             display: flex;
# #             flex-direction: column;
# #             align-items: center;
# #             justify-content: center;
# #             text-align: center;
# #             color: white;
# #             padding: 20px;
# #             z-index: 998;
# #         }}

# #         .hero-title {{
# #             font-size: 4rem;
# #             font-weight: 900;
# #             background: linear-gradient(to bottom, #ffffff, #ffffff, #ffffff);
# #             -webkit-background-clip: text;
# #             -webkit-text-fill-color: transparent;
# #             color: transparent;
# #             # text-shadow: 2px 2px 18px rgba(255, 255, 255, 0.7);
# #             margin-bottom: 12px;
# #             letter-spacing: 1.5px;
# #             animation: fadeIn 2s ease-in-out;
# #         }}

# #         .hero-subtitle {{
# #             font-size: 1.4rem;
# #             color: #ffffff;
# #             text-shadow: 1px 1px 6px rgba(0,0,0,0.9);
# #             margin-bottom: 35px;
# #             animation: fadeIn 2.5s ease-in-out;
# #         }}
        
# #         div.stButton > button {{
# #             background: linear-gradient(to right, #f1c40f, #e67e22) !important;
# #             color: white !important;
# #             font-size: 1.2rem !important;
# #             font-weight: 800 !important;
# #             border-radius: 50px !important;
# #             border: 2px solid #f1c40f !important;
# #             padding: 12px 45px !important;
# #             box-shadow: 0 4px 20px rgba(241, 196, 15, 0.7) !important;
# #             transition: all 0.3s ease-in-out !important;
# #             display: block !important;
# #             margin: 0 auto !important;
# #         }}
        
# #         div.stButton > button:hover {{
# #             background: linear-gradient(to right, #f39c12, #f1c40f) !important;
# #             transform: scale(1.08) !important;
# #             box-shadow: 0 6px 25px rgba(241, 196, 15, 0.9) !important;
# #         }}
# #         </style>
# #     """, unsafe_allow_html=True)

# #     st.markdown("""
# #         <div class="hero-container">
# #             <div class="hero-title">Smart Semsar</div>
# #             <div class="hero-subtitle">Match • Visualize • Design - رحلتك العقارية الذكية تبدأ هنا</div>
# #         </div>
# #     """, unsafe_allow_html=True)

# #     st.markdown('<div style="position: fixed; top: 70%; left: 50%; transform: translate(-50%, -50%); z-index: 999;">', unsafe_allow_html=True)
# #     if st.button("🚀 Start your Journey!"):
# #         st.session_state.splash_done = True
# #         st.rerun()
# #     st.markdown('</div>', unsafe_allow_html=True)

# # # ==================== 2. التطبيق الرئيسي بعد الدخول ====================
# # else:
# #     st.markdown("""
# #         <style>
# #         /* ضبط الصفحة الرئيسية لتكون من اليمين لليسار */
# #         .main .block-container {
# #             direction: rtl !important;
# #             text-align: right !important;
# #         }
        
# #         /* ضبط العناوين والنصوص لتكون محاذاة لليمين */
# #         h1, h2, h3, h4, h5, h6, p, div {
# #             text-align: right;
# #         }
# #         </style>
# #     """, unsafe_allow_html=True)
# #     # عرض الـ Sidebar الخاص بالشات في كل الصفحات الرئيسية
# #     render_chat_sidebar()
    
# #     # عرض الصفحة الرئيسية الافتتاحية (أو يتم تبديلها لاحقاً حسب الخطوة في البايبلاين)
# #     render_default_home()

# #################################################################################################################################################

# import streamlit as st
# from langgraph.types import Command
# import sys
# import os
# from dotenv import load_dotenv, find_dotenv

# # إضافة مسار جذر المشروع للـ sys.path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# load_dotenv(find_dotenv())

# st.set_page_config(page_title="Smart Semsar - AI Platform", page_icon="🏡", layout="centered")

# # --- 1. إدارة حالة التنقل (Splash Screen State) ---
# if "started_journey" not in st.session_state:
#     st.session_state.started_journey = False

# # --- 2. واجهة الـ Splash Screen (لو العميل لسه مابدأش) ---
# if not st.session_state.started_journey:
#     # تصميم CSS بسيط لترتيب الـ Splash Screen في منتصف الشاشة بشكل أنيق
#     st.markdown("""
#         <style>
#             .splash-container {
#                 display: flex;
#                 flex-direction: column;
#                 align-items: center;
#                 justify-content: center;
#                 height: 70vh;
#                 text-align: center;
#             }
#             .splash-title {
#                 font-size: 3rem;
#                 font-weight: 700;
#                 color: #FF4B4B;
#                 margin-bottom: 10px;
#             }
#             .splash-subtitle {
#                 font-size: 1.2rem;
#                 color: #666;
#                 margin-bottom: 30px;
#             }
#         </style>
#         <div class="splash-container">
#             <div class="splash-title">🏡 Smart Semsar</div>
#             <div class="splash-subtitle">منصتك الذكية لاكتشاف، معاينة، وتأثيث عقارك بالذكاء الاصطناعي</div>
#         </div>
#     """, unsafe_allow_html=True)

#     # زرار البداية في منتصف الصفحة بالضبط
#     col1, col2, col3 = st.columns([1, 2, 1])
#     with col2:
#         if st.button("🚀 ابدأ رحلتك معنا", use_container_width=True, type="primary"):
#             st.session_state.started_journey = True
#             st.rerun()

# # --- 3. صفحة الشات الأصلية (تظهر فور الضغط على ابدأ رحلتك) ---
# else:
#     st.title("🏡 Smart Semsar - AI Platform")

#     # 1. تحميل الجراف مرة واحدة فقط باستخدام الـ Caching لمنع البطء
#     @st.cache_resource
#     def load_orchestrator():
#         from backend.agents.semsar_graph import the_Orchestrator
#         return the_Orchestrator

#     try:
#         the_Orchestrator = load_orchestrator()
#     except Exception as e:
#         st.error(f"❌ خطأ في تحميل الجراف أو موديلات الباك إند: {e}")
#         st.stop()

#     # إعداد الـ thread_id والـ chat history في الـ session state
#     if "thread_id" not in st.session_state:
#         st.session_state.thread_id = "streamlit_user_session"

#     if "messages" not in st.session_state:
#         st.session_state.messages = []

#     config = {"configurable": {"thread_id": st.session_state.thread_id}}

#     # زرار للرجوع للـ Splash Screen (اختياري لو حابة تضيفيه كاختصار)
#     if st.sidebar.button("🏠 العودة للرئيسية"):
#         st.session_state.started_journey = False
#         st.rerun()

#     # عرض سجل المحادثة السابق
#     for message in st.session_state.messages:
#         with st.chat_message(message["role"]):
#             st.markdown(message["content"])

#     # --- التعامل مع عرض الـ Interrupts الحالية في بداية الصفحة (مثل أزرار اختيار العقارات) ---
#     current_state = the_Orchestrator.get_state(config)

#     if current_state.tasks and any(task.interrupts for task in current_state.tasks):
#         interrupt_payload = current_state.tasks[0].interrupts[0].value
        
#         # لو الـ interrupt خاص باختيار العقارات (يحتوي على dictionary و properties)
#         if isinstance(interrupt_payload, dict) and interrupt_payload.get("type") == "property_selection":
#             with st.chat_message("assistant"):
#                 st.markdown(interrupt_payload.get("message", "اختر العقار المناسب:"))
                
#                 props = interrupt_payload.get("properties", [])
#                 for idx, prop in enumerate(props):
#                     with st.container():
#                         p_title = getattr(prop, 'title', None) or (prop.get('title') if isinstance(prop, dict) else 'عقار')
#                         p_price = getattr(prop, 'price', None) or (prop.get('price') if isinstance(prop, dict) else 0)
                        
#                         p_img = (
#                             getattr(prop, 'image_path', None) or 
#                             getattr(prop, 'plan_path', None) or 
#                             (prop.get('image_path') if isinstance(prop, dict) else None)
#                         )
                        
#                         p_id = getattr(prop, 'property_id', None) or (prop.get('property_id') if isinstance(prop, dict) else idx)
                        
#                         st.write(f"🏠 **{p_title}** - السعر: {p_price:,.0f} جنيه")
#                         if p_img:
#                             st.caption(f"📁 مسار الملف/الصورة: `{p_img}`")
                        
#                         if st.button(f"اختر هذه الشقة (#{idx+1})", key=f"select_prop_{p_id}_{idx}"):
#                             with st.spinner("جاري تأكيد اختيار العقار وتوليد الـ 3D Staging..."):
#                                 try:
#                                     for event in the_Orchestrator.stream(Command(resume=p_id), config=config):
#                                         pass
#                                     st.rerun()
#                                 except Exception as ex:
#                                     st.error(f"❌ حدث خطأ أثناء إرسال الاختيار: {ex}")

#     # --- عرض مخرجات الـ 3D Staging Node (لو تم الانتهاء منه) ---
#     graph_values = current_state.values if hasattr(current_state, "values") else {}
#     model_state = graph_values.get("model_state")

#     if model_state and getattr(model_state, "status", None) == "ready":
#         st.success("🎉 تم توليد جولة الـ 3D و الـ Staging بنجاح!")
        
#         walkthrough_path = getattr(model_state, "walkthrough_path", None)
#         glb_path = getattr(model_state, "glb_path", None)
        
#         if walkthrough_path and os.path.exists(walkthrough_path):
#             st.markdown("### 🌐 معاينة الـ 3D Walkthrough التفاعلية:")
#             try:
#                 with open(walkthrough_path, "r", encoding="utf-8") as f:
#                     html_content = f.read()
#                 st.components.v1.html(html_content, height=600, scrolling=True)
#             except Exception as e:
#                 st.error(f"❌ تعذر عرض ملف الـ Walkthrough: {e}")
                
#         if glb_path and os.path.exists(glb_path):
#             with open(glb_path, "rb") as file_to_download:
#                 st.download_button(
#                     label="📥 تحميل نموذج الـ 3D (GLB)",
#                     data=file_to_download,
#                     file_name=os.path.basename(glb_path),
#                     mime="model/gltf-binary"
#                 )

#     elif model_state and getattr(model_state, "status", None) == "failed":
#         error_msg = getattr(model_state, "error", "Unknown error")
#         st.error(f"❌ فشل توليد الـ 3D Staging: {error_msg}")

#     # استقبال إدخال اليوزر الجديد
#     user_query = st.chat_input("اكتب طلبك هنا (مثلاً: عايز شقة في التجمع)...")

#     if user_query:
#         st.chat_message("user").write(user_query)
#         st.session_state.messages.append({"role": "user", "content": user_query})
        
#         with st.spinner("جاري المعالجة..."):
#             try:
#                 current_state = the_Orchestrator.get_state(config)
                
#                 if current_state.tasks and any(task.interrupts for task in current_state.tasks):
#                     execution_input = Command(resume=user_query)
#                 else:
#                     execution_input = {
#                         "session_id": st.session_state.thread_id,
#                         "user_input_type": "text",
#                         "user_query": user_query,
#                         "user_text": user_query,
#                     }

#                 for event in the_Orchestrator.stream(execution_input, config=config):
#                     for node_name, output in event.items():
#                         pass

#                 updated_state = the_Orchestrator.get_state(config)
                
#                 if updated_state.tasks and any(task.interrupts for task in updated_state.tasks):
#                     interrupt_payload = updated_state.tasks[0].interrupts[0].value
                    
#                     if not (isinstance(interrupt_payload, dict) and interrupt_payload.get("type") == "property_selection"):
#                         interrupt_msg = str(interrupt_payload) if not isinstance(interrupt_payload, dict) else interrupt_payload.get("message", "")
#                         with st.chat_message("assistant"):
#                             st.markdown(interrupt_msg)
#                         st.session_state.messages.append({"role": "assistant", "content": interrupt_msg})
#                         st.rerun()
#                 else:
#                     success_msg = "✅ تم الانتهاء من المعالجة بنجاح!"
#                     with st.chat_message("assistant"):
#                         st.markdown(success_msg)
#                     st.session_state.messages.append({"role": "assistant", "content": success_msg})
                    
#             except Exception as e:
#                 error_msg = f"❌ حدث خطأ أثناء تشغيل الجراف: {e}"
#                 st.error(error_msg)
#                 st.session_state.messages.append({"role": "assistant", "content": error_msg})

################################################################
# import streamlit as st
# from langgraph.types import Command
# import sys
# import os
# from dotenv import load_dotenv, find_dotenv

# # إضافة مسار جذر المشروع للـ sys.path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# load_dotenv(find_dotenv())

# st.set_page_config(page_title="Smart Semsar - AI Platform", page_icon="🏡", layout="centered")

# # --- 1. إدارة حالة التنقل (Splash Screen State) ---
# if "started_journey" not in st.session_state:
#     st.session_state.started_journey = False

# # --- 2. واجهة الـ Splash Screen (لو العميل لسه مابدأش) ---
# if not st.session_state.started_journey:
#     # تصميم CSS بسيط لترتيب الـ Splash Screen في منتصف الشاشة بشكل أنيق
#     st.markdown("""
#         <style>
#             .splash-container {
#                 display: flex;
#                 flex-direction: column;
#                 align-items: center;
#                 justify-content: center;
#                 height: 70vh;
#                 text-align: center;
#             }
#             .splash-title {
#                 font-size: 3rem;
#                 font-weight: 700;
#                 color: #FF4B4B;
#                 margin-bottom: 10px;
#             }
#             .splash-subtitle {
#                 font-size: 1.2rem;
#                 color: #666;
#                 margin-bottom: 30px;
#             }
#         </style>
#         <div class="splash-container">
#             <div class="splash-title">🏡 Smart Semsar</div>
#             <div class="splash-subtitle">منصتك الذكية لاكتشاف، معاينة، وتأثيث عقارك بالذكاء الاصطناعي</div>
#         </div>
#     """, unsafe_allow_html=True)

#     # زرار البداية في منتصف الصفحة بالضبط
#     col1, col2, col3 = st.columns([1, 2, 1])
#     with col2:
#         if st.button("🚀 ابدأ رحلتك معنا", use_container_width=True, type="primary"):
#             st.session_state.started_journey = True
#             st.rerun()

# # --- 3. صفحة الشات الأصلية (تظهر فور الضغط على ابدأ رحلتك) ---
# else:
#     st.title("🏡 Smart Semsar - AI Platform")

#     # 1. تحميل الجراف مرة واحدة فقط باستخدام الـ Caching لمنع البطء
#     @st.cache_resource
#     def load_orchestrator():
#         from backend.agents.semsar_graph import the_Orchestrator
#         return the_Orchestrator

#     try:
#         the_Orchestrator = load_orchestrator()
#     except Exception as e:
#         st.error(f"❌ خطأ في تحميل الجراف أو موديلات الباك إند: {e}")
#         st.stop()

#     # إعداد الـ thread_id والـ chat history في الـ session state
#     if "thread_id" not in st.session_state:
#         st.session_state.thread_id = "streamlit_user_session"

#     if "messages" not in st.session_state:
#         st.session_state.messages = []

#     config = {"configurable": {"thread_id": st.session_state.thread_id}}

#     # زرار للرجوع للـ Splash Screen (اختياري لو حابة تضيفيه كاختصار)
#     if st.sidebar.button("🏠 العودة للرئيسية"):
#         st.session_state.started_journey = False
#         st.rerun()

#     # عرض سجل المحادثة السابق
#     for message in st.session_state.messages:
#         with st.chat_message(message["role"]):
#             st.markdown(message["content"])

#     # --- التعامل مع عرض الـ Interrupts الحالية في بداية الصفحة (مثل أزرار اختيار العقارات) ---
#     current_state = the_Orchestrator.get_state(config)

#     if current_state.tasks and any(task.interrupts for task in current_state.tasks):
#         interrupt_payload = current_state.tasks[0].interrupts[0].value
        
#         # لو الـ interrupt خاص باختيار العقارات (يحتوي على dictionary و properties)
#         if isinstance(interrupt_payload, dict) and interrupt_payload.get("type") == "property_selection":
#             with st.chat_message("assistant"):
#                 st.markdown(interrupt_payload.get("message", "اختر العقار المناسب:"))
                
#                 props = interrupt_payload.get("properties", [])
#                 for idx, prop in enumerate(props):
#                     with st.container():
#                         p_title = getattr(prop, 'title', None) or (prop.get('title') if isinstance(prop, dict) else 'عقار')
#                         p_price = getattr(prop, 'price', None) or (prop.get('price') if isinstance(prop, dict) else 0)
                        
#                         p_img = (
#                             getattr(prop, 'image_path', None) or 
#                             getattr(prop, 'plan_path', None) or 
#                             (prop.get('image_path') if isinstance(prop, dict) else None)
#                         )
                        
#                         p_id = getattr(prop, 'property_id', None) or (prop.get('property_id') if isinstance(prop, dict) else idx)
                        
#                         st.write(f"🏠 **{p_title}** - السعر: {p_price:,.0f} جنيه")
#                         if p_img:
#                             st.caption(f"📁 مسار الملف/الصورة: `{p_img}`")
                        
#                         if st.button(f"اختر هذه الشقة (#{idx+1})", key=f"select_prop_{p_id}_{idx}"):
#                             with st.spinner("جاري تأكيد اختيار العقار وتوليد الـ 3D Staging..."):
#                                 try:
#                                     for event in the_Orchestrator.stream(Command(resume=p_id), config=config):
#                                         pass
#                                     st.rerun()
#                                 except Exception as ex:
#                                     st.error(f"❌ حدث خطأ أثناء إرسال الاختيار: {ex}")

#     # --- عرض مخرجات الـ 3D Staging Node (لو تم الانتهاء منه) ---
#     graph_values = current_state.values if hasattr(current_state, "values") else {}
#     model_state = graph_values.get("model_state")

#     if model_state and getattr(model_state, "status", None) == "ready":
#         st.success("🎉 تم توليد جولة الـ 3D و الـ Staging بنجاح!")
        
#         walkthrough_path = getattr(model_state, "walkthrough_path", None)
#         glb_path = getattr(model_state, "glb_path", None)
        
#         if walkthrough_path and os.path.exists(walkthrough_path):
#             st.markdown("### 🌐 معاينة الـ 3D Walkthrough التفاعلية:")
#             try:
#                 with open(walkthrough_path, "r", encoding="utf-8") as f:
#                     html_content = f.read()
#                 st.components.v1.html(html_content, height=600, scrolling=True)
#             except Exception as e:
#                 st.error(f"❌ تعذر عرض ملف الـ Walkthrough: {e}")
                
#         if glb_path and os.path.exists(glb_path):
#             with open(glb_path, "rb") as file_to_download:
#                 st.download_button(
#                     label="📥 تحميل نموذج الـ 3D (GLB)",
#                     data=file_to_download,
#                     file_name=os.path.basename(glb_path),
#                     mime="model/gltf-binary"
#                 )

#     elif model_state and getattr(model_state, "status", None) == "failed":
#         error_msg = getattr(model_state, "error", "Unknown error")
#         st.error(f"❌ فشل توليد الـ 3D Staging: {error_msg}")

#     # استقبال إدخال اليوزر الجديد
#     user_query = st.chat_input("اكتب طلبك هنا (مثلاً: عايز شقة في التجمع)...")

#     if user_query:
#         st.chat_message("user").write(user_query)
#         st.session_state.messages.append({"role": "user", "content": user_query})
        
#         with st.spinner("جاري المعالجة..."):
#             try:
#                 current_state = the_Orchestrator.get_state(config)
                
#                 if current_state.tasks and any(task.interrupts for task in current_state.tasks):
#                     execution_input = Command(resume=user_query)
#                 else:
#                     execution_input = {
#                         "session_id": st.session_state.thread_id,
#                         "user_input_type": "text",
#                         "user_query": user_query,
#                         "user_text": user_query,
#                     }

#                 for event in the_Orchestrator.stream(execution_input, config=config):
#                     for node_name, output in event.items():
#                         pass

#                 updated_state = the_Orchestrator.get_state(config)
                
#                 if updated_state.tasks and any(task.interrupts for task in updated_state.tasks):
#                     interrupt_payload = updated_state.tasks[0].interrupts[0].value
                    
#                     if not (isinstance(interrupt_payload, dict) and interrupt_payload.get("type") == "property_selection"):
#                         interrupt_msg = str(interrupt_payload) if not isinstance(interrupt_payload, dict) else interrupt_payload.get("message", "")
#                         with st.chat_message("assistant"):
#                             st.markdown(interrupt_msg)
#                         st.session_state.messages.append({"role": "assistant", "content": interrupt_msg})
#                         st.rerun()
#                 else:
#                     success_msg = "✅ تم الانتهاء من المعالجة بنجاح!"
#                     with st.chat_message("assistant"):
#                         st.markdown(success_msg)
#                     st.session_state.messages.append({"role": "assistant", "content": success_msg})
                    
#             except Exception as e:
#                 error_msg = f"❌ حدث خطأ أثناء تشغيل الجراف: {e}"
#                 st.error(error_msg)
#                 st.session_state.messages.append({"role": "assistant", "content": error_msg})



import streamlit as st
import sys
import os

# 1. إعداد الصفحة في أول سطر خالص
st.set_page_config(page_title="Smart Semsar - AI Platform", page_icon="🏡", layout="centered")

# إضافة مسار جذر المشروع للـ sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 2. إدارة حالة التنقل
if "started_journey" not in st.session_state:
    st.session_state.started_journey = False

# 3. التوجيه الشرطي الصارم (لو مشغلتش الرحلة اعرض الـ Splash، لو اشتغلت ادخل على الـ Home/Chat مباشرة)
if not st.session_state.started_journey:
    from views.splash_screen import render_splash
    render_splash()
else:
    from views.chat_view import render_chat_flow
    render_chat_flow()