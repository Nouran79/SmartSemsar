import streamlit as st
from components.cards import page_header
from services.property_service import get_properties, search_properties
from services.telegram_service import (
    format_property_report,
    generate_linking_token,
    get_confirmed_booking_for_property,
    is_telegram_configured,
    send_property_report,
    verify_telegram_linking,
)
from utils.session import get_session_telegram_link


def render_properties() -> None:
    page_header("Property catalogue", "Explore Properties", "Search the demo catalogue by location, type, budget, and bedroom count.")

    locations = ["All locations", "New Cairo", "New Administrative Capital", "Sheikh Zayed", "6th of October"]
    types = ["All types", "Apartment", "Villa", "Duplex"]
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        location = c1.selectbox("Location", locations)
        property_type = c2.selectbox("Property type", types)
        max_price = c3.number_input("Maximum price (EGP)", min_value=0, value=10_000_000, step=250_000)
        bedrooms = c4.number_input("Min. bedrooms", min_value=0, max_value=10, value=0)
    results = search_properties(location, property_type, max_price or None, bedrooms)

    with st.expander("🧮 Installments Calculator", expanded=False):
        st.subheader("Calculate Your Monthly Installment")

        demo_properties = get_properties()
        if not demo_properties:
            st.info("No properties available for calculation.")
        else:
            properties_by_id = {p["id"]: p for p in demo_properties}
            property_ids = list(properties_by_id.keys())

            current_selected = st.session_state.get("selected_property_id")
            if "last_synced_property_id" not in st.session_state:
                if current_selected in property_ids:
                    st.session_state["calc_property_id"] = current_selected
                    st.session_state["last_synced_property_id"] = current_selected
                else:
                    st.session_state["calc_property_id"] = property_ids[0]
                    st.session_state["last_synced_property_id"] = property_ids[0]
            elif current_selected and current_selected != st.session_state.get("last_synced_property_id"):
                if current_selected in property_ids:
                    st.session_state["calc_property_id"] = current_selected
                    st.session_state["last_synced_property_id"] = current_selected

            default_index = property_ids.index(st.session_state.get("calc_property_id", property_ids[0]))

            col_prop, col_price = st.columns([3, 1])
            with col_prop:
                selected_property_id = st.selectbox(
                    "Select property",
                    options=property_ids,
                    index=default_index,
                    format_func=lambda pid: f"{pid} - {properties_by_id[pid]['title']} (EGP {properties_by_id[pid]['price']:,.0f})",
                    key="calc_property_id",
                )

            selected_property = properties_by_id[selected_property_id]
            st.session_state["selected_property_id"] = selected_property_id
            st.session_state["last_synced_property_id"] = selected_property_id

            property_price = float(selected_property["price"])

            with col_price:
                st.metric("Property price", f"EGP {property_price:,.0f}")

            col1, col2 = st.columns(2)

            with col1:
                down_payment_percent = st.slider(
                    "Down payment (%)",
                    min_value=0,
                    max_value=100,
                    value=20,
                    key="calc_down_payment",
                )

            with col2:
                years = st.selectbox(
                    "Installment duration (years)",
                    [1, 2, 3, 5, 7, 10],
                    index=3,
                    key="calc_duration",
                )

            annual_interest_rate = st.number_input(
                "Flat annual interest rate (%)",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=0.5,
                help="Set to 0% for an interest-free estimate.",
                key="calc_interest",
            )

            down_payment = property_price * down_payment_percent / 100
            remaining = property_price - down_payment
            total_interest = remaining * annual_interest_rate / 100 * years
            total_installments = remaining + total_interest
            monthly_installment = total_installments / (years * 12)
            total_cost = down_payment + total_installments

            st.divider()
            c1, c2 = st.columns(2)

            c1.metric("Down payment", f"EGP {down_payment:,.0f}")
            c2.metric("Remaining amount", f"EGP {remaining:,.0f}")

            c1, c2, c3 = st.columns(3)
            c1.metric("Total interest", f"EGP {total_interest:,.0f}")
            c2.metric("Monthly installment", f"EGP {monthly_installment:,.0f}")
            c3.metric("Estimated total cost", f"EGP {total_cost:,.0f}")

            st.caption(
                "This estimate uses simple flat interest on the remaining balance; "
                "actual developer payment plans may differ."
            )

            st.divider()
            st.markdown("#### ✈️ Send Property Report via Telegram")

            is_tg_conf, tg_conf_msg = is_telegram_configured()
            customer_profile = st.session_state.get("customer_profile", {})
            tg_chat_id = customer_profile.get("telegram_chat_id")
            tg_username = customer_profile.get("telegram_username")

            if not is_tg_conf:
                st.warning(f"⚠️ {tg_conf_msg} Set TELEGRAM_BOT_TOKEN in your environment to enable Telegram delivery.")
            elif not tg_chat_id:
                st.info("💡 Link your Telegram account to receive property reports directly in your Telegram chat.")

                # Generate or reuse active one-time linking token for this session
                link_info = get_session_telegram_link(
                    customer_id=customer_profile.get("name", "customer")
                )
                bot_user = link_info.get("bot_username", "SmartSemsarPropertyBot")

                st.markdown(
                    f"**Step 1:** Open the Telegram bot with your one-time code (`{link_info['token']}`).\n\n"
                    f"**Step 2:** Press **Start** in Telegram.\n\n"
                    f"💡 *Already opened @{bot_user}? Just send this command in chat:*\n"
                    f"```\n/start {link_info['token']}\n```\n\n"
                    f"**Step 3:** Click **Verify Connection** below."
                )

                lcol1, lcol2, lcol3 = st.columns([2, 2, 1])
                with lcol1:
                    st.link_button(
                        "✈️ Open Bot in Telegram",
                        link_info["deep_link"],
                        type="primary",
                        use_container_width=True,
                        key=f"btn_open_tg_bot_{selected_property_id}",
                    )
                with lcol2:
                    if st.button("🔄 Verify Connection", key=f"btn_verify_tg_{selected_property_id}", use_container_width=True):
                        with st.spinner("Checking Telegram for your start message..."):
                            v_res = verify_telegram_linking(link_info["token"])
                        if v_res.get("success"):
                            st.session_state["customer_profile"]["telegram_chat_id"] = v_res["chat_id"]
                            st.session_state["customer_profile"]["telegram_username"] = v_res.get("username", "")
                            st.session_state.pop("active_tg_link_info", None)
                            st.success(f"✅ Telegram account linked! (Chat ID: {v_res['chat_id']})")
                            st.rerun()
                        else:
                            st.error(f"❌ {v_res.get('error')}")
                with lcol3:
                    if st.button("New Code", key=f"btn_new_tg_code_{selected_property_id}", use_container_width=True):
                        get_session_telegram_link(
                            customer_id=customer_profile.get("name", "customer"),
                            force_new=True,
                        )
                        st.rerun()
            else:
                # Connected state
                u_label = f" (@{tg_username})" if tg_username else ""
                st.success(f"✅ Connected to Telegram Chat: **{tg_chat_id}**{u_label}")

                # Check if there is an existing confirmed viewing for this property
                confirmed_booking = get_confirmed_booking_for_property(
                    selected_property_id,
                    booking_data=st.session_state.get("booking_data"),
                    booking_history=st.session_state.get("booking_history"),
                )

                if confirmed_booking:
                    st.info(
                        f"📅 Confirmed viewing appointment found for this property: "
                        f"**{confirmed_booking.get('date')} at {confirmed_booking.get('time')}**. "
                        "It will be included in the report."
                    )

                installment_plan = {
                    "down_payment": down_payment,
                    "down_payment_percent": down_payment_percent,
                    "remaining": remaining,
                    "total_interest": total_interest,
                    "total_installments": total_installments,
                    "monthly_installment": monthly_installment,
                    "total_cost": total_cost,
                    "years": years,
                    "annual_interest_rate": annual_interest_rate,
                }

                scol1, scol2 = st.columns([2, 1])
                with scol1:
                    if st.button(
                        "✈️ Send Property Report via Telegram",
                        key=f"btn_calc_tg_{selected_property_id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        with st.spinner("Sending property report to your Telegram chat..."):
                            send_res = send_property_report(
                                chat_id=tg_chat_id,
                                property_info=selected_property,
                                customer_name=customer_profile.get("name", "Valued Customer"),
                                installment_plan=installment_plan,
                                booking_data=confirmed_booking,
                            )
                        if send_res.get("success"):
                            st.success(f"🎉 Property report sent successfully to Telegram! (Message ID: {send_res.get('message_id')})")
                            st.session_state[f"tg_last_report_{selected_property_id}"] = send_res
                        else:
                            st.error(f"❌ Failed to send Telegram report: {send_res.get('error')}")

                with scol2:
                    if st.button("Disconnect", key=f"btn_unlink_tg_{selected_property_id}", use_container_width=True):
                        st.session_state["customer_profile"]["telegram_chat_id"] = None
                        st.session_state["customer_profile"]["telegram_username"] = None
                        st.rerun()

                preview_text = format_property_report(
                    property_info=selected_property,
                    customer_name=customer_profile.get("name", "Valued Customer"),
                    installment_plan=installment_plan,
                    booking_data=confirmed_booking,
                    format_type="plain",
                )
                with st.expander("👁️ Preview Message Text", expanded=False):
                    st.text_area("Message Content", preview_text, height=200, disabled=True, key=f"preview_calc_tg_{selected_property_id}")

    st.caption(f"{len(results)} demo properties found")
    if not results:
        st.warning("No properties match these filters. Try adjusting your search.")
        return
    columns = st.columns(2)
    for index, item in enumerate(results):
        with columns[index % 2]:
            with st.container(border=True):
                st.caption(item["id"])
                st.subheader(item["title"])
                st.write(f"📍 {item['location']}")
                st.metric("Price", f"EGP {item['price']:,.0f}")
                st.write(f"🛏️ {item['bedrooms']} bedrooms  ·  📐 {item['area_sqm']} m²")
                st.write(f"Finishing: {item['finishing']}")
                st.write(item["description"])
                c1, c2 = st.columns(2)
                if c1.button("View details", key=f"details_{item['id']}", use_container_width=True):
                    st.session_state["selected_property_id"] = item["id"]
                    st.session_state["current_page"] = "Recommendations"
                    st.rerun()
                is_favorite = item["id"] in st.session_state["favorite_property_ids"]
                if c2.button("♥ Saved" if is_favorite else "♡ Save", key=f"fav_{item['id']}", use_container_width=True):
                    favorites = st.session_state["favorite_property_ids"]
                    if is_favorite:
                        favorites.remove(item["id"])
                    else:
                        favorites.append(item["id"])
                    st.rerun()

                with st.expander("✈️ Telegram Report", expanded=False):
                    card_customer = st.session_state.get("customer_profile", {})
                    card_tg_chat_id = card_customer.get("telegram_chat_id")
                    card_confirmed = get_confirmed_booking_for_property(
                        item["id"],
                        booking_data=st.session_state.get("booking_data"),
                        booking_history=st.session_state.get("booking_history"),
                    )
                    if card_confirmed:
                        st.caption(f"✅ Confirmed viewing: {card_confirmed.get('date')} at {card_confirmed.get('time')}")

                    if not card_tg_chat_id:
                        st.caption("Telegram not connected yet.")
                        c_link = get_session_telegram_link(customer_id="customer")
                        st.caption(f"Send `/start {c_link['token']}` to @{c_link.get('bot_username', 'SmartSemsarPropertyBot')}")
                        c_col1, c_col2 = st.columns(2)
                        with c_col1:
                            st.link_button("✈️ Open Bot", c_link["deep_link"], use_container_width=True, key=f"btn_card_open_tg_{item['id']}")
                        with c_col2:
                            if st.button("Verify Connection", key=f"btn_card_verify_tg_{item['id']}", use_container_width=True):
                                v_res = verify_telegram_linking(c_link["token"])
                                if v_res.get("success"):
                                    st.session_state["customer_profile"]["telegram_chat_id"] = v_res["chat_id"]
                                    st.session_state["customer_profile"]["telegram_username"] = v_res.get("username", "")
                                    st.session_state.pop("active_tg_link_info", None)
                                    st.success("✅ Telegram linked!")
                                    st.rerun()
                                else:
                                    st.error(v_res.get("error"))
                    else:
                        st.caption(f"Connected: Chat ID `{card_tg_chat_id}`")
                        if st.button("✈️ Send Property Report via Telegram", key=f"btn_card_send_tg_{item['id']}", use_container_width=True):
                            with st.spinner("Sending report to Telegram..."):
                                card_res = send_property_report(
                                    chat_id=card_tg_chat_id,
                                    property_info=item,
                                    customer_name=card_customer.get("name", "Valued Customer"),
                                    booking_data=card_confirmed,
                                )
                            if card_res.get("success"):
                                st.success(f"✅ Sent! (Message ID: {card_res.get('message_id')})")
                            else:
                                st.error(f"❌ {card_res.get('error')}")
