from typing import TypedDict, List, Optional, Dict, Any, Annotated
import operator
from pydantic import BaseModel, Field


class CustomerRequirements(BaseModel):
    location: Optional[str] = Field(default=None, description="Preferred Location")
    budget_min: Optional[float] = Field(default=None, description="Min budget in EGP")
    budget_max: Optional[float] = Field(default=None, description="Max budget in EGP")
    area_sqm: Optional[float] = Field(default=None, description="Area of property")
    bedrooms: Optional[int] = Field(default=None, description="Bedroom count")
    property_type: Optional[Literal["apartment", "villa", "duplex", "studio", "townhouse", "unknown"]] = Field(default="unknown", description="Type of property")
    purpose: Optional[Literal["living", "investment", "unknown"]] = Field(default="unknown", description="Purpose of Searching for Apartment")
    style_preference: Optional[str] = Field(default=None, description="Design style e.g., Modern, Classic")
    notes: Optional[str] = Field(default=None, description="Notes from customer inputs regards the property")
    
class PropertyItem(BaseModel):
    """Property details from the matching agent"""
    property_id: str
    title: str
    price: float
    location: str
    floorplan_2d_url: Optional[str] = None


def update_profile_reducer(old_profile: Optional[CustomerProfile], new_profile: Optional[CustomerProfile]) -> Optional[CustomerProfile]:
    """تحديث البروفايل جزئياً بدلاً من مسحه بالكامل عند إضافة معلومة جديدة"""
    if not old_profile:
        return new_profile
    if not new_profile:
        return old_profile
    
    # دمج البيانات القديمة والجديدة
    updated_data = old_profile.model_dump()
    new_data = new_profile.model_dump(exclude_unset=True)
    updated_data.update(new_data)
    
    return CustomerProfile(**updated_data)



class AgentState(TypedDict):
    # Inputs
    user_input_type: str                         # 'voice' | 'pdf' | 'text'
    raw_input_path_or_text: str

    # Profile (يتم دمجه تلقائياً لو تم تعديله في أكثر من Node)
    customer_profile: Annotated[Optional[CustomerProfile], update_profile_reducer]

    # Matching Results (القائمة هتلحق بها التنائج بدلاً من الإلغاء الكامل لو استخدمت operator.add)
    top_properties: Optional[List[PropertyItem]]
    selected_property: Optional[PropertyItem]

    # CV & 3D Staging
    render_3d_url: Optional[str]

    # Workflow Control & Errors
    error_message: Optional[str]
    next_step: Optional[str]