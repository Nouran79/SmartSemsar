"""
Deterministic plan validator (no LLM yet).
بيقارن المخطط (plan.json) ببيانات الإعلان: الغرف، الحمامات، المساحة، وعدد الأدوار مقابل نوع العقار.

    result = validate_plan(plan, listing_row)
    -> {approved, checks[], warnings[], source_warning}
If approved is False the agent should pick another listing.
"""
import re
from typing import Any, Mapping, Optional

from pydantic import BaseModel, Field

from backend.schema.plan import Plan

AREA_TOLERANCE = 0.10          # ±10% of the listing area
MAX_STRETCH = 1.25             # look-alike linear scale factor above this -> warning
MIN_STRETCH = 0.80

# أول كلمة تظهر في العنوان هي اللي بتحدد النوع
PROPERTY_TYPE_KEYWORDS = [
    ("duplex", r"duplex|دوبلكس"),
    ("penthouse", r"penthouse|بنتهاوس"),
    ("townhouse", r"town\s*house|twin\s*house|تاون|توين"),
    ("studio", r"studio|ستوديو|استوديو"),
    ("villa", r"villa|stand\s*alone|standalone|فيلا"),
    ("apartment", r"apartment|\bapart\b|\bapt\b|\bflat\b|ground floor|\broof\b|شقة|شقه"),
]

# allowed number of floors per type: (min, max); outside -> check fails
FLOORS_BY_TYPE = {
    "apartment": (1, 1), "studio": (1, 1), "penthouse": (1, 1),
    "duplex": (2, 2), "townhouse": (2, 4), "villa": (1, 4),
}


class Check(BaseModel):
    name: str
    passed: bool
    expected: Any = None
    actual: Any = None
    message: str = ""


class ValidationResult(BaseModel):
    approved: bool
    checks: list[Check] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_warning: str


def infer_property_type(title: Optional[str]) -> str:
    """'Duplex apartment for rent' -> 'duplex'; nothing found -> 'unknown'."""
    text = (title or "").lower()
    best, best_pos = "unknown", len(text) + 1
    for ptype, pattern in PROPERTY_TYPE_KEYWORDS:
        m = re.search(pattern, text)
        if m and m.start() < best_pos:
            best, best_pos = ptype, m.start()
    return best


def _get(listing: Mapping, *keys):
    for k in keys:
        v = listing.get(k) if hasattr(listing, "get") else None
        if v is not None and v == v:  # skip None / NaN
            return v
    return None


def validate_plan(plan: Plan, listing: Mapping, area_tolerance: float = AREA_TOLERANCE) -> dict:
    """listing: CSV row / dict with pf_bedrooms, pf_bathrooms, pf_area_sqm, title (or property_type)."""
    checks: list[Check] = []
    warnings: list[str] = []

    bedrooms = _get(listing, "pf_bedrooms", "bedrooms")
    bathrooms = _get(listing, "pf_bathrooms", "bathrooms")
    area = _get(listing, "pf_area_sqm", "area_sqm")
    ptype = _get(listing, "property_type") or infer_property_type(_get(listing, "title"))

    # 1) bedrooms / bathrooms
    for name, expected, room_type in (("bedrooms", bedrooms, "bedroom"), ("bathrooms", bathrooms, "bathroom")):
        actual = plan.count(room_type)
        if expected is None:
            warnings.append(f"Listing has no {name} value; check skipped.")
            continue
        ok = actual == int(expected)
        checks.append(Check(name=name, passed=ok, expected=int(expected), actual=actual,
                            message="" if ok else f"Plan has {actual} {name}, listing says {int(expected)}."))

    # 2) total area
    if area:
        diff = abs(plan.total_area_sqm - float(area)) / float(area)
        ok = diff <= area_tolerance
        checks.append(Check(name="total_area", passed=ok, expected=float(area), actual=plan.total_area_sqm,
                            message=f"{diff:.0%} difference (tolerance {area_tolerance:.0%})."))
    else:
        warnings.append("Listing has no area value; area check skipped.")

    # 3) floors vs property type
    floors = plan.num_floors
    if ptype in FLOORS_BY_TYPE:
        lo, hi = FLOORS_BY_TYPE[ptype]
        ok = lo <= floors <= hi
        checks.append(Check(name="floors_vs_type", passed=ok, expected=[lo, hi], actual=floors,
                            message=f"{ptype} with {floors} floor(s)."))
        if ok and ptype == "villa" and floors == 1:
            warnings.append("Single-floor villa layout; most villas have 2+ floors.")
    else:
        warnings.append("Property type could not be determined; floors check skipped.")
        if floors > 1:
            warnings.append(f"Plan has {floors} floors; most listings are single-floor apartments.")

    # 4) look-alike stretch: big factors mean doors/walls/rooms are distorted
    if plan.source == "cubicasa_lookalike" and plan.scale.method == "fit_listing_area":
        k = plan.scale.factor
        if not (MIN_STRETCH <= k <= MAX_STRETCH):
            warnings.append(f"Layout was scaled x{k:.2f} in each direction to match the listing area; "
                            f"room proportions, door and wall sizes are approximate.")

    if plan.source == "generated":
        warnings.append("Plan is AI-generated; it is not based on any real floor plan.")

    result = ValidationResult(approved=all(c.passed for c in checks), checks=checks,
                              warnings=warnings, source_warning=plan.source_warning)
    return result.model_dump()
