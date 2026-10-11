# # import streamlit as st
# # from langgraph.types import Command
# # import sys
# # import os
# # from dotenv import load_dotenv, find_dotenv

# # # إضافة مسار جذر المشروع للـ sys.path
# # sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# # load_dotenv(find_dotenv())

# # st.set_page_config(page_title="Smart Semsar - AI Platform", page_icon="🏡")

# # st.title("🏡 Smart Semsar - AI Platform")

# # # 1. تحميل الجراف مرة واحدة فقط باستخدام الـ Caching لمنع البطء (التعديل الصح هنا بـ def)
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

# # # استقبال إدخال اليوزر الجديد
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
# #                 interrupt_msg = updated_state.tasks[0].interrupts[0].value
# #                 with st.chat_message("assistant"):
# #                     st.markdown(interrupt_msg)
# #                 st.session_state.messages.append({"role": "assistant", "content": interrupt_msg})
# #             else:
# #                 success_msg = "✅ تم استخراج الطلبات وتنفيذ البحث بنجاح!"
# #                 with st.chat_message("assistant"):
# #                     st.markdown(success_msg)
# #                 st.session_state.messages.append({"role": "assistant", "content": success_msg})
                
# #         except Exception as e:
# #             error_msg = f"❌ حدث خطأ أثناء تشغيل الجراف: {e}"
# #             st.error(error_msg)
# #             st.session_state.messages.append({"role": "assistant", "content": error_msg})

# import streamlit as st
# from langgraph.types import Command
# import sys
# import os
# from dotenv import load_dotenv, find_dotenv

# # إضافة مسار جذر المشروع للـ sys.path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# load_dotenv(find_dotenv())

# st.set_page_config(page_title="Smart Semsar - AI Platform", page_icon="🏡")

# st.title("🏡 Smart Semsar - AI Platform")

# # 1. تحميل الجراف مرة واحدة فقط باستخدام الـ Caching لمنع البطء
# @st.cache_resource
# def load_orchestrator():
#     from backend.agents.semsar_graph import the_Orchestrator
#     return the_Orchestrator

# try:
#     the_Orchestrator = load_orchestrator()
# except Exception as e:
#     st.error(f"❌ خطأ في تحميل الجراف أو موديلات الباك إند: {e}")
#     st.stop()

# # إعداد الـ thread_id والـ chat history في الـ session state
# if "thread_id" not in st.session_state:
#     st.session_state.thread_id = "streamlit_user_session"

# if "messages" not in st.session_state:
#     st.session_state.messages = []

# config = {"configurable": {"thread_id": st.session_state.thread_id}}

# # عرض سجل المحادثة السابق
# for message in st.session_state.messages:
#     with st.chat_message(message["role"]):
#         st.markdown(message["content"])

# # --- التعامل مع عرض الـ Interrupts الحالية (مثل الأزرار أو الرسائل المعلقة) ---
# current_state = the_Orchestrator.get_state(config)

# if current_state.tasks and any(task.interrupts for task in current_state.tasks):
#     interrupt_payload = current_state.tasks[0].interrupts[0].value
    
#     # لو الـ interrupt خاص باختيار العقارات (يحتوي على dictionary و properties)
#     if isinstance(interrupt_payload, dict) and interrupt_payload.get("type") == "property_selection":
#         with st.chat_message("assistant"):
#             st.markdown(interrupt_payload.get("message", "اختر العقار المناسب:"))
            
#             props = interrupt_payload.get("properties", [])
#             for idx, prop in enumerate(props):
#                 with st.container():
#                     # عرض تفاصيل العقار (مع دعم استخدام الـ attributes أو الـ dictionary keys بأمان)
#                     p_title = getattr(prop, 'title', None) or prop.get('title', 'عقار')
#                     p_price = getattr(prop, 'price', None) or prop.get('price', 0)
#                     p_id = getattr(prop, 'property_id', None) or prop.get('property_id', idx)
                    
#                     st.write(f"🏠 **{p_title}** - السعر: {p_price:,.0f} جنيه")
                    
#                     # زرار تفاعلي لاختيار العقار وإرسال الـ ID للجراف
#                     if st.button(f"اختر هذه الشقة (#{idx+1})", key=f"select_prop_{p_id}_{idx}"):
#                         with st.spinner("جاري تأكيد اختيار العقار..."):
#                             try:
#                                 for event in the_Orchestrator.stream(Command(resume=p_id), config=config):
#                                     pass
#                                 st.rerun()
#                             except Exception as ex:
#                                 st.error(f"❌ حدث خطأ أثناء إرسال الاختيار: {ex}")

# # استقبال إدخال اليوزر الجديد (لو مش في حالة انتظار اختيار عقار يتطلب أزرار، أو للاستعلامات العادية)
# user_query = st.chat_input("اكتب طلبك هنا (مثلاً: عايز شقة في التجمع)...")

# if user_query:
#     # عرض وطباعة رسالة المستخدم
#     st.chat_message("user").write(user_query)
#     st.session_state.messages.append({"role": "user", "content": user_query})
    
#     with st.spinner("جاري المعالجة..."):
#         try:
#             # التحقق هل الجراف واقف وبيستنى استئناف (Interrupt)؟
#             current_state = the_Orchestrator.get_state(config)
            
#             if current_state.tasks and any(task.interrupts for task in current_state.tasks):
#                 execution_input = Command(resume=user_query)
#             else:
#                 execution_input = {
#                     "session_id": st.session_state.thread_id,
#                     "user_input_type": "text",
#                     "user_query": user_query,
#                     "user_text": user_query,
#                 }

#             # تشغيل الجراف
#             for event in the_Orchestrator.stream(execution_input, config=config):
#                 for node_name, output in event.items():
#                     pass

#             # التحقق من حالة الجراف بعد التنفيذ
#             updated_state = the_Orchestrator.get_state(config)
            
#             if updated_state.tasks and any(task.interrupts for task in updated_state.tasks):
#                 interrupt_payload = updated_state.tasks[0].interrupts[0].value
                
#                 # لو الـ interrupt الجديد مش عبارة عن أزرار عقارات، نعرضه كنص عادي
#                 if not (isinstance(interrupt_payload, dict) and interrupt_payload.get("type") == "property_selection"):
#                     interrupt_msg = str(interrupt_payload) if not isinstance(interrupt_payload, dict) else interrupt_payload.get("message", "")
#                     with st.chat_message("assistant"):
#                         st.markdown(interrupt_msg)
#                     st.session_state.messages.append({"role": "assistant", "content": interrupt_msg})
#                     st.rerun()
#             else:
#                 success_msg = "✅ تم الانتهاء من المعالجة بنجاح!"
#                 with st.chat_message("assistant"):
#                     st.markdown(success_msg)
#                 st.session_state.messages.append({"role": "assistant", "content": success_msg})
                
#         except Exception as e:
#             error_msg = f"❌ حدث خطأ أثناء تشغيل الجراف: {e}"
#             st.error(error_msg)
#             st.session_state.messages.append({"role": "assistant", "content": error_msg})


import streamlit as st
from langgraph.types import Command
import sys
import os
from dotenv import load_dotenv, find_dotenv

# إضافة مسار جذر المشروع للـ sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv(find_dotenv())

st.set_page_config(page_title="Smart Semsar - AI Platform", page_icon="🏡")

st.title("🏡 Smart Semsar - AI Platform")

# 1. تحميل الجراف مرة واحدة فقط باستخدام الـ Caching لمنع البطء
@st.cache_resource
def load_orchestrator():
    from backend.agents.semsar_graph import the_Orchestrator
    return the_Orchestrator

try:
    the_Orchestrator = load_orchestrator()
except Exception as e:
    st.error(f"❌ خطأ في تحميل الجراف أو موديلات الباك إند: {e}")
    st.stop()

# إعداد الـ thread_id والـ chat history في الـ session state
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "streamlit_user_session"

if "messages" not in st.session_state:
    st.session_state.messages = []

config = {"configurable": {"thread_id": st.session_state.thread_id}}

# عرض سجل المحادثة السابق
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- التعامل مع عرض الـ Interrupts الحالية في بداية الصفحة (مثل أزرار اختيار العقارات) ---
current_state = the_Orchestrator.get_state(config)

if current_state.tasks and any(task.interrupts for task in current_state.tasks):
    interrupt_payload = current_state.tasks[0].interrupts[0].value
    
    # لو الـ interrupt خاص باختيار العقارات (يحتوي على dictionary و properties)
    if isinstance(interrupt_payload, dict) and interrupt_payload.get("type") == "property_selection":
        with st.chat_message("assistant"):
            st.markdown(interrupt_payload.get("message", "اختر العقار المناسب:"))
            
            props = interrupt_payload.get("properties", [])
            for idx, prop in enumerate(props):
                with st.container():
                    # عرض تفاصيل العقار (مع دعم استخدام الـ attributes أو الـ dictionary keys بأمان)
                    p_title = getattr(prop, 'title', None) or (prop.get('title') if isinstance(prop, dict) else 'عقار')
                    p_price = getattr(prop, 'price', None) or (prop.get('price') if isinstance(prop, dict) else 0)
                    p_id = getattr(prop, 'property_id', None) or (prop.get('property_id') if isinstance(prop, dict) else idx)
                    
                    st.write(f"🏠 **{p_title}** - السعر: {p_price:,.0f} جنيه")
                    
                    # زرار تفاعلي لاختيار العقار وإرسال الـ ID للجراف واستئناف التنفيذ
                    if st.button(f"اختر هذه الشقة (#{idx+1})", key=f"select_prop_{p_id}_{idx}"):
                        with st.spinner("جاري تأكيد اختيار العقار..."):
                            try:
                                for event in the_Orchestrator.stream(Command(resume=p_id), config=config):
                                    pass
                                st.rerun()
                            except Exception as ex:
                                st.error(f"❌ حدث خطأ أثناء إرسال الاختيار: {ex}")

# استقبال إدخال اليوزر الجديد (للاستعلامات العادية أو التوجيه)
user_query = st.chat_input("اكتب طلبك هنا (مثلاً: عايز شقة في التجمع)...")

if user_query:
    # عرض وطباعة رسالة المستخدم
    st.chat_message("user").write(user_query)
    st.session_state.messages.append({"role": "user", "content": user_query})
    
    with st.spinner("جاري المعالجة..."):
        try:
            # التحقق هل الجراف واقف وبيستنى استئناف (Interrupt)؟
            current_state = the_Orchestrator.get_state(config)
            
            if current_state.tasks and any(task.interrupts for task in current_state.tasks):
                execution_input = Command(resume=user_query)
            else:
                execution_input = {
                    "session_id": st.session_state.thread_id,
                    "user_input_type": "text",
                    "user_query": user_query,
                    "user_text": user_query,
                }

            # تشغيل الجراف
            for event in the_Orchestrator.stream(execution_input, config=config):
                for node_name, output in event.items():
                    pass

            # التحقق من حالة الجراف بعد التنفيذ
            updated_state = the_Orchestrator.get_state(config)
            
            if updated_state.tasks and any(task.interrupts for task in updated_state.tasks):
                interrupt_payload = updated_state.tasks[0].interrupts[0].value
                
                # لو الـ interrupt الجديد مش أزرار عقارات، نعرضه كنص عادي
                if not (isinstance(interrupt_payload, dict) and interrupt_payload.get("type") == "property_selection"):
                    interrupt_msg = str(interrupt_payload) if not isinstance(interrupt_payload, dict) else interrupt_payload.get("message", "")
                    with st.chat_message("assistant"):
                        st.markdown(interrupt_msg)
                    st.session_state.messages.append({"role": "assistant", "content": interrupt_msg})
                    st.rerun()
            else:
                success_msg = "✅ تم الانتهاء من المعالجة بنجاح!"
                with st.chat_message("assistant"):
                    st.markdown(success_msg)
                st.session_state.messages.append({"role": "assistant", "content": success_msg})
                
        except Exception as e:
            error_msg = f"❌ حدث خطأ أثناء تشغيل الجراف: {e}"
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
