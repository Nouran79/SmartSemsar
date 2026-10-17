import datetime
import streamlit as st
from components.cards import page_header
from services.property_service import get_properties, get_property_by_id
from services.google_calendar_service import (
    authorize_google_calendar,
    create_viewing_event,
    get_upcoming_events,
    is_google_calendar_authenticated,
    is_google_calendar_configured,
)
from services.telegram_service import (
    format_property_report,
    generate_linking_token,
    get_confirmed_booking_for_property,
    is_confirmed_booking,
    is_telegram_configured,
    send_property_report,
    verify_telegram_linking,
)
from utils.session import get_session_telegram_link


def render_booking() -> None:
    page_header(
        "Next step",
        "Schedule a Viewing",
        "Book a property viewing appointment and sync it directly to Google Calendar.",
    )

    demo_properties = get_properties()
    if not demo_properties:
        st.warning("No demo properties found.")
        return

    properties_by_id = {p["id"]: p for p in demo_properties}
    property_ids = list(properties_by_id.keys())

    # Determine default selected property from session_state
    current_selected_id = st.session_state.get("selected_property_id", property_ids[0])
    default_index = (
        property_ids.index(current_selected_id)
        if current_selected_id in property_ids
        else 0
    )

    # Property selection
    st.markdown("#### 1. Select Property")
    selected_property_id = st.selectbox(
        "Property",
        options=property_ids,
        index=default_index,
        format_func=lambda pid: f"{pid} - {properties_by_id[pid]['title']} (EGP {properties_by_id[pid]['price']:,.0f})",
        key="booking_property_selection",
    )
    selected = properties_by_id[selected_property_id]
    st.session_state["selected_property_id"] = selected_property_id

    # Display selected property details card
    with st.container(border=True):
        col_info, col_price = st.columns([3, 1])
        with col_info:
            st.subheader(selected["title"])
            st.write(
                f"📍 {selected['location']}  ·  🛏️ {selected.get('bedrooms', 0)} bedrooms  ·  📐 {selected.get('area_sqm', 0)} m²"
            )
        with col_price:
            st.metric("Price", f"EGP {selected['price']:,.0f}")

    # Pre-booking Telegram Report (Scenario 1: No booking required)
    with st.expander("✈️ Send Property Report via Telegram (No booking required)", expanded=False):
        st.caption("Send an instant property overview and payment estimate directly to your Telegram chat.")
        is_tg_conf, tg_conf_msg = is_telegram_configured()
        pre_tg_customer = st.session_state.get("customer_profile", {})
        pre_tg_chat_id = pre_tg_customer.get("telegram_chat_id")

        if not is_tg_conf:
            st.warning(f"⚠️ {tg_conf_msg} Set TELEGRAM_BOT_TOKEN in your environment to enable Telegram delivery.")
        elif not pre_tg_chat_id:
            st.info("💡 Link your Telegram account to receive property reports directly in your Telegram chat.")
            pre_link_info = get_session_telegram_link(
                customer_id=pre_tg_customer.get("name", "customer")
            )
            bot_user = pre_link_info.get("bot_username", "SmartSemsarPropertyBot")
            st.markdown(
                f"**Step 1:** Open the Telegram bot with your one-time code (`{pre_link_info['token']}`).\n\n"
                f"**Step 2:** Press **Start** in Telegram.\n\n"
                f"💡 *Already opened @{bot_user}? Just send this command in chat:*\n"
                f"```\n/start {pre_link_info['token']}\n```\n\n"
                f"**Step 3:** Click **Verify Connection** below."
            )
            bcol1, bcol2 = st.columns([1, 1])
            with bcol1:
                st.link_button(
                    "✈️ Open Bot in Telegram",
                    pre_link_info["deep_link"],
                    type="primary",
                    use_container_width=True,
                    key=f"btn_open_pre_tg_bot_{selected['id']}",
                )
            with bcol2:
                if st.button("🔄 Verify Connection", key=f"btn_verify_pre_tg_{selected['id']}", use_container_width=True):
                    with st.spinner("Checking Telegram for your start message..."):
                        v_res = verify_telegram_linking(pre_link_info["token"])
                    if v_res.get("success"):
                        st.session_state["customer_profile"]["telegram_chat_id"] = v_res["chat_id"]
                        st.session_state["customer_profile"]["telegram_username"] = v_res.get("username", "")
                        st.session_state.pop("active_tg_link_info", None)
                        st.success(f"✅ Telegram account linked! (Chat ID: {v_res['chat_id']})")
                        st.rerun()
                    else:
                        st.error(f"❌ {v_res.get('error')}")
        else:
            st.success(f"✅ Connected to Telegram Chat: **{pre_tg_chat_id}**")
            if st.button(
                "✈️ Send Property Report via Telegram",
                key=f"btn_booking_pre_tg_{selected['id']}",
                type="primary",
                use_container_width=True,
            ):
                with st.spinner("Sending property report to your Telegram chat..."):
                    send_res = send_property_report(
                        chat_id=pre_tg_chat_id,
                        property_info=selected,
                        customer_name=pre_tg_customer.get("name", "Valued Customer"),
                        booking_data=None,  # No booking required (Scenario 1)
                    )
                if send_res.get("success"):
                    st.success(f"🎉 Property report sent to Telegram! (Message ID: {send_res.get('message_id')})")
                else:
                    st.error(f"❌ Failed to send Telegram report: {send_res.get('error')}")

            pre_report_txt = format_property_report(
                property_info=selected,
                customer_name=pre_tg_customer.get("name", "Valued Customer"),
                booking_data=None,
                format_type="plain",
            )
            with st.expander("👁️ Preview Message Text", expanded=False):
                st.text_area("Message Content", pre_report_txt, height=180, disabled=True, key=f"prev_booking_pre_tg_{selected['id']}")

    # Google Calendar integration status & setup banner
    is_configured, status_msg = is_google_calendar_configured()
    is_authenticated = is_google_calendar_authenticated()

    with st.expander(
        "📅 Google Calendar Integration Status",
        expanded=not is_authenticated,
    ):
        if is_authenticated:
            st.success("✅ Google Calendar is connected and authorized. Confirmed viewings will sync automatically.")
            if st.button("🔄 Re-authorize / Switch Account", key="btn_reauth_gcal"):
                with st.spinner("Opening Google OAuth consent in your browser..."):
                    auth_ok, auth_msg = authorize_google_calendar(interactive=True)
                if auth_ok:
                    st.success(f"✅ {auth_msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {auth_msg}")
        elif is_configured:
            st.warning("⚠️ Google Calendar client credentials found (`credentials.json`), but account access is not authorized yet.")
            st.write("Authorize your Google account to enable live viewing appointments sync to your Google Calendar:")
            if st.button("🔐 Authorize Google Calendar", type="primary", key="btn_auth_gcal"):
                with st.spinner("Opening Google OAuth consent in your browser... Please sign in and approve access."):
                    auth_ok, auth_msg = authorize_google_calendar(interactive=True)
                if auth_ok:
                    st.success(f"✅ {auth_msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {auth_msg}")
        else:
            st.warning("⚠️ Google Calendar credentials not found.")
            st.markdown(
                """
                **How to enable real Google Calendar sync:**
                1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create or select a project.
                2. Navigate to **APIs & Services > Library** and enable **Google Calendar API**.
                3. Configure the **OAuth consent screen** (User type: *External*, add your email as a Test user).
                4. Go to **Credentials > Create Credentials > OAuth client ID** (Application type: *Desktop app*).
                5. Download the credentials JSON and save it as `credentials.json` in the project root, or set `GOOGLE_CALENDAR_CREDENTIALS_FILE` in your `.env` file.
                6. *Note:* When credentials are not provided, viewing requests are safely recorded in your local session.
                """
            )

    # Booking Form
    st.markdown("#### 2. Viewing Appointment Details")
    customer_profile = st.session_state.get("customer_profile", {})
    default_name = customer_profile.get("name", "")
    default_phone = customer_profile.get("phone", "")

    with st.form("booking_form"):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            name = st.text_input("Customer name", value=default_name)
        with col_c2:
            phone = st.text_input("Phone number", value=default_phone)

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            today = datetime.date.today()
            date = st.date_input("Preferred date", value=today, min_value=today)
        with col_d2:
            time = st.selectbox(
                "Preferred time",
                ["10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00", "18:00"],
                index=1,
            )

        notes = st.text_area(
            "Additional notes",
            placeholder="e.g., Interested in developer payment plans, preferred language Arabic, special accessibility needs...",
        )
        submitted = st.form_submit_button(
            "Confirm viewing appointment",
            type="primary",
            use_container_width=True,
            key="booking_submit_btn",
        )

    # Handle submission
    if submitted:
        clean_name = name.strip()
        clean_phone = phone.strip()
        if not clean_name:
            st.error("Please enter a customer name.")
        elif not clean_phone:
            st.error("Please enter a phone number.")
        else:
            submission_key = f"{selected['id']}_{clean_name}_{str(date)}_{time}"
            confirmed_keys = st.session_state.setdefault("confirmed_booking_keys", set())

            if submission_key in confirmed_keys:
                st.warning("⚠️ This viewing appointment has already been submitted and confirmed.")
            else:
                if is_authenticated:
                    with st.spinner("Connecting to Google Calendar and creating appointment..."):
                        cal_result = create_viewing_event(
                            property_info=selected,
                            customer_name=clean_name,
                            customer_phone=clean_phone,
                            appointment_date=date,
                            appointment_time=time,
                            notes=notes,
                        )

                    if cal_result.get("success"):
                        confirmed_keys.add(submission_key)
                        booking_data = {
                            "property_id": selected["id"],
                            "property_title": selected["title"],
                            "customer_name": clean_name,
                            "phone": clean_phone,
                            "date": str(date),
                            "time": time,
                            "notes": notes,
                            "status": "Confirmed on Google Calendar",
                            "calendar_event_id": cal_result.get("event_id"),
                            "calendar_link": cal_result.get("html_link"),
                        }
                        st.session_state["booking_data"] = booking_data
                        st.session_state.setdefault("booking_history", []).append(booking_data)
                        st.session_state["active_confirmed_booking"] = booking_data
                        st.session_state.pop("active_unconfirmed_booking", None)
                    else:
                        error_msg = cal_result.get("error", "Unknown error")
                        st.error(f"❌ Failed to create Google Calendar event: {error_msg}")
                        booking_data = {
                            "property_id": selected["id"],
                            "property_title": selected["title"],
                            "customer_name": clean_name,
                            "phone": clean_phone,
                            "date": str(date),
                            "time": time,
                            "notes": notes,
                            "status": f"Saved locally (Google Calendar failed: {error_msg})",
                        }
                        st.session_state["booking_data"] = booking_data
                        st.session_state["active_unconfirmed_booking"] = booking_data
                        st.session_state.pop("active_confirmed_booking", None)
                        st.warning("The booking was saved locally in your session, but could not be added to Google Calendar.")
                else:
                    # Not authenticated -> save demo request locally without creating calendar event
                    status_desc = (
                        "Demo request saved in this session (Google Calendar not authorized)"
                        if is_configured
                        else "Demo request saved in this session (Google Calendar not configured)"
                    )
                    booking_data = {
                        "property_id": selected["id"],
                        "property_title": selected["title"],
                        "customer_name": clean_name,
                        "phone": clean_phone,
                        "date": str(date),
                        "time": time,
                        "notes": notes,
                        "status": status_desc,
                    }
                    st.session_state["booking_data"] = booking_data
                    st.session_state.setdefault("booking_history", []).append(booking_data)
                    st.session_state["active_unconfirmed_booking"] = booking_data
                    st.session_state.pop("active_confirmed_booking", None)
                    if is_configured:
                        st.info("Demo viewing request saved in this session. Authorize Google Calendar above to enable live sync.")
                    else:
                        st.info("Demo viewing request saved in this session. Configure Google Calendar above to enable live sync.")

    # Persistent Confirmation and Telegram Delivery Section
    active_conf = st.session_state.get("active_confirmed_booking")
    active_unconf = st.session_state.get("active_unconfirmed_booking")

    if active_conf and active_conf.get("property_id") == selected["id"]:
        st.success("🎉 Viewing appointment successfully created on Google Calendar!")
        if active_conf.get("calendar_link"):
            st.markdown(f"📅 **[Open in Google Calendar]({active_conf['calendar_link']})**")
        st.json(active_conf)

        st.markdown("#### ✈️ Send Confirmed Booking & Property Report via Telegram")
        conf_tg_chat_id = st.session_state.get("customer_profile", {}).get("telegram_chat_id")
        if conf_tg_chat_id:
            if st.button("✈️ Send Confirmed Report via Telegram", key="btn_booking_confirmed_tg", type="primary", use_container_width=True):
                with st.spinner("Sending confirmed viewing report to Telegram..."):
                    c_res = send_property_report(
                        chat_id=conf_tg_chat_id,
                        property_info=selected,
                        customer_name=active_conf.get("customer_name", "Valued Customer"),
                        booking_data=active_conf,
                    )
                if c_res.get("success"):
                    st.success(f"🎉 Confirmed appointment report sent to Telegram! (Message ID: {c_res.get('message_id')})")
                    st.session_state["booking_tg_report"] = c_res
                else:
                    st.error(f"❌ Failed to send Telegram report: {c_res.get('error')}")
        else:
            st.info("💡 Link your Telegram account to receive this confirmed booking report on Telegram.")
            b_link = get_session_telegram_link(customer_id=active_conf.get("customer_name", "customer"))
            st.caption(f"Send `/start {b_link['token']}` to @{b_link.get('bot_username', 'SmartSemsarPropertyBot')}")
            bc1, bc2 = st.columns([1, 1])
            with bc1:
                st.link_button("✈️ Open Bot in Telegram", b_link["deep_link"], type="primary", use_container_width=True, key="btn_open_conf_tg")
            with bc2:
                if st.button("🔄 Verify & Send Report", key="btn_verify_conf_tg", use_container_width=True):
                    v_res = verify_telegram_linking(b_link["token"])
                    if v_res.get("success"):
                        st.session_state["customer_profile"]["telegram_chat_id"] = v_res["chat_id"]
                        st.session_state["customer_profile"]["telegram_username"] = v_res.get("username", "")
                        st.session_state.pop("active_tg_link_info", None)
                        c_res = send_property_report(
                            chat_id=v_res["chat_id"],
                            property_info=selected,
                            customer_name=active_conf.get("customer_name", "Valued Customer"),
                            booking_data=active_conf,
                        )
                        if c_res.get("success"):
                            st.success(f"🎉 Account linked and confirmed report sent! (Message ID: {c_res.get('message_id')})")
                        else:
                            st.error(f"❌ Linked, but failed to send report: {c_res.get('error')}")
                        st.rerun()
                    else:
                        st.error(f"❌ {v_res.get('error')}")

        with st.expander("👁️ Preview Telegram Message", expanded=False):
            st.text_area(
                "Message Content",
                format_property_report(selected, active_conf.get("customer_name", "Valued Customer"), booking_data=active_conf, format_type="plain"),
                height=180,
                disabled=True,
                key="prev_booking_confirmed_tg",
            )
    elif active_unconf and active_unconf.get("property_id") == selected["id"]:
        st.json(active_unconf)
        st.markdown("#### ✈️ Send Property Report via Telegram")
        st.caption("A viewing appointment has not been confirmed on Google Calendar. Sending standard property report without booking information.")
        unconf_tg_chat_id = st.session_state.get("customer_profile", {}).get("telegram_chat_id")
        if unconf_tg_chat_id:
            if st.button("✈️ Send Property Report via Telegram", key="btn_booking_unconfirmed_tg", type="primary", use_container_width=True):
                with st.spinner("Sending property report to Telegram..."):
                    u_res = send_property_report(
                        chat_id=unconf_tg_chat_id,
                        property_info=selected,
                        customer_name=active_unconf.get("customer_name", "Valued Customer"),
                        booking_data=None,  # No booking information
                    )
                if u_res.get("success"):
                    st.success(f"🎉 Property report sent to Telegram! (Message ID: {u_res.get('message_id')})")
                    st.session_state["booking_tg_report"] = u_res
                else:
                    st.error(f"❌ Failed to send Telegram report: {u_res.get('error')}")
        else:
            st.info("💡 Link your Telegram account to receive property reports directly in your Telegram chat.")

        with st.expander("👁️ Preview Telegram Message", expanded=False):
            st.text_area(
                "Message Content",
                format_property_report(selected, active_unconf.get("customer_name", "Valued Customer"), booking_data=None, format_type="plain"),
                height=180,
                disabled=True,
                key="prev_booking_unconf_tg",
            )

    # Upcoming Appointments Section
    st.divider()
    st.subheader("📅 Upcoming Viewing Appointments")

    if is_authenticated:
        cal_upcoming = get_upcoming_events(max_results=10)
        if cal_upcoming.get("success"):
            events = cal_upcoming.get("events", [])
            if events:
                for evt in events:
                    with st.container(border=True):
                        ec1, ec2 = st.columns([3, 1])
                        with ec1:
                            st.markdown(f"**{evt.get('summary', 'Viewing Appointment')}**")
                            start_disp = evt.get("start", "")
                            end_disp = evt.get("end", "")
                            st.caption(f"🕒 Time: {start_disp} – {end_disp}")
                            if evt.get("location"):
                                st.write(f"📍 Location: {evt['location']}")
                            if evt.get("customer_name"):
                                st.write(f"👤 Customer: {evt['customer_name']} ({evt.get('customer_phone', '')})")
                        with ec2:
                            if evt.get("html_link"):
                                st.link_button("View on Calendar", evt["html_link"], use_container_width=True)
            else:
                st.info("No upcoming viewing appointments found on Google Calendar.")
        else:
            st.warning(f"Could not load upcoming calendar events: {cal_upcoming.get('error')}")
    else:
        history = st.session_state.get("booking_history", [])
        if history:
            for b in reversed(history):
                with st.container(border=True):
                    hc1, hc2 = st.columns([3, 1])
                    with hc1:
                        st.markdown(f"**{b.get('property_title', b.get('property_id'))}**")
                        st.caption(f"🕒 Date & Time: {b.get('date')} at {b.get('time')}")
                        st.write(f"👤 Customer: {b.get('customer_name')} ({b.get('phone')})")
                        if b.get("notes"):
                            st.write(f"📝 Notes: {b['notes']}")
                    with hc2:
                        st.caption("Status")
                        st.write(b.get("status", "Pending"))
                        if is_confirmed_booking(b):
                            hist_prop = get_property_by_id(b.get("property_id")) or selected
                            hist_chat_id = st.session_state.get("customer_profile", {}).get("telegram_chat_id")
                            if hist_chat_id:
                                if st.button("✈️ Telegram", key=f"btn_tg_hist_{b.get('property_id')}_{b.get('date')}_{b.get('time')}", use_container_width=True):
                                    with st.spinner("Sending to Telegram..."):
                                        h_res = send_property_report(
                                            chat_id=hist_chat_id,
                                            property_info=hist_prop,
                                            customer_name=b.get("customer_name", "Valued Customer"),
                                            booking_data=b,
                                        )
                                    if h_res.get("success"):
                                        st.success("Sent to Telegram!")
                                    else:
                                        st.error(h_res.get("error"))
        else:
            if is_configured:
                st.info("No viewing appointments scheduled yet in this session. Authorize Google Calendar above to view synced appointments.")
            else:
                st.info("No viewing appointments scheduled yet in this session.")
