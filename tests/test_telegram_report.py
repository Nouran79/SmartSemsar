import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from streamlit.testing.v1 import AppTest

# Ensure smart_semsar_ui is in sys.path
UI_PATH = Path(__file__).parent.parent / "smart_semsar_ui"
if str(UI_PATH) not in sys.path:
    sys.path.insert(0, str(UI_PATH))

from services.property_service import get_properties, get_property_by_id
from services.telegram_service import (
    _PENDING_LINKING_TOKENS,
    _sanitize_secret,
    fetch_telegram_bot_username,
    format_property_report,
    generate_linking_token,
    get_confirmed_booking_for_property,
    get_linking_token_info,
    get_telegram_bot_token,
    get_telegram_bot_username,
    get_telegram_webhook_info,
    is_confirmed_booking,
    is_telegram_configured,
    is_valid_public_url,
    send_property_report,
    send_telegram_message,
    verify_telegram_linking,
)


# --- Unit Tests: Configuration & Security ---


def test_is_telegram_configured_logic():
    """Verify configuration check responds correctly to presence/absence of token."""
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "123456:ABC-DEF"}, clear=False):
        configured, msg = is_telegram_configured()
        assert configured is True
        assert "configured" in msg.lower()

    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": ""}, clear=False):
        configured, msg = is_telegram_configured()
        assert configured is False
        assert "not configured" in msg.lower()


def test_get_telegram_bot_username():
    """Verify username resolution strips @ symbol and defaults to SmartSemsarBot."""
    with patch.dict(os.environ, {"TELEGRAM_BOT_USERNAME": "@MyCustomBot"}, clear=False):
        assert get_telegram_bot_username() == "MyCustomBot"

    with patch.dict(os.environ, {"TELEGRAM_BOT_USERNAME": "PlainBot"}, clear=False):
        assert get_telegram_bot_username() == "PlainBot"

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("TELEGRAM_BOT_USERNAME", None)
        assert get_telegram_bot_username() == "SmartSemsarBot"


def test_is_valid_public_url():
    """Verify only genuine public HTTP/HTTPS URLs are allowed, rejecting local files and localhost."""
    # Valid public URLs
    assert is_valid_public_url("https://smartsemsar.com/tours/prop-001") is True
    assert is_valid_public_url("http://cdn.example.com/floorplans/plan.png") is True

    # Invalid: local paths, file scheme, Windows drive letters, localhost
    assert is_valid_public_url("smartsemsar-plan-3d-files/out/PROP-001/walkthrough.html") is False
    assert is_valid_public_url("C:\\Users\\User\\Documents\\model.glb") is False
    assert is_valid_public_url("/data/cubicasa_svg/floorplan.svg") is False
    assert is_valid_public_url("file:///C:/Users/User/model.glb") is False
    assert is_valid_public_url("http://localhost:8501/view") is False
    assert is_valid_public_url("http://127.0.0.1:8000/tour") is False
    assert is_valid_public_url("") is False
    assert is_valid_public_url(None) is False


def test_format_property_report_zero_hallucination_urls():
    """Verify local filesystem paths are strictly excluded and never leaked in Telegram reports."""
    prop_with_local_and_public = {
        "id": "PROP-009",
        "title": "Test Villa",
        "location": "New Cairo",
        "price": 10_000_000,
        "bedrooms": 4,
        "area_sqm": 300,
        "finishing": "Finished",
        "public_3d_url": "https://smartsemsar.com/3d-walkthrough/PROP-009",
        "floor_plan_url": "data/cubicasa_svg/floorplan.svg",  # Local path: MUST BE OMITTED
        "image_url": "C:\\Users\\Admin\\images\\photo.png",  # Local path: MUST BE OMITTED
    }

    report = format_property_report(prop_with_local_and_public, format_type="html")

    # Valid public URL must be present
    assert "https://smartsemsar.com/3d-walkthrough/PROP-009" in report

    # Local paths MUST NOT be present
    assert "data/cubicasa_svg" not in report
    assert "C:\\Users" not in report
    assert "photo.png" not in report


def test_sanitize_secret_redacts_tokens():
    """Verify secrets are redacted from error strings."""
    secret = "SECRET_12345"
    raw_error = "Failed to connect to https://api.telegram.org/botSECRET_12345/sendMessage"
    sanitized = _sanitize_secret(raw_error, secret)
    assert secret not in sanitized
    assert "<REDACTED_BOT_TOKEN>" in sanitized


# --- Unit Tests: Booking Verification Logic ---


def test_is_confirmed_booking():
    """Verify confirmation checks require matching property, date, time, and confirmed status."""
    confirmed_cal = {
        "property_id": "PROP-001",
        "date": "2026-10-20",
        "time": "14:00",
        "status": "Confirmed on Google Calendar",
        "calendar_event_id": "event_12345",
    }
    assert is_confirmed_booking(confirmed_cal, "PROP-001") is True
    # Mismatched property ID
    assert is_confirmed_booking(confirmed_cal, "PROP-002") is False

    # Confirmed status without calendar_event_id
    manual_confirmed = {
        "property_id": "PROP-002",
        "date": "2026-10-21",
        "time": "11:00",
        "status": "Confirmed viewing appointment",
    }
    assert is_confirmed_booking(manual_confirmed, "PROP-002") is True

    # Unconfirmed demo / local save
    demo_booking = {
        "property_id": "PROP-001",
        "date": "2026-10-20",
        "time": "14:00",
        "status": "Demo request saved in this session (Google Calendar not configured)",
    }
    assert is_confirmed_booking(demo_booking, "PROP-001") is False

    # Failed calendar booking
    failed_booking = {
        "property_id": "PROP-001",
        "date": "2026-10-20",
        "time": "14:00",
        "status": "Saved locally (Google Calendar failed: HTTP 403)",
    }
    assert is_confirmed_booking(failed_booking, "PROP-001") is False

    # Incomplete booking
    missing_time = {"property_id": "PROP-001", "date": "2026-10-20", "status": "Confirmed"}
    assert is_confirmed_booking(missing_time, "PROP-001") is False
    assert is_confirmed_booking({}, "PROP-001") is False
    assert is_confirmed_booking(None, "PROP-001") is False


def test_get_confirmed_booking_for_property():
    """Verify fetching confirmed booking from active booking_data or history list."""
    history = [
        {
            "property_id": "PROP-001",
            "date": "2026-10-18",
            "time": "10:00",
            "status": "Confirmed on Google Calendar",
            "calendar_event_id": "evt_1",
        },
        {
            "property_id": "PROP-002",
            "date": "2026-10-19",
            "time": "12:00",
            "status": "Saved locally (Google Calendar failed)",
        },
    ]

    active_booking = {
        "property_id": "PROP-003",
        "date": "2026-10-22",
        "time": "16:00",
        "status": "Confirmed on Google Calendar",
        "calendar_event_id": "evt_3",
    }

    # Matches active booking
    found_3 = get_confirmed_booking_for_property("PROP-003", booking_data=active_booking, booking_history=history)
    assert found_3 is not None
    assert found_3["property_id"] == "PROP-003"

    # Matches history
    found_1 = get_confirmed_booking_for_property("PROP-001", booking_data=None, booking_history=history)
    assert found_1 is not None
    assert found_1["calendar_event_id"] == "evt_1"

    # PROP-002 is unconfirmed in history
    found_2 = get_confirmed_booking_for_property("PROP-002", booking_data=None, booking_history=history)
    assert found_2 is None

    # Unknown property
    found_none = get_confirmed_booking_for_property("PROP-999", booking_data=None, booking_history=history)
    assert found_none is None


# --- Unit Tests: Report Formatting (Scenario 1 & Scenario 2) ---


def test_format_property_report_scenario_1_without_booking():
    """Verify Scenario 1: Report includes property specs, installments, disclaimer, and NO booking section."""
    prop = get_property_by_id("PROP-001")
    assert prop is not None

    custom_plan = {
        "down_payment": 960_000.0,
        "down_payment_percent": 20.0,
        "remaining": 3_840_000.0,
        "total_interest": 0.0,
        "total_installments": 3_840_000.0,
        "monthly_installment": 64_000.0,
        "total_cost": 4_800_000.0,
        "years": 5,
        "annual_interest_rate": 0.0,
    }

    report = format_property_report(
        property_info=prop,
        customer_name="Ahmed Mohamed",
        installment_plan=custom_plan,
        booking_data=None,  # No booking
        format_type="html",
    )

    # Must contain greeting & property info
    assert "Ahmed Mohamed" in report
    assert "Modern Apartment in New Cairo" in report
    assert "PROP-001" in report
    assert "EGP 4,800,000" in report
    assert "3" in report  # bedrooms
    assert "155" in report  # area_sqm

    # Must contain installment plan details & assumptions
    assert "Down Payment:</b> EGP 960,000 (20%)" in report
    assert "Duration:</b> 5 years" in report
    assert "Monthly Installment:</b> EGP 64,000 / month" in report
    assert "0.0% flat annual rate" in report
    assert "actual developer payment plans may differ" in report

    # Scenario 1 MUST NOT contain any viewing appointment details
    assert "Confirmed Viewing Appointment" not in report
    assert "Viewing Appointment" not in report


def test_format_property_report_scenario_2_with_confirmed_booking():
    """Verify Scenario 2: When confirmed booking exists, verified appointment date & time are included."""
    prop = get_property_by_id("PROP-001")
    assert prop is not None

    confirmed_booking = {
        "property_id": "PROP-001",
        "date": "2026-10-25",
        "time": "14:00",
        "notes": "Customer interested in payment plans.",
        "status": "Confirmed on Google Calendar",
        "calendar_event_id": "gcal_evt_789",
        "calendar_link": "https://calendar.google.com/event?eid=gcal_evt_789",
    }

    report = format_property_report(
        property_info=prop,
        customer_name="Sara Ibrahim",
        booking_data=confirmed_booking,
        format_type="html",
    )

    assert "Sara Ibrahim" in report
    assert "Modern Apartment in New Cairo" in report

    # Scenario 2 MUST include the confirmed appointment details
    assert "Confirmed Viewing Appointment" in report
    assert "2026-10-25" in report
    assert "14:00" in report
    assert "Customer interested in payment plans." in report
    assert "https://calendar.google.com/event?eid=gcal_evt_789" in report


def test_format_property_report_scenario_2_ignores_mismatched_booking():
    """Verify that a confirmed booking for PROP-001 is NOT included when generating report for PROP-002."""
    prop2 = get_property_by_id("PROP-002")
    assert prop2 is not None

    confirmed_booking_prop1 = {
        "property_id": "PROP-001",
        "date": "2026-10-25",
        "time": "14:00",
        "status": "Confirmed on Google Calendar",
        "calendar_event_id": "gcal_evt_789",
    }

    report = format_property_report(
        property_info=prop2,
        customer_name="Sara Ibrahim",
        booking_data=confirmed_booking_prop1,
    )

    assert "Contemporary Apartment in Mostakbal City" in report
    assert "Confirmed Viewing Appointment" not in report


# --- Unit Tests: Account Linking Flow ---


def test_generate_linking_token():
    """Verify generation of secure one-time expiring linking code and deep link."""
    with patch.dict(os.environ, {"TELEGRAM_BOT_USERNAME": "SmartSemsarBot"}):
        res = generate_linking_token(customer_id="cust_1", ttl_seconds=300)
        assert res["token"].startswith("LINK_")
        assert f"https://t.me/SmartSemsarBot?start={res['token']}" == res["deep_link"]
        assert res["expires_in_seconds"] == 300
        assert res["token"] in _PENDING_LINKING_TOKENS


def test_verify_telegram_linking_success():
    """Verify linking succeeds when matching /start token is returned by Telegram getUpdates."""
    token_res = generate_linking_token(customer_id="test_user", ttl_seconds=600)
    token = token_res["token"]

    mock_updates_response = {
        "ok": True,
        "result": [
            {
                "update_id": 1001,
                "message": {
                    "message_id": 50,
                    "from": {"id": 987654321, "first_name": "Ahmed", "username": "ahmed_dev"},
                    "chat": {"id": 987654321, "first_name": "Ahmed", "username": "ahmed_dev"},
                    "date": int(time.time()),
                    "text": f"/start {token}",
                },
            }
        ],
    }

    mock_send_response = {"ok": True, "result": {"message_id": 51}}

    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_get.return_value.json.return_value = mock_updates_response
        mock_post.return_value.json.return_value = mock_send_response

        verify_res = verify_telegram_linking(token, bot_token="MOCK_BOT_TOKEN")
        assert verify_res["success"] is True
        assert verify_res["chat_id"] == "987654321"
        assert verify_res["username"] == "ahmed_dev"

        # Token should be consumed
        assert token not in _PENDING_LINKING_TOKENS


def test_verify_telegram_linking_not_started_yet():
    """Verify linking reports clear instructions if user has not clicked start in Telegram."""
    token_res = generate_linking_token(customer_id="test_user", ttl_seconds=600)
    token = token_res["token"]

    mock_updates_response = {
        "ok": True,
        "result": [],  # No messages yet
    }

    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_updates_response

        verify_res = verify_telegram_linking(token, bot_token="MOCK_BOT_TOKEN")
        assert verify_res["success"] is False
        assert "No start message found in Telegram yet" in verify_res["error"]


def test_verify_telegram_linking_expired_token():
    """Verify expired linking codes are rejected."""
    token = "LINK_EXPIRED_99"
    _PENDING_LINKING_TOKENS[token] = {
        "customer_id": "test_user",
        "created_at": time.time() - 1000,
        "expires_at": time.time() - 100,  # Expired
    }

    verify_res = verify_telegram_linking(token, bot_token="MOCK_BOT_TOKEN")
    assert verify_res["success"] is False
    assert "expired" in verify_res["error"].lower()


def test_verify_telegram_linking_unconfigured():
    """Verify linking rejects when Telegram Bot Token is missing."""
    token_res = generate_linking_token(customer_id="test_user", ttl_seconds=600)
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": ""}, clear=False):
        verify_res = verify_telegram_linking(token_res["token"], bot_token="")
        assert verify_res["success"] is False
        assert "not configured" in verify_res["error"].lower()


def test_verify_telegram_linking_plain_token_and_case_insensitive():
    """Verify linking succeeds when customer sends raw token without /start or in lowercase."""
    token_res = generate_linking_token(customer_id="test_user", ttl_seconds=600)
    token = token_res["token"]

    mock_updates_response = {
        "ok": True,
        "result": [
            {
                "update_id": 1002,
                "message": {
                    "message_id": 55,
                    "from": {"id": 11223344, "first_name": "Salma", "username": "salma_user"},
                    "chat": {"id": 11223344, "first_name": "Salma", "username": "salma_user"},
                    "date": int(time.time()),
                    "text": token.lower(),  # lowercase raw token
                },
            }
        ],
    }

    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_get.return_value.json.return_value = mock_updates_response
        mock_post.return_value.json.return_value = {"ok": True, "result": {}}

        verify_res = verify_telegram_linking(token, bot_token="MOCK_BOT_TOKEN")
        assert verify_res["success"] is True
        assert verify_res["chat_id"] == "11223344"
        assert verify_res["username"] == "salma_user"


def test_verify_telegram_linking_missing_start_payload():
    """Verify that when user sends plain /start without linking code, specific guidance is returned."""
    token_res = generate_linking_token(customer_id="test_user", ttl_seconds=600)
    token = token_res["token"]

    mock_updates_response = {
        "ok": True,
        "result": [
            {
                "update_id": 1003,
                "message": {
                    "message_id": 60,
                    "from": {"id": 55667788, "first_name": "Kareem"},
                    "chat": {"id": 55667788, "first_name": "Kareem"},
                    "date": int(time.time()),
                    "text": "/start",  # Plain /start without token
                },
            }
        ],
    }

    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_updates_response

        verify_res = verify_telegram_linking(token, bot_token="MOCK_BOT_TOKEN")
        assert verify_res["success"] is False
        assert verify_res.get("code_missing") is True
        assert "missing your linking code" in verify_res["error"]
        assert token in verify_res["error"]


def test_verify_telegram_linking_webhook_conflict():
    """Verify 409 conflict when webhook is active is detected and reported cleanly."""
    token_res = generate_linking_token(customer_id="test_user", ttl_seconds=600)
    token = token_res["token"]

    mock_err_response = {
        "ok": False,
        "error_code": 409,
        "description": "Conflict: can't use getUpdates method while webhook is active; use deleteWebhook to delete the webhook first",
    }

    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_err_response

        verify_res = verify_telegram_linking(token, bot_token="MOCK_BOT_TOKEN")
        assert verify_res["success"] is False
        assert verify_res.get("conflict") is True
        assert "webhook is currently active" in verify_res["error"]
        assert "MOCK_BOT_TOKEN" not in verify_res["error"]


def test_verify_telegram_linking_polling_conflict():
    """Verify 409 conflict when another getUpdates process is active is reported cleanly."""
    token_res = generate_linking_token(customer_id="test_user", ttl_seconds=600)
    token = token_res["token"]

    mock_err_response = {
        "ok": False,
        "error_code": 409,
        "description": "Conflict: terminated by other getUpdates request; make sure that only one bot instance is running",
    }

    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_err_response

        verify_res = verify_telegram_linking(token, bot_token="MOCK_BOT_TOKEN")
        assert verify_res["success"] is False
        assert verify_res.get("conflict") is True
        assert "Another process is currently polling" in verify_res["error"]


def test_verify_telegram_linking_network_error_sanitizes_token():
    """Verify network exceptions never leak the bot token in error messages."""
    token_res = generate_linking_token(customer_id="test_user", ttl_seconds=600)
    secret_token = "SECRET_123456:XYZ_TOP_SECRET"

    with patch("requests.get", side_effect=Exception(f"Connection timed out to https://api.telegram.org/bot{secret_token}/getUpdates")):
        verify_res = verify_telegram_linking(token_res["token"], bot_token=secret_token)
        assert verify_res["success"] is False
        assert secret_token not in verify_res["error"]
        assert "<REDACTED_BOT_TOKEN>" in verify_res["error"]


def test_get_telegram_webhook_info():
    """Verify webhook info retrieval parses result and detects webhook status."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "ok": True,
            "result": {
                "url": "https://myapp.com/webhook",
                "pending_update_count": 5,
            },
        }
        res = get_telegram_webhook_info(bot_token="MOCK_TOKEN")
        assert res["ok"] is True
        assert res["has_webhook"] is True
        assert res["url"] == "https://myapp.com/webhook"
        assert res["pending_update_count"] == 5


def test_fetch_telegram_bot_username_discovery():
    """Verify dynamic discovery of bot username from getMe API."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "ok": True,
            "result": {"username": "SmartSemsarPropertyBot"},
        }
        # Reset cached username for test isolation
        import services.telegram_service as tg_mod
        tg_mod._CACHED_BOT_USERNAME = None
        discovered = fetch_telegram_bot_username("MOCK_BOT_TOKEN")
        assert discovered == "SmartSemsarPropertyBot"


def test_get_linking_token_info_helper():
    """Verify get_linking_token_info helper returns valid metadata and handles expiration."""
    res = generate_linking_token(customer_id="c_test", ttl_seconds=300)
    tok = res["token"]

    info = get_linking_token_info(tok)
    assert info is not None
    assert info["customer_id"] == "c_test"

    # Manipulate expiry
    _PENDING_LINKING_TOKENS[tok]["expires_at"] = time.time() - 10
    expired_info = get_linking_token_info(tok)
    assert expired_info is None
    assert tok not in _PENDING_LINKING_TOKENS



# --- Unit Tests: Telegram API Sending & Error Handling ---


def test_send_property_report_success_mock():
    """Verify property report delivery via mocked Telegram Bot API."""
    prop = get_property_by_id("PROP-001")
    assert prop is not None

    mock_post_res = {
        "ok": True,
        "result": {
            "message_id": 7777,
            "chat": {"id": 123456789},
            "date": 1690000000,
        },
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = mock_post_res

        res = send_property_report(
            chat_id="123456789",
            property_info=prop,
            customer_name="Kareem",
            bot_token="MOCK_TOKEN_999",
        )

        assert res["success"] is True
        assert res["message_id"] == 7777
        assert res["chat_id"] == "123456789"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["chat_id"] == "123456789"
        assert call_kwargs["json"]["parse_mode"] == "HTML"
        assert "Modern Apartment in New Cairo" in call_kwargs["json"]["text"]


def test_send_property_report_api_failure():
    """Verify Telegram API error response is reported to the caller."""
    prop = get_property_by_id("PROP-001")
    mock_post_err = {
        "ok": False,
        "description": "Forbidden: bot was blocked by the user",
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = mock_post_err

        res = send_property_report(
            chat_id="123456789",
            property_info=prop,
            bot_token="MOCK_TOKEN_999",
        )

        assert res["success"] is False
        assert "Forbidden: bot was blocked by the user" in res["error"]


def test_send_property_report_missing_config():
    """Verify sending reports without a configured bot token returns a clean error."""
    prop = get_property_by_id("PROP-001")
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": ""}, clear=False):
        res = send_property_report(chat_id="123456789", property_info=prop, bot_token="")
        assert res["success"] is False
        assert "not configured" in res["error"].lower()


def test_send_property_report_missing_chat_id():
    """Verify sending reports without a chat ID returns a clear error."""
    prop = get_property_by_id("PROP-001")
    res = send_property_report(chat_id="", property_info=prop, bot_token="MOCK_TOKEN")
    assert res["success"] is False
    assert "missing" in res["error"].lower()


def test_send_property_report_token_never_leaked_in_network_error():
    """Verify secret bot token is never exposed in error messages if network fails."""
    prop = get_property_by_id("PROP-001")
    secret_token = "TOP_SECRET_BOT_TOKEN_123"

    with patch("requests.post", side_effect=Exception(f"Connection failure to bot{secret_token}/sendMessage")):
        res = send_property_report(
            chat_id="123456789",
            property_info=prop,
            bot_token=secret_token,
        )
        assert res["success"] is False
        assert secret_token not in res["error"]
        assert "<REDACTED_BOT_TOKEN>" in res["error"]


# --- Integration Tests: Streamlit UI Flows ---


def test_streamlit_properties_page_telegram_linking_and_sending():
    """Verify Streamlit Properties page linking flow and Telegram report delivery."""
    with patch("views.properties.is_telegram_configured", return_value=(True, "Mock configured")):
        app_file = str(UI_PATH / "app.py")
        at = AppTest.from_file(app_file).run()

        at.session_state["current_page"] = "Properties"
        at.run()
        assert not at.exception

        selected_id = at.session_state.get("selected_property_id", "PROP-001")

        # 1. Unlinked state: Verify Connection button should exist
        verify_btn_key = f"btn_verify_tg_{selected_id}"
        v_buttons = [b for b in at.button if b.key == verify_btn_key]
        assert len(v_buttons) == 1

        # Mock verify_telegram_linking to return verified chat ID
        mock_verify_res = {
            "success": True,
            "chat_id": "555123456",
            "username": "tester_tg",
        }
        with patch("views.properties.verify_telegram_linking", return_value=mock_verify_res):
            v_buttons[0].click().run()
            assert not at.exception

        # Profile now has linked telegram_chat_id
        assert at.session_state["customer_profile"]["telegram_chat_id"] == "555123456"

        # 2. Linked state: Send Property Report button should now be available
        send_btn_key = f"btn_calc_tg_{selected_id}"
        send_buttons = [b for b in at.button if b.key == send_btn_key]
        assert len(send_buttons) == 1

        # Click Send Report
        mock_send_res = {"success": True, "message_id": 8888, "chat_id": "555123456"}
        with patch("views.properties.send_property_report", return_value=mock_send_res):
            send_buttons[0].click().run()
            assert not at.exception
            last_rep = at.session_state.get(f"tg_last_report_{selected_id}")
            assert last_rep is not None
            assert last_rep["message_id"] == 8888


def test_streamlit_booking_page_pre_booking_telegram_report():
    """Verify customer can send pre-booking Telegram report (Scenario 1: No booking)."""
    with patch("views.booking.is_google_calendar_authenticated", return_value=False), \
         patch("views.booking.is_google_calendar_configured", return_value=(False, "Mock unconfigured")), \
         patch("views.booking.is_telegram_configured", return_value=(True, "Mock configured")):
        app_file = str(UI_PATH / "app.py")
        at = AppTest.from_file(app_file).run()
        at.session_state["current_page"] = "Booking"
        # Pre-link Telegram in customer profile
        at.session_state["customer_profile"]["telegram_chat_id"] = "99887766"
        at.run()
        assert not at.exception

        selected_id = at.session_state.get("selected_property_id", "PROP-001")
        pre_send_key = f"btn_booking_pre_tg_{selected_id}"
        pre_buttons = [b for b in at.button if b.key == pre_send_key]
        assert len(pre_buttons) == 1

        mock_send_res = {"success": True, "message_id": 9001, "chat_id": "99887766"}
        with patch("views.booking.send_property_report", return_value=mock_send_res) as mock_send:
            pre_buttons[0].click().run()
            assert not at.exception
            mock_send.assert_called_once()
            # Scenario 1: booking_data MUST be None
            assert mock_send.call_args[1]["booking_data"] is None


def test_streamlit_booking_page_confirmed_booking_telegram_report():
    """Verify confirmed Google Calendar booking delivers viewing appointment on Telegram (Scenario 2)."""
    mock_cal_result = {
        "success": True,
        "event_id": "gcal_event_9988",
        "html_link": "https://calendar.google.com/event?eid=gcal_event_9988",
    }

    with patch("views.booking.is_google_calendar_authenticated", return_value=True), \
         patch("views.booking.is_google_calendar_configured", return_value=(True, "Mock configured")), \
         patch("views.booking.is_telegram_configured", return_value=(True, "Mock configured")), \
         patch("views.booking.create_viewing_event", return_value=mock_cal_result):

        app_file = str(UI_PATH / "app.py")
        at = AppTest.from_file(app_file).run()
        at.session_state["current_page"] = "Booking"
        # Pre-link Telegram in customer profile
        at.session_state["customer_profile"]["telegram_chat_id"] = "99887766"
        at.run()
        assert not at.exception

        # Submit viewing appointment
        at.button("booking_submit_btn").click().run()
        assert not at.exception
        assert "Confirmed on Google Calendar" in at.session_state["booking_data"]["status"]

        # Button to send confirmed report is present
        conf_send_buttons = [b for b in at.button if b.key == "btn_booking_confirmed_tg"]
        assert len(conf_send_buttons) == 1

        mock_send_res = {"success": True, "message_id": 9002, "chat_id": "99887766"}
        with patch("views.booking.send_property_report", return_value=mock_send_res) as mock_send:
            conf_send_buttons[0].click().run()
            assert not at.exception
            mock_send.assert_called_once()
            # Scenario 2: booking_data MUST be the confirmed booking
            sent_booking = mock_send.call_args[1]["booking_data"]
            assert sent_booking is not None
            assert sent_booking["status"] == "Confirmed on Google Calendar"
            assert sent_booking["calendar_event_id"] == "gcal_event_9988"
