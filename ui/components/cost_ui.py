"""
Cost analysis UI component for the Streamlit application.

This module provides the cost analysis interface that displays
borrow vs order cost comparisons and recommendations.

Usage:
    from ui.components.cost_ui import render_cost_analysis

    render_cost_analysis(order_plan, transfer_plan)
"""

import streamlit as st

from schemas.order import OrderPlan
from schemas.transfer import TransferPlan
from schemas.cost import CostConfig
from agent.cost_analyzer import run_cost_agent
from tools.cost_calculator import load_cost_config


def render_cost_comparison_card(borrow_cost: dict, order_cost: dict, comparison: dict):
    """
    Render side-by-side cost comparison cards.

    Args:
        borrow_cost: Borrow cost breakdown
        order_cost: Order cost breakdown
        comparison: Cost comparison with recommendation
    """
    comp = comparison.get("comparison", {})

    col1, col2 = st.columns(2)

    # Borrow option card
    with col1:
        is_recommended = comp.get("recommendation") == "borrow"
        border_color = "green" if is_recommended else None

        with st.container(border=True):
            if is_recommended:
                st.markdown("### 🚛 Borrow Option ✅")
            else:
                st.markdown("### 🚛 Borrow Option")

            st.metric("Total Cost", f"${borrow_cost['total_cost']:.2f}")

            st.caption("Breakdown:")
            st.write(f"- Travel: ${borrow_cost['travel_cost']:.2f}")
            st.write(f"- Labor: ${borrow_cost['labor_cost']:.2f}")

            if is_recommended:
                st.success("**Recommended** - Lower cost")

    # Order option card
    with col2:
        is_recommended = comp.get("recommendation") == "order"

        with st.container(border=True):
            if is_recommended:
                st.markdown("### 📦 Order Option ✅")
            else:
                st.markdown("### 📦 Order Option")

            st.metric("Total Cost", f"${order_cost['total_cost']:.2f}")

            st.caption("Breakdown:")
            st.write(f"- Parts: ${order_cost['parts_cost']:.2f}")
            st.write(f"- Shipping: ${order_cost['shipping_cost']:.2f}")

            if is_recommended:
                st.success("**Recommended** - Lower cost")


def render_savings_banner(comparison: dict):
    """
    Render the savings banner with recommendation.

    Args:
        comparison: Cost comparison with savings info
    """
    comp = comparison.get("comparison", {})
    savings = comp.get("savings", 0)
    recommendation = comp.get("recommendation", "")
    summary = comp.get("summary", "")

    if recommendation == "borrow":
        borrow_cost = comp.get("borrow_cost", 0)
        order_cost = comp.get("order_cost", 0)
        savings_pct = (savings / order_cost * 100) if order_cost > 0 else 0

        st.success(f"""
        ### 💰 Recommendation: BORROW

        **Save ${savings:.2f}** ({savings_pct:.1f}%) by borrowing instead of ordering!

        - Borrow cost: **${borrow_cost:.2f}**
        - Order cost: ~~${order_cost:.2f}~~
        """)

    elif recommendation == "order":
        borrow_cost = comp.get("borrow_cost", 0)
        order_cost = comp.get("order_cost", 0)
        savings_pct = (savings / borrow_cost * 100) if borrow_cost > 0 else 0

        st.info(f"""
        ### 📦 Recommendation: ORDER

        **Save ${savings:.2f}** ({savings_pct:.1f}%) by ordering instead of borrowing!

        - Order cost: **${order_cost:.2f}**
        - Borrow cost: ~~${borrow_cost:.2f}~~
        """)

    else:
        st.info("### ✓ No significant cost difference between options")


def render_cost_breakdown_table(comparison: dict):
    """
    Render detailed cost breakdown table.

    Args:
        comparison: Full comparison result
    """
    st.subheader("📊 Detailed Cost Breakdown")

    borrow = comparison.get("borrow_option", {})
    order = comparison.get("order_option", {})

    # Create comparison table data
    rows = [
        ("Travel Cost", f"${borrow.get('travel_cost', 0):.2f}", "-"),
        ("Labor Cost", f"${borrow.get('labor_cost', 0):.2f}", "-"),
        ("Parts Cost", "-", f"${order.get('parts_cost', 0):.2f}"),
        ("Shipping Cost", "-", f"${order.get('shipping_cost', 0):.2f}"),
        ("**TOTAL**", f"**${borrow.get('total_cost', 0):.2f}**", f"**${order.get('total_cost', 0):.2f}**"),
    ]

    # Display as markdown table
    table_md = "| Cost Item | Borrow | Order |\n|-----------|--------|-------|\n"
    for row in rows:
        table_md += f"| {row[0]} | {row[1]} | {row[2]} |\n"

    st.markdown(table_md)

    # Parts breakdown if ordering
    if order.get("parts_breakdown"):
        st.caption("Parts breakdown (if ordering):")
        for consumable, details in order["parts_breakdown"].items():
            name = consumable.replace("_", " ").title()
            st.write(f"- {name}: {details['quantity']} × ${details['unit_price']:.2f} = ${details['cost']:.2f}")


def render_cost_config_info(cost_config: CostConfig):
    """
    Render the cost configuration being used.

    Args:
        cost_config: Current cost configuration
    """
    with st.expander("⚙️ Cost Configuration"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Travel Costs:**")
            st.write(f"- Per mile: ${cost_config.travel.cost_per_mile:.2f}")
            st.write(f"- Per hour (labor): ${cost_config.travel.cost_per_hour_labor:.2f}")
            st.write(f"- Average speed: {cost_config.travel.average_speed_mph} mph")

        with col2:
            st.markdown("**Consumable Prices:**")
            for name, pricing in cost_config.consumables.items():
                display_name = name.replace("_", " ").title()
                st.write(f"- {display_name}: ${pricing.unit_price:.2f}")

        st.markdown("**Shipping:**")
        st.write(f"- Base cost: ${cost_config.shipping.base_cost:.2f}")
        st.write(f"- Per unit: ${cost_config.shipping.per_unit_cost:.2f}")


def render_cost_analysis(
    order_plan: OrderPlan | None = None,
    transfer_plan: TransferPlan | None = None,
):
    """
    Render the full cost analysis interface.

    Args:
        order_plan: OrderPlan from the order planning agent
        transfer_plan: TransferPlan from the transfer coordinator
    """
    st.header("Cost Analysis")
    st.caption("Compare borrow vs order costs")

    if order_plan is None:
        st.warning("⚠️ Generate an order plan first in the Job Planning tab.")
        return

    if transfer_plan is None:
        st.warning("⚠️ Generate a transfer plan first in the Transfer Planning tab.")
        return

    # Check if there are items to analyze
    has_needs = any(
        (item.total_needed - item.on_hand) > 0
        for item in order_plan.items
    )

    if not has_needs:
        st.info("✅ All consumables are covered by on-hand spares. No cost analysis needed.")
        return

    # Load cost config
    cost_config = load_cost_config()

    # Show config info
    render_cost_config_info(cost_config)

    st.divider()

    # Analyze costs button
    if st.button("💰 Analyze Costs", type="primary", use_container_width=True):
        with st.spinner("Analyzing costs..."):
            result = run_cost_agent(
                agent=None,  # Use deterministic mode
                order_plan=order_plan,
                transfer_plan=transfer_plan,
                cost_config=cost_config,
            )

            # Store in session state
            st.session_state["cost_result"] = result

        st.success("✅ Cost analysis complete!")
        st.rerun()

    # Display results if available
    if "cost_result" in st.session_state:
        result = st.session_state["cost_result"]

        # Savings banner
        render_savings_banner(result["comparison"])

        st.divider()

        # Side-by-side comparison
        render_cost_comparison_card(
            result["borrow_cost"],
            result["order_cost"],
            result["comparison"],
        )

        st.divider()

        # Detailed breakdown
        render_cost_breakdown_table(result["comparison"])

        # Recalculate button
        if st.button("🔄 Recalculate"):
            del st.session_state["cost_result"]
            st.rerun()
