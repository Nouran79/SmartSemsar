import json
from typing import TypedDict, Optional, List, Dict, Any

class SketchState(TypedDict):
    user_id: str
    user_data: Dict[str, Any]      
    svg_code: Optional[str]         
    svg_file_path: Optional[str]    
    edit_instructions: Optional[str] 
    status: str                     