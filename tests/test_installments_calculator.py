import sys
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

# Ensure smart_semsar_ui is in sys.path
UI_PATH = Path(__file__).parent.parent / "smart_semsar_ui"
if str(UI_PATH) not in sys.path:
    sys.path.insert(0, str(UI_PATH))

from services.property_service import get_properties, calculate_installments


def test_calculate_installments_exact_formula():
    """Verify formula outputs against known values."""
    # Test case 1: PROP-001 (4,800,000), 20% down, 5 years, 0% interest
    calc = calculate_installments(
        property_price=4_800_000.0,
        down_payment_percent=20.0,
        years=5,
        annual_interest_rate=0.0,
    )
    assert calc["down_payment"] == 960_000.0
    assert calc["remaining"] == 3_840_000.0
    assert calc["total_interest"] == 0.0
    assert calc["total_installments"] == 3_840_000.0
    assert calc["monthly_installment"] == 64_000.0
    assert calc["total_cost"] == 4_800_000.0

    # Test case 2: PROP-002 (4,250,000), 10% down, 3 years, 8% interest
    calc2 = calculate_installments(
        property_price=4_250_000.0,
        down_payment_percent=10.0,
        years=3,
        annual_interest_rate=8.0,
    )
    expected_dp = 425_000.0
    expected_rem = 3_825_000.0
    expected_interest = 3_825_000.0 * 0.08 * 3  # 918_000.0
    expected_total_inst = expected_rem + expected_interest  # 4_743_000.0
    expected_monthly = expected_total_inst / (3 * 12)  # 131_750.0
    expected_cost = expected_dp + expected_total_inst  # 5_168_000.0

    assert calc2["down_payment"] == expected_dp
    assert calc2["remaining"] == expected_rem
    assert calc2["total_interest"] == expected_interest
    assert calc2["total_installments"] == expected_total_inst
    assert calc2["monthly_installment"] == expected_monthly
    assert calc2["total_cost"] == expected_cost


def test_calculate_installments_edge_cases():
    """Verify boundary conditions like 0% down and 100% down payment."""
    # 0% down payment
    calc_zero_dp = calculate_installments(
        property_price=2_000_000.0,
        down_payment_percent=0.0,
        years=1,
        annual_interest_rate=10.0,
    )
    assert calc_zero_dp["down_payment"] == 0.0
    assert calc_zero_dp["remaining"] == 2_000_000.0
    assert calc_zero_dp["total_interest"] == 200_000.0
    assert calc_zero_dp["monthly_installment"] == (2_200_000.0 / 12)
    assert calc_zero_dp["total_cost"] == 2_200_000.0

    # 100% down payment
    calc_full_dp = calculate_installments(
        property_price=2_000_000.0,
        down_payment_percent=100.0,
        years=5,
        annual_interest_rate=10.0,
    )
    assert calc_full_dp["down_payment"] == 2_000_000.0
    assert calc_full_dp["remaining"] == 0.0
    assert calc_full_dp["total_interest"] == 0.0
    assert calc_full_dp["monthly_installment"] == 0.0
    assert calc_full_dp["total_cost"] == 2_000_000.0


def test_streamlit_installments_calculator_renders_and_updates():
    """Verify Streamlit Properties page calculator populates and updates property price."""
    app_file = str(UI_PATH / "app.py")
    at = AppTest.from_file(app_file).run()

    # Navigate to Properties page
    at.session_state["current_page"] = "Properties"
    at.run()
    assert not at.exception

    # Check selectbox exists
    prop_select = at.selectbox("calc_property_id")
    assert prop_select is not None
    assert prop_select.value == "PROP-001"

    # Verify metrics for default selection PROP-001 (price 4,800,000)
    metrics_by_label = {m.label: m.value for m in at.metric}
    assert metrics_by_label.get("Property price") == "EGP 4,800,000"
    assert metrics_by_label.get("Down payment") == "EGP 960,000"
    assert metrics_by_label.get("Remaining amount") == "EGP 3,840,000"
    assert metrics_by_label.get("Monthly installment") == "EGP 64,000"
    assert metrics_by_label.get("Estimated total cost") == "EGP 4,800,000"

    # Select a different property: PROP-002 (price 4,250,000)
    prop_select.select("PROP-002").run()
    assert not at.exception

    # Price and calculations must update automatically without stale session state
    updated_metrics = {m.label: m.value for m in at.metric}
    assert updated_metrics.get("Property price") == "EGP 4,250,000"
    assert updated_metrics.get("Down payment") == "EGP 850,000"
    assert updated_metrics.get("Remaining amount") == "EGP 3,400,000"
    assert updated_metrics.get("Monthly installment") == "EGP 56,667"
    assert updated_metrics.get("Estimated total cost") == "EGP 4,250,000"


def test_streamlit_installments_calculator_interest_and_duration():
    """Verify changes to duration, down payment, and interest rate update the estimate."""
    app_file = str(UI_PATH / "app.py")
    at = AppTest.from_file(app_file).run()
    at.session_state["current_page"] = "Properties"
    at.run()

    # Change duration to 3 years and annual interest to 10%
    at.selectbox("calc_duration").select(3).run()
    at.number_input("calc_interest").set_value(10.0).run()
    assert not at.exception

    # For PROP-001 (4,800,000):
    # down payment (20%): 960,000
    # remaining: 3,840,000
    # total interest: 3,840,000 * 0.10 * 3 = 1,152,000
    # total installments: 4,992,000
    # monthly installment: 4,992,000 / 36 = 138,667
    # total cost: 960,000 + 4,992,000 = 5,952,000
    metrics = {m.label: m.value for m in at.metric}
    assert metrics.get("Total interest") == "EGP 1,152,000"
    assert metrics.get("Monthly installment") == "EGP 138,667"
    assert metrics.get("Estimated total cost") == "EGP 5,952,000"


def test_streamlit_installments_duration_options_and_disclaimer():
    """Verify available duration options and flat interest estimate disclaimer."""
    app_file = str(UI_PATH / "app.py")
    at = AppTest.from_file(app_file).run()
    at.session_state["current_page"] = "Properties"
    at.run()
    assert not at.exception

    duration_select = at.selectbox("calc_duration")
    assert [int(x) for x in duration_select.options] == [1, 2, 3, 5, 7, 10]

    # Verify flat interest estimate disclaimer caption is rendered
    disclaimer_found = any(
        "simple flat interest" in c.value for c in at.caption
    )
    assert disclaimer_found, "Estimate disclaimer caption not found"


def test_external_property_selection_sync():
    """Verify that when a property was selected on another page, the calculator reflects it."""
    app_file = str(UI_PATH / "app.py")
    at = AppTest.from_file(app_file).run()

    # Simulate navigating to Recommendations and choosing PROP-003, then coming to Properties
    at.session_state["selected_property_id"] = "PROP-003"
    at.session_state["current_page"] = "Properties"
    at.run()
    assert not at.exception

    prop_select = at.selectbox("calc_property_id")
    assert prop_select.value == "PROP-003"

    # PROP-003 price is 6,200,000
    metrics = {m.label: m.value for m in at.metric}
    assert metrics.get("Property price") == "EGP 6,200,000"
    assert metrics.get("Down payment") == "EGP 1,240,000"
    assert metrics.get("Remaining amount") == "EGP 4,960,000"


def test_catalogue_search_and_property_cards_preserved():
    """Verify property search filters and property cards are unaffected by calculator."""
    app_file = str(UI_PATH / "app.py")
    at = AppTest.from_file(app_file).run()
    at.session_state["current_page"] = "Properties"
    at.run()
    assert not at.exception

    # 5 demo properties by default
    demo_count_caption = any("5 demo properties found" in c.value for c in at.caption)
    assert demo_count_caption

    # Check button details and favorites exist for properties
    details_buttons = [b for b in at.button if b.key.startswith("details_")]
    assert len(details_buttons) == 5
