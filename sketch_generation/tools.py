import os
import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, Tuple

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

ARCHITECTURAL_DEFS = """
  <defs>
    <!-- Bed Symbol -->
    <g id="symbol_bed_double">
      <rect x="0" y="0" width="140" height="180" rx="6" fill="#f8fafc" stroke="#334155" stroke-width="2"/>
      <rect x="15" y="10" width="45" height="30" rx="4" fill="#cbd5e1" stroke="#64748b" stroke-width="1.5"/>
      <rect x="80" y="10" width="45" height="30" rx="4" fill="#cbd5e1" stroke="#64748b" stroke-width="1.5"/>
      <path d="M 10 70 L 130 70" stroke="#94a3b8" stroke-width="2" stroke-dasharray="4,4"/>
    </g>

    <!-- Door Swing Symbol (Right) -->
    <g id="symbol_door_swing">
      <line x1="0" y1="0" x2="0" y2="50" stroke="#1e293b" stroke-width="3"/>
      <path d="M 0 50 A 50 50 0 0 1 50 0" fill="none" stroke="#64748b" stroke-width="1.5" stroke-dasharray="3,3"/>
    </g>

    <!-- Dining Table with Chairs -->
    <g id="symbol_dining_table">
      <rect x="20" y="20" width="120" height="70" rx="5" fill="#f8fafc" stroke="#334155" stroke-width="2"/>
      <circle cx="50" cy="8" r="10" fill="#e2e8f0" stroke="#64748b" stroke-width="1.5"/>
      <circle cx="110" cy="8" r="10" fill="#e2e8f0" stroke="#64748b" stroke-width="1.5"/>
      <circle cx="50" cy="102" r="10" fill="#e2e8f0" stroke="#64748b" stroke-width="1.5"/>
      <circle cx="110" cy="102" r="10" fill="#e2e8f0" stroke="#64748b" stroke-width="1.5"/>
    </g>
  </defs>
"""

def validate_and_save_svg(user_id: str, svg_content: str, required_bedrooms: int = 1) -> Tuple[bool, str, str]:
    if not svg_content:
        return False, "Validation Failed: SVG is empty.", ""

    cleaned_svg = svg_content.strip()
    
    for prefix in ["```xml", "```svg", "```json", "```"]:
        if cleaned_svg.startswith(prefix):
            cleaned_svg = cleaned_svg[len(prefix):]
    if cleaned_svg.endswith("```"):
        cleaned_svg = cleaned_svg[:-3]
    cleaned_svg = cleaned_svg.strip(' "\'\n\r')

    start_idx = cleaned_svg.find("<svg")
    end_idx = cleaned_svg.rfind("</svg>")
    if start_idx != -1 and end_idx != -1:
        cleaned_svg = cleaned_svg[start_idx : end_idx + 6]
    else:
        return False, "Validation Failed: Valid <svg> tags not found.", ""

    if "<defs>" not in cleaned_svg:
        insert_pos = cleaned_svg.find(">") + 1
        cleaned_svg = cleaned_svg[:insert_pos] + ARCHITECTURAL_DEFS + cleaned_svg[insert_pos:]

    try:
        ET.fromstring(cleaned_svg)
    except ET.ParseError as e:
        return False, f"Validation Failed: Invalid XML syntax - {str(e)}", ""

    file_path = os.path.join(OUTPUT_DIR, f"{user_id}_layout.svg")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(cleaned_svg)

    return True, "SVG layout with full architectural symbology generated and saved.", file_path

def update_user_profile_json(user_id: str, updated_data: Dict[str, Any]) -> str:
    file_path = os.path.join(OUTPUT_DIR, f"{user_id}_profile.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=2)
    return file_path