"""input_node.py: LangGraph node that turns the customer's input
(recorded call and/or free text) into structured requirements.

Reads from state:
    audio_path : str | None   path to a recorded call
    user_text  : str | None   free text (Arabic or English)

Writes to state:
    conversation_text : str | None   speaker-labeled call transcript
    requirements      : dict | None  CustomerRequirements as a dict
    missing_fields    : list[str]
    error             : str | None
"""
from backend.services.user_input import audio_to_conversation
from backend.services.user_input_text import extract_requirements
from backend.schema.state import AgentState, PropertyItem
from typing import Optional, Literal, List, Dict, Any
from langgraph.types import interrupt


def input_node(state: AgentState) -> Dict[str, Any]:
    
    print("🔥 ANA HENNA EL-GADEED 🔥")  # سطر مميز جداً عشان نتأكد إنه شايف الملف
    print("Execute Input Node...")
    
    micro_intent = state.get("micro_intent")
    print(f"Current Micro Intent is: {micro_intent}")
    
    # لو البحث جديد، نجبره يقف هنا وما يكملش تحت
    if micro_intent in ["new_search", "modify_search"]:
        print("🔄 [RESET] Force resetting in input_node...")
        
        user_response = interrupt("تمام، هبدأ معاك بحث جديد. اكتب لي المواصفات الجديدة:")
        resumed_text = user_response.strip() if isinstance(user_response, str) else None
        
        req = extract_requirements(call_transcript=None, raw_text=resumed_text)
        
        return {
            "user_req_text": resumed_text,
            "user_query": resumed_text,
            "customer_reqs": req,
            "top_properties": [],
            "selected_property_id": None,
            "selected_property": None,
            "error_message": None
        }
    if (not state.get("customer_reqs") and not state.get("user_req_text")):
        user_response = interrupt("من فضلك، اكتب مواصفات الشقة المطلوبة (المنطقة، الميزانية، عدد الغرف):")
        
        # بعد الـ interrupt، يستأنف التنفيذ هنا
        resumed_text = user_response.strip() if isinstance(user_response, str) else None
        
        # نقوم بتحديث الـ raw_text مباشرة من النص المستأنف
        # لضمان أنه سيستخدم في بقية الكود أدناه
        raw_text = resumed_text
    else:
        # إذا لم يكن هناك interrupt، نحصل على الـ text العادي
        raw_text = (state.get("user_req_text") or "").strip() or None

    input_type = state.get("user_input_type", "text")
    audio_path = state.get("user_req_audio_path")
    # raw_text = (state.get("user_req_text") or "").strip() or None
    print("Input Node execution")

    conversation_text = audio_to_conversation(audio_path) if audio_path else None

    if not any([conversation_text, raw_text]):
        print("No inputss here")
        return {
            # "conversation_text": None,1
            "customer_reqs": None,
            # "missing_fields": [],
            "error": "Please provide at least one input: a recorded call or text.",
        }
    print(f"📥 Extracting requirements from Text: '{raw_text}' | Audio: {conversation_text is not None}")
    req = extract_requirements(call_transcript=conversation_text, raw_text=raw_text)
    print("Here is reqs heereeeee")

    return {
        "user_req_text": raw_text,
        "user_query": raw_text,
        "customer_reqs": req,
        "error_message": None
    }
