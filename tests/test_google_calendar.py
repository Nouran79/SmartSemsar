import datetime
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from googleapiclient.errors import HttpError
from httplib2 import Response

# Ensure smart_semsar_ui is in sys.path
UI_PATH = Path(__file__).parent.parent / "smart_semsar_ui"
if str(UI_PATH) not in sys.path:
    sys.path.insert(0, str(UI_PATH))

from services.google_calendar_service import (
    authorize_google_calendar,
    build_event_data,
    create_viewing_event,
    get_upcoming_events,
    is_google_calendar_authenticated,
    is_google_calendar_configured,
)
from services.property_service import get_properties
from streamlit.testing.v1 import AppTest



SAMPLE_PROPERTY = {
    "id": "PROP-001",
    "title": "Modern Apartment in New Cairo",
    "location": "New Cairo",
    "price": 4_800_000,
    "bedrooms": 3,
    "area_sqm": 155,
    "property_type": "Apartment",
    "finishing": "Fully Finished",
}


def test_build_event_data_structure():
    """Verify event payload structure conforms to Google Calendar API requirements."""
    payload = build_event_data(
        property_info=SAMPLE_PROPERTY,
        customer_name="Sherif Hassan",
        customer_phone="+20 100 555 7788",
        appointment_date="2026-11-15",
        appointment_time="14:00",
        notes="Customer wants to inspect balcony view.",
        duration_minutes=60,
        timezone="Africa/Cairo",
    )

    assert "Property Viewing: Modern Apartment in New Cairo (PROP-001) - Sherif Hassan" == payload["summary"]
    assert payload["location"] == "New Cairo"
    assert payload["start"]["dateTime"] == "2026-11-15T14:00:00"
    assert payload["start"]["timeZone"] == "Africa/Cairo"
    assert payload["end"]["dateTime"] == "2026-11-15T15:00:00"
    assert payload["end"]["timeZone"] == "Africa/Cairo"

    # Verify description content
    desc = payload["description"]
    assert "Sherif Hassan" in desc
    assert "+20 100 555 7788" in desc
    assert "PROP-001" in desc
    assert "4,800,000" in desc
    assert "Customer wants to inspect balcony view." in desc

    # Verify extended properties
    priv = payload["extendedProperties"]["private"]
    assert priv["property_id"] == "PROP-001"
    assert priv["customer_name"] == "Sherif Hassan"
    assert priv["customer_phone"] == "+20 100 555 7788"
    assert priv["source"] == "SmartSemsar"

    # Verify reminders
    assert payload["reminders"]["useDefault"] is False
    assert len(payload["reminders"]["overrides"]) == 2


def test_build_event_data_datetime_variations():
    """Verify handling of datetime.date objects, custom duration, and timezone."""
    d = datetime.date(2026, 12, 1)
    payload = build_event_data(
        property_info=SAMPLE_PROPERTY,
        customer_name="Mona Zaki",
        customer_phone="+20 111 222 3333",
        appointment_date=d,
        appointment_time="10:30",
        duration_minutes=90,
        timezone="Asia/Riyadh",
    )

    assert payload["start"]["dateTime"] == "2026-12-01T10:30:00"
    assert payload["start"]["timeZone"] == "Asia/Riyadh"
    assert payload["end"]["dateTime"] == "2026-12-01T12:00:00"
    assert payload["end"]["timeZone"] == "Asia/Riyadh"


def test_create_viewing_event_success_mock():
    """Verify create_viewing_event with a mocked Google Calendar API service."""
    mock_service = MagicMock()
    mock_insert = MagicMock()
    mock_service.events().insert.return_value = mock_insert
    mock_insert.execute.return_value = {
        "id": "evt_123456789",
        "htmlLink": "https://www.google.com/calendar/event?eid=mock_eid",
        "summary": "Property Viewing: Modern Apartment in New Cairo (PROP-001) - Sherif Hassan",
        "status": "confirmed",
    }

    result = create_viewing_event(
        property_info=SAMPLE_PROPERTY,
        customer_name="Sherif Hassan",
        customer_phone="+20 100 555 7788",
        appointment_date="2026-11-15",
        appointment_time="14:00",
        notes="Test note",
        calendar_id="primary",
        service=mock_service,
    )

    assert result["success"] is True
    assert result["event_id"] == "evt_123456789"
    assert result["html_link"] == "https://www.google.com/calendar/event?eid=mock_eid"
    mock_service.events().insert.assert_called_once()
    call_args = mock_service.events().insert.call_args[1]
    assert call_args["calendarId"] == "primary"
    assert call_args["body"]["summary"].startswith("Property Viewing:")


def test_create_viewing_event_http_error_handling():
    """Verify graceful handling when Google API returns an HTTP error."""
    mock_service = MagicMock()
    mock_insert = MagicMock()
    mock_service.events().insert.return_value = mock_insert

    # Simulate Google API HTTP 403 Forbidden
    resp = Response({"status": "403", "reason": "Forbidden"})
    mock_insert.execute.side_effect = HttpError(resp, b'{"error": {"message": "Calendar quota exceeded"}}')

    result = create_viewing_event(
        property_info=SAMPLE_PROPERTY,
        customer_name="Sherif Hassan",
        customer_phone="+20 100 555 7788",
        appointment_date="2026-11-15",
        appointment_time="14:00",
        service=mock_service,
    )

    assert result["success"] is False
    assert "Google Calendar API HTTP 403" in result["error"]


def test_create_viewing_event_unauthenticated_error():
    """Verify graceful error when credentials are not available."""
    with patch("services.google_calendar_service.get_credentials", return_value=None):
        result = create_viewing_event(
            property_info=SAMPLE_PROPERTY,
            customer_name="Sherif Hassan",
            customer_phone="+20 100 555 7788",
            appointment_date="2026-11-15",
            appointment_time="14:00",
        )
        assert result["success"] is False
        assert "Authentication error" in result["error"]


def test_get_upcoming_events_mock():
    """Verify fetching and parsing upcoming events with a mocked Google Calendar service."""
    mock_service = MagicMock()
    mock_list = MagicMock()
    mock_service.events().list.return_value = mock_list
    mock_list.execute.return_value = {
        "items": [
            {
                "id": "evt_abc1",
                "summary": "Property Viewing: Modern Apartment in New Cairo (PROP-001) - Tamer",
                "start": {"dateTime": "2026-11-20T10:00:00+02:00"},
                "end": {"dateTime": "2026-11-20T11:00:00+02:00"},
                "location": "New Cairo",
                "htmlLink": "https://calendar.google.com/event?eid=abc1",
                "extendedProperties": {
                    "private": {
                        "property_id": "PROP-001",
                        "customer_name": "Tamer",
                        "customer_phone": "+20 101 000 1111",
                    }
                },
            }
        ]
    }

    result = get_upcoming_events(max_results=5, service=mock_service)
    assert result["success"] is True
    assert len(result["events"]) == 1
    event = result["events"][0]
    assert event["id"] == "evt_abc1"
    assert event["property_id"] == "PROP-001"
    assert event["customer_name"] == "Tamer"
    assert event["customer_phone"] == "+20 101 000 1111"
    assert event["start"] == "2026-11-20T10:00:00+02:00"


def test_get_upcoming_events_http_error():
    """Verify error handling when listing events fails."""
    mock_service = MagicMock()
    mock_list = MagicMock()
    mock_service.events().list.return_value = mock_list
    resp = Response({"status": "500", "reason": "Internal Server Error"})
    mock_list.execute.side_effect = HttpError(resp, b"Server Error")

    result = get_upcoming_events(service=mock_service)
    assert result["success"] is False
    assert result["events"] == []
    assert "Google Calendar API HTTP 500" in result["error"]


def test_is_google_calendar_configured_logic():
    """Verify detection logic for credentials and token existence."""
    with patch("services.google_calendar_service.get_token_path") as mock_token, \
         patch("services.google_calendar_service.get_credentials_path") as mock_creds, \
         patch.dict("os.environ", {}, clear=True):

        mock_token.return_value.exists.return_value = False
        mock_creds.return_value.exists.return_value = False

        configured, msg = is_google_calendar_configured()
        assert configured is False
        assert "not found" in msg

        # When credentials file exists
        mock_creds.return_value.exists.return_value = True
        mock_creds.return_value.name = "credentials.json"
        configured, msg = is_google_calendar_configured()
        assert configured is True
        assert "Credentials file found" in msg


def test_is_google_calendar_authenticated_logic():
    """Verify is_google_calendar_authenticated detects valid tokens vs missing tokens."""
    with patch("services.google_calendar_service.get_token_path") as mock_token, \
         patch("services.google_calendar_service.get_credentials") as mock_get_creds, \
         patch.dict("os.environ", {}, clear=True):

        # When token file does not exist and no env refresh token
        mock_token.return_value.exists.return_value = False
        assert is_google_calendar_authenticated() is False

        # When token file exists and creds are valid
        mock_token.return_value.exists.return_value = True
        mock_cred_obj = MagicMock()
        mock_cred_obj.valid = True
        mock_get_creds.return_value = mock_cred_obj
        assert is_google_calendar_authenticated() is True

        # When creds exist but are invalid
        mock_cred_obj.valid = False
        assert is_google_calendar_authenticated() is False


def test_authorize_google_calendar_interactive_mock():
    """Verify authorize_google_calendar runs local server flow and writes token."""
    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.to_json.return_value = '{"token": "mock_token"}'

    with patch("services.google_calendar_service.get_token_path") as mock_token, \
         patch("services.google_calendar_service.get_credentials_path") as mock_creds_path, \
         patch("services.google_calendar_service.InstalledAppFlow") as mock_flow_cls:

        mock_token.return_value.exists.return_value = False
        mock_token.return_value.name = "token.json"
        mock_creds_path.return_value.exists.return_value = True

        mock_flow = MagicMock()
        mock_flow_cls.from_client_secrets_file.return_value = mock_flow
        mock_flow.run_local_server.return_value = mock_creds

        success, msg = authorize_google_calendar(interactive=True)
        assert success is True
        assert "authorized successfully" in msg
        mock_flow.run_local_server.assert_called_once()
        mock_token.return_value.write_text.assert_called_once_with('{"token": "mock_token"}', encoding="utf-8")


def test_streamlit_booking_page_renders_and_submits_demo():
    """Verify Booking page renders and saves demo viewing request in session when unconfigured."""
    with patch("views.booking.is_google_calendar_authenticated", return_value=False), \
         patch("views.booking.is_google_calendar_configured", return_value=(False, "Mock unconfigured")):
        app_file = str(UI_PATH / "app.py")
        at = AppTest.from_file(app_file).run()

        # Navigate to Booking page
        at.session_state["current_page"] = "Booking"
        at.run()
        assert not at.exception

        # Selectbox for property selection
        prop_select = at.selectbox("booking_property_selection")
        assert prop_select is not None
        assert prop_select.value == "PROP-001"

        # Submit form
        at.button("booking_submit_btn").click().run()
        assert not at.exception

        # Check booking_data is populated in session state
        booking_data = at.session_state.get("booking_data", {})
        assert booking_data.get("property_id") == "PROP-001"
        assert booking_data.get("customer_name") == "Ahmed Mohamed"
        assert "Demo request saved in this session" in booking_data.get("status", "")


def test_streamlit_booking_page_authorize_button_flow():
    """Verify authorize button appears when credentials exist and triggers OAuth flow."""
    with patch("views.booking.is_google_calendar_configured", return_value=(True, "Mock configured")), \
         patch("views.booking.is_google_calendar_authenticated", return_value=False), \
         patch("views.booking.authorize_google_calendar", return_value=(True, "Authorized successfully!")) as mock_auth:
        app_file = str(UI_PATH / "app.py")
        at = AppTest.from_file(app_file).run()
        at.session_state["current_page"] = "Booking"
        at.run()

        # Button should be available in expander
        auth_buttons = [b for b in at.button if b.key == "btn_auth_gcal"]
        assert len(auth_buttons) == 1

        # Click authorize button
        at.button("btn_auth_gcal").click().run()
        assert not at.exception
        mock_auth.assert_called_once_with(interactive=True)


def test_streamlit_booking_page_with_mocked_google_calendar_success():
    """Verify Booking page creates real calendar appointment when Google Calendar is configured."""
    app_file = str(UI_PATH / "app.py")
    at = AppTest.from_file(app_file).run()
    at.session_state["current_page"] = "Booking"
    at.run()

    mock_event_result = {
        "success": True,
        "event_id": "mock_google_id_999",
        "html_link": "https://calendar.google.com/mock_link",
        "event": {"id": "mock_google_id_999"},
    }

    with patch("views.booking.is_google_calendar_configured", return_value=(True, "Mock configured")), \
         patch("views.booking.is_google_calendar_authenticated", return_value=True), \
         patch("views.booking.create_viewing_event", return_value=mock_event_result):

        # Submit the booking form
        at.button("booking_submit_btn").click().run()
        assert not at.exception

        booking_data = at.session_state.get("booking_data", {})
        assert booking_data.get("status") == "Confirmed on Google Calendar"
        assert booking_data.get("calendar_event_id") == "mock_google_id_999"
        assert booking_data.get("calendar_link") == "https://calendar.google.com/mock_link"

        # Check success message appears
        success_found = any("successfully created on Google Calendar" in s.value for s in at.success)
        assert success_found


def test_streamlit_booking_page_duplicate_prevention():
    """Verify duplicate submissions are prevented on repeated submissions."""
    app_file = str(UI_PATH / "app.py")
    at = AppTest.from_file(app_file).run()
    at.session_state["current_page"] = "Booking"
    at.run()

    mock_event_result = {
        "success": True,
        "event_id": "mock_dup_id",
        "html_link": "https://calendar.google.com/mock_dup",
        "event": {"id": "mock_dup_id"},
    }

    with patch("views.booking.is_google_calendar_configured", return_value=(True, "Mock configured")), \
         patch("views.booking.is_google_calendar_authenticated", return_value=True), \
         patch("views.booking.create_viewing_event", return_value=mock_event_result) as mock_create:

        # First submission
        at.button("booking_submit_btn").click().run()
        assert not at.exception
        assert mock_create.call_count == 1

        # Second submission (same parameters)
        at.button("booking_submit_btn").click().run()
        assert not at.exception

        # Ensure create_viewing_event was NOT called a second time
        assert mock_create.call_count == 1

        # Warning about duplicate should be displayed
        warning_found = any("already been submitted" in w.value for w in at.warning)
        assert warning_found


def test_streamlit_booking_page_google_calendar_failure_reporting():
    """Verify app reports failure and does NOT report success when Google API fails."""
    app_file = str(UI_PATH / "app.py")
    at = AppTest.from_file(app_file).run()
    at.session_state["current_page"] = "Booking"
    at.run()

    mock_fail_result = {
        "success": False,
        "error": "Google Calendar API HTTP 403: Rate Limit Exceeded",
    }

    with patch("views.booking.is_google_calendar_configured", return_value=(True, "Mock configured")), \
         patch("views.booking.is_google_calendar_authenticated", return_value=True), \
         patch("views.booking.create_viewing_event", return_value=mock_fail_result):

        at.button("booking_submit_btn").click().run()
        assert not at.exception

        # Success message must NOT be shown
        success_found = any("successfully created on Google Calendar" in s.value for s in at.success)
        assert not success_found

        # Error message must be shown
        error_found = any("Failed to create Google Calendar event" in e.value for e in at.error)
        assert error_found

        booking_data = at.session_state.get("booking_data", {})
        assert "Google Calendar failed" in booking_data.get("status", "")
