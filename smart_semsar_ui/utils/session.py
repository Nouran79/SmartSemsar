import streamlit as st


def initialize_session_state() -> None:
    defaults = {
        "current_page": "Dashboard",
        "uploaded_audio_name": None,
        "audio_demo_result": None,
        "customer_profile": {
            "name": "Ahmed Mohamed",
            "phone": "+20 100 123 4567",
            "budget": 5_000_000,
            "location": "New Cairo",
            "property_type": "Apartment",
            "bedrooms": 3,
            "area_sqm": 150,
            "purpose": "Family Living",
            "finishing": "Fully Finished",
            "payment_plan": "Installments",
            "telegram_chat_id": None,
            "telegram_username": None,
        },
        "properties": None,
        "selected_property_id": "PROP-001",
        "favorite_property_ids": [],
        "booking_data": {},
        "staging_preferences": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, (dict, list)) else value


def get_session_telegram_link(customer_id: str = "customer", force_new: bool = False) -> dict:
    """Retrieve or generate the active Telegram linking token for the current user session."""
    from services.telegram_service import generate_linking_token, get_linking_token_info

    current = st.session_state.get("active_tg_link_info")
    if force_new or not current or not get_linking_token_info(current.get("token", "")):
        current = generate_linking_token(customer_id=customer_id)
        st.session_state["active_tg_link_info"] = current
    return current
