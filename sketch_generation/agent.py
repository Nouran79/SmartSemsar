import re
import os
import json
import html
import warnings
from typing import Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

import config
from state import SketchState
from tools import validate_and_save_svg, update_user_profile_json
from prompts import SYSTEM_PROMPT

warnings.filterwarnings("ignore")

# إعداد الموديل
llm = ChatGoogleGenerativeAI(
    model="gemini-3.8-flash",
    google_api_key=config.GEMINI_API_KEY,
    temperature=0.2
)

def extract_svg_and_json(raw_text: str, default_data: dict) -> tuple[dict, str]:
    """
    استخراج موثوق للـ JSON والـ SVG مع فك تشفير أي Escape Characters.
    """
    updated_profile = default_data
    svg_code = ""

    # 1. إزالة كتل الـ Markdown المحيطة بالـ JSON إن وجدت
    cleaned_text = raw_text.strip()
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:]
    elif cleaned_text.startswith("```xml") or cleaned_text.startswith("```svg"):
        cleaned_text = cleaned_text[6:]
    elif cleaned_text.startswith("```"):
        cleaned_text = cleaned_text[3:]
    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3]
    cleaned_text = cleaned_text.strip()

    # 2. محاولة تحليل الـ JSON أولاً (وهو المصدر الأكثر دقة لكود الـ SVG الأصلي)
    try:
        parsed = json.loads(cleaned_text)
        if isinstance(parsed, dict):
            # استخراج بروفايل العميل
            if "updated_profile" in parsed:
                updated_profile = parsed["updated_profile"]
            elif "profile" in parsed:
                updated_profile = parsed["profile"]
            else:
                updated_profile = {k: v for k, v in parsed.items() if k not in ["svg_code", "svg", "layout_svg"]}

            # استخراج كود الـ SVG
            svg_code = parsed.get("svg_code") or parsed.get("svg") or parsed.get("layout_svg", "")
    except Exception:
        # في حال فشل تحليل الـ JSON، نبحث بالـ Regex
        pass

    # 3. Fallback: إذا لم نجد الـ SVG داخل JSON صالح، نستخرجه بالـ Regex
    if not svg_code:
        svg_match = re.search(r"(<svg[\s\S]*?</svg>)", cleaned_text, re.IGNORECASE)
        if svg_match:
            svg_code = svg_match.group(1).strip()

    # 4. تنظيف كود الـ SVG من أي slashes زائدة أو entities مكسورة
    if svg_code:
        # فك أي unicode escapes أو newlines متبقية
        svg_code = svg_code.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
        svg_code = svg_code.strip(' "\'\n\r')

    return updated_profile, svg_code


def generate_or_edit_sketch_node(state: SketchState) -> Dict[str, Any]:
    user_id = state.get("user_id", "default_user")
    user_data = state.get("user_data", {})
    edit_instructions = state.get("edit_instructions")
    current_svg = state.get("svg_code")

    if edit_instructions and current_svg:
        prompt_content = f"""
Existing Client Profile (JSON):
{json.dumps(user_data, indent=2)}

Existing Architectural SVG:
{current_svg}

User Revision Request:
{edit_instructions}

Update both the architectural SVG and the JSON profile according to the user request. Ensure all text and property values are in English.
"""
    else:
        prompt_content = f"""
Client Requirements (JSON):
{json.dumps(user_data, indent=2)}

Generate a complete 2D architectural SVG and an updated client profile. Ensure everything is in English.
"""

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt_content)
    ]

    response = llm.invoke(messages)
    
    # استخراج النص
    raw_content = response.content
    if isinstance(raw_content, list):
        response_text = "".join([str(p.get("text", p) if isinstance(p, dict) else p) for p in raw_content]).strip()
    else:
        response_text = str(raw_content).strip()

    # معالجة النتائج
    updated_profile, svg_code = extract_svg_and_json(response_text, user_data)

    # حفظ وتحقق من الـ SVG
    is_valid, msg, file_path = validate_and_save_svg(user_id, svg_code, required_bedrooms=1)
    print(f"[SVG Status] {msg}")

    # حفظ الـ JSON المحدث
    profile_path = update_user_profile_json(user_id, updated_profile)
    print(f"[Profile Status] Saved JSON profile to: {profile_path}")

    return {
        "user_id": user_id,
        "user_data": updated_profile,
        "svg_code": svg_code,
        "svg_file_path": file_path,
        "status": "approved" if not edit_instructions else "updated",
        "edit_instructions": None
    }


def create_sketch_graph():
    """
    بناء وتجميع الـ LangGraph Workflow.
    """
    workflow = StateGraph(SketchState)
    workflow.add_node("sketch_generator", generate_or_edit_sketch_node)
    workflow.set_entry_point("sketch_generator")
    workflow.add_edge("sketch_generator", END)
    return workflow.compile()


def handle_user_modification(user_id: str, new_edit_prompt: str, json_file_path: str = None) -> Dict[str, Any]:
    """
    قراءة الملف الحالي واستقبال تعديل المستخدم وإعادة توليد المخطط وتحديث البيانات.
    """
    if json_file_path is None:
        json_file_path = os.path.join("output", f"{user_id}_profile.json")

    with open(json_file_path, "r", encoding="utf-8") as f:
        current_user_data = json.load(f)

    svg_file_path = os.path.join("output", f"{user_id}_layout.svg")
    current_svg = ""
    if os.path.exists(svg_file_path):
        with open(svg_file_path, "r", encoding="utf-8") as f:
            current_svg = f.read()

    graph = create_sketch_graph()
    state_payload = {
        "user_id": user_id,
        "user_data": current_user_data,
        "svg_code": current_svg,
        "svg_file_path": svg_file_path,
        "edit_instructions": new_edit_prompt,
        "status": "modifying"
    }

    updated_state = graph.invoke(state_payload)
    return updated_state