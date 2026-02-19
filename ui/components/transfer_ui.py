"""
Transfer planning UI component for the Streamlit application.

This module provides the transfer planning interface that displays
weather conditions and route planning for consumable transfers.

Usage:
    from ui.components.transfer_ui import render_transfer_planning

    render_transfer_planning(crew_data, order_plan)
"""

import streamlit as st
import pandas as pd

from schemas.crew import CrewData
from schemas.order import OrderPlan
from schemas.transfer import TransferPlan
from agent.transfer_coordinator import run_transfer_agent


def get_weather_emoji(condition: str) -> str:
    """Get emoji for weather condition."""
    emojis = {
        "clear": "☀️",
        "cloudy": "⛅",
        "rain": "🌧️",
        "heavy_rain": "⛈️",
        "storm": "🌪️",
        "fog": "🌫️",
    }
    return emojis.get(condition, "❓")


def get_multiplier_color(multiplier: float) -> str:
    """Get color based on weather multiplier severity."""
    if multiplier <= 1.0:
        return "green"
    elif multiplier <= 1.3:
        return "orange"
    else:
        return "red"


def render_weather_overview(weather_data: dict):
    """
    Render weather conditions for all crews.

    Args:
        weather_data: Weather data from check_weather tool
    """
    st.subheader("🌤️ Weather Conditions")

    if not weather_data.get("crews"):
        st.info("No weather data available.")
        return

    # Create weather table
    weather_rows = []
    for crew in weather_data["crews"]:
        emoji = get_weather_emoji(crew["condition"])
        condition_display = crew["condition"].replace("_", " ").title()
        multiplier = crew["time_multiplier"]

        weather_rows.append({
            "Crew": crew["crew_id"],
            "Area": crew["area"],
            "Condition": f"{emoji} {condition_display}",
            "Temp": f"{crew['temperature_f']}°F",
            "Wind": f"{crew['wind_mph']} mph",
            "Visibility": f"{crew['visibility_miles']} mi",
            "Delay": f"{multiplier}x" if multiplier > 1.0 else "Normal",
        })

    df = pd.DataFrame(weather_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Warnings for hazardous conditions
    hazardous = [c for c in weather_data["crews"] if c["time_multiplier"] >= 1.6]
    if hazardous:
        st.warning(
            "⚠️ **Hazardous Conditions Detected**\n\n" +
            "\n".join([
                f"- Crew {c['crew_id']}: {c['condition'].replace('_', ' ').title()} "
                f"({c['time_multiplier']}x travel time)"
                for c in hazardous
            ])
        )


def render_transfer_route(transfer_plan: TransferPlan):
    """
    Render the transfer route with segments and timing.

    Args:
        transfer_plan: TransferPlan from route planner
    """
    st.subheader("🚛 Transfer Route")

    if not transfer_plan.segments:
        st.info("No transfers needed - all items covered by on-hand spares or ordering.")
        return

    # Route summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Distance", f"{transfer_plan.total_distance_miles} mi")
    with col2:
        base_mins = round(transfer_plan.total_base_time_hours * 60, 1)
        st.metric("Base Time", f"{base_mins} min")
    with col3:
        delay_mins = round(transfer_plan.weather_delay_hours * 60, 1)
        st.metric("Weather Delay", f"+{delay_mins} min", delta=f"+{delay_mins}" if delay_mins > 0 else None, delta_color="inverse")
    with col4:
        total_mins = round(transfer_plan.total_adjusted_time_hours * 60, 1)
        st.metric("Total Time", f"{total_mins} min")

    st.divider()

    # Route segments
    st.markdown("**Route Segments:**")

    for i, segment in enumerate(transfer_plan.segments, 1):
        with st.container(border=True):
            # Segment header
            emoji = get_weather_emoji(segment.weather_condition)
            time_mins = round(segment.adjusted_travel_time_hours * 60, 1)

            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.markdown(f"**{i}. Crew {segment.from_crew} → Crew {segment.to_crew}**")
            with col2:
                st.caption(f"{segment.distance_miles} mi • {time_mins} min • {emoji} {segment.weather_condition.replace('_', ' ').title()}")
            with col3:
                if segment.weather_multiplier > 1.0:
                    st.caption(f"⏱️ {segment.weather_multiplier}x")

            # Pickup items
            if segment.items_to_pickup:
                items_str = ", ".join([
                    f"{qty} {name.replace('_', ' ').title()}"
                    for name, qty in segment.items_to_pickup.items()
                ])
                st.success(f"📦 **Pickup:** {items_str}")


def render_pickup_manifest(transfer_plan: TransferPlan):
    """
    Render the pickup manifest showing what to get from each crew.

    Args:
        transfer_plan: TransferPlan with pickup manifest
    """
    st.subheader("📋 Pickup Manifest")

    if not transfer_plan.pickup_manifest:
        st.info("No items to pick up.")
        return

    for crew_id, items in transfer_plan.pickup_manifest.items():
        with st.container(border=True):
            st.markdown(f"**Crew {crew_id}**")

            cols = st.columns(len(items))
            for i, (consumable, qty) in enumerate(items.items()):
                with cols[i]:
                    display_name = consumable.replace("_", " ").title()
                    st.metric(display_name, qty)


def render_transfer_planning(
    crew_data: CrewData,
    order_plan: OrderPlan | None = None,
    weather_seed: int | None = None,
):
    """
    Render the full transfer planning interface.

    Args:
        crew_data: CrewData with crew information
        order_plan: OrderPlan from the order planning agent
        weather_seed: Optional seed for reproducible weather (for testing)
    """
    st.header("Transfer Planning")
    st.caption("Plan transfers between crews with weather-adjusted routing")

    if order_plan is None:
        st.warning("⚠️ Generate an order plan first in the Job Planning tab.")
        return

    # Check if there are any borrows in the order plan
    has_borrows = any(item.borrow_sources for item in order_plan.items)

    if not has_borrows:
        st.info("📦 No transfers needed - the order plan doesn't require borrowing from other crews.")

        # Show order plan summary
        st.subheader("Order Plan Summary")
        for item in order_plan.items:
            name = item.consumable_name.replace("_", " ").title()
            if item.to_order > 0:
                st.write(f"- **{name}**: Order {item.to_order} from supplier")
            elif item.total_needed == 0:
                st.write(f"- **{name}**: No action needed")
            else:
                st.write(f"- **{name}**: Covered by on-hand spares")
        return

    # Generate transfer plan button
    if st.button("🚛 Plan Transfer Route", type="primary", use_container_width=True):
        with st.spinner("Planning transfer route..."):
            result = run_transfer_agent(
                agent=None,  # Use deterministic mode
                order_plan=order_plan,
                crew_data=crew_data,
                weather_seed=weather_seed,
            )

            # Store in session state
            st.session_state["transfer_result"] = result

        st.success("✅ Transfer plan generated!")
        st.rerun()

    # Display results if available
    if "transfer_result" in st.session_state:
        result = st.session_state["transfer_result"]

        # Weather overview
        render_weather_overview(result["weather_data"])

        st.divider()

        # Transfer route
        render_transfer_route(result["transfer_plan"])

        st.divider()

        # Pickup manifest
        render_pickup_manifest(result["transfer_plan"])

        # Clear button
        if st.button("🔄 Regenerate with New Weather"):
            del st.session_state["transfer_result"]
            st.rerun()
