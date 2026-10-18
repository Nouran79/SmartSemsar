# main.py
import os
import sys
import json
import argparse
from agent import create_sketch_graph, handle_user_modification

def load_input_json(file_path: str) -> tuple[str, dict]:
    """
    Reads a dynamic JSON file and extracts the user ID from the filename or contents.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file not found at: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # استخراج user_id من اسم الملف (مثلاً client_101.json -> client_101) أو من الحقول
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    user_id = data.get("user_id", base_name)
    
    return user_id, data

def run_pipeline(json_path: str, edit_instructions: str = None):
    # 1. قراءة الملف المرفوع ديناميكياً
    user_id, user_data = load_input_json(json_path)
    print(f" Loaded input data dynamically for User/File: {user_id}")

    graph = create_sketch_graph()

    # 2. فحص إذا كان المطلوب توليد جديد أم تعديل
    if edit_instructions:
        print(f" Applying Modification Request: {edit_instructions}")
        result = handle_user_modification(user_id=user_id, new_edit_prompt=edit_instructions, json_file_path=json_path)
        print(f" Updated SVG saved to: {result['svg_file_path']}")
        print(f" Updated Profile JSON saved to: output/{user_id}_profile.json")
    else:
        print(f" Generating Initial 2D SVG layout...")
        initial_state = {
            "user_id": user_id,
            "user_data": user_data,
            "svg_code": None,
            "svg_file_path": None,
            "edit_instructions": None,
            "status": "pending"
        }
        result = graph.invoke(initial_state)
        print(f" Initial SVG saved to: {result['svg_file_path']}")
        print(f" Profile JSON saved to: output/{user_id}_profile.json")

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dynamic 2D Sketch Generation from JSON")
    parser.add_argument("--file", "-f", type=str, default="input.json", help="Path to the input JSON file")
    parser.add_argument("--edit", "-e", type=str, default=None, help="Optional user modification prompt")
    
    args = parser.parse_args()
    
    # تشغيل الـ Pipeline بالملف الممرر
    run_pipeline(json_path=args.file, edit_instructions=args.edit)