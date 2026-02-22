"""
Core chatbot logic for the frac consumables planner.

This module provides context-aware chatbot functionality with intent routing.
Messages are classified into four intents:
- STATUS: LLM answers freely about pump health
- ORDER: Deterministic order pipeline, no LLM
- COST: Full deterministic pipeline (order -> transfer -> cost), no LLM
- EXPLAIN: LLM-based explanation of order decisions and what-if sensitivity analysis
           (only active in job_planning context; falls through to STATUS otherwise)

Usage:
    from ui.chatbot import handle_chat_message, ChatMessage, ChatIntent

    response, intent = handle_chat_message(crew_data, message, history)
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from schemas.crew import CrewData
from schemas.order import OrderPlan
from schemas.transfer import TransferPlan
from schemas.cost import CostConfig
from schemas.chatbot_response import ChatbotResponse, OrderRecommendation
from tools.needs_calculator import calculate_needs
from tools.inventory_reader import read_inventory
from tools.order_planner import plan_order
from agent.orchestrator import _generate_recommendation
from agent.transfer_coordinator import _run_deterministic_transfer
from agent.cost_analyzer import _run_deterministic_cost_analysis
from tools.route_planner import format_transfer_plan
from tools.cost_calculator import format_cost_comparison, load_cost_config
from tools.weather_checker import check_weather
from tools.sensitivity_calculator import recalculate_sensitivity, set_sensitivity_context
from ui.intent_router import classify_intent, ChatIntent

# Fixed seed for stable weather within a session
DEFAULT_WEATHER_SEED = 42
from prompts.chatbot_prompts import (
    CHATBOT_BASE_PROMPT,
    PUMP_STATUS_CONTEXT_TEMPLATE,
    JOB_PLANNING_CONTEXT_TEMPLATE,
    ORDER_ANALYSIS_PROMPT,
)


@dataclass
class ChatMessage:
    """Represents a single chat message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


def order_plan_to_recommendations(order_plan: OrderPlan) -> list[OrderRecommendation]:
    """
    Convert OrderPlan to structured recommendations programmatically.

    This function generates recommendations deterministically from the order plan,
    without any LLM involvement. This ensures consistency with the Generate Order button.

    Args:
        order_plan: The pre-calculated order plan

    Returns:
        List of OrderRecommendation objects
    """
    recommendations = []
    for item in order_plan.items:
        # Add borrow recommendations
        if item.borrow_sources:
            for source in item.borrow_sources:
                recommendations.append(OrderRecommendation(
                    consumable=item.consumable_name,
                    action="borrow",
                    quantity=source.quantity,
                    source=source.crew_id
                ))
        # Add order recommendation if needed
        if item.to_order > 0:
            recommendations.append(OrderRecommendation(
                consumable=item.consumable_name,
                action="order",
                quantity=item.to_order,
                source=None
            ))
        # Add "none needed" if no action required
        if not item.borrow_sources and item.to_order == 0:
            recommendations.append(OrderRecommendation(
                consumable=item.consumable_name,
                action="none_needed",
                quantity=0,
                source=None
            ))
    return recommendations


def get_health_status(remaining_life: int, job_duration: int) -> tuple[str, str]:
    """
    Determine health status based on remaining life vs job duration.

    Returns:
        Tuple of (emoji, status_name)
    """
    if job_duration == 0:
        return ("🟢", "healthy")

    ratio = remaining_life / job_duration
    if ratio >= 1.5:
        return ("🟢", "healthy")
    elif ratio >= 1.0:
        return ("🟡", "marginal")
    else:
        return ("🔴", "critical")


def build_pump_status_context(crew_data: CrewData) -> str:
    """
    Build context string for pump status questions.

    Args:
        crew_data: Current crew data

    Returns:
        Formatted context string for LLM
    """
    total_pumps = 0
    crews_with_critical = 0
    pumps_needing_attention = 0
    crew_details_lines = []

    for crew in crew_data.crews:
        total_pumps += len(crew.pumps)
        crew_has_critical = False

        crew_lines = [f"\n#### Crew {crew.crew_id}"]
        # Safe geography access for backwards compatibility
        area = getattr(crew, 'area', 'Permian Basin')
        region = getattr(crew, 'region', 'Texas')
        country = getattr(crew, 'country', 'United States')
        crew_lines.append(f"- Location: {area}, {region}, {country}")
        crew_lines.append(f"- Job Duration: {crew.job_duration_hours} hours")
        if crew.distance_to_crew_a is not None:
            crew_lines.append(f"- Distance to Crew A: {crew.distance_to_crew_a} miles")
        crew_lines.append(f"- Spares: VP={crew.spares.valve_packings}, Seals={crew.spares.seals}, Plungers={crew.spares.plungers}")
        crew_lines.append("- Pumps:")

        for pump in crew.pumps:
            vp_emoji, vp_status = get_health_status(pump.valve_packings_life, crew.job_duration_hours)
            seals_emoji, seals_status = get_health_status(pump.seals_life, crew.job_duration_hours)
            plungers_emoji, plungers_status = get_health_status(pump.plungers_life, crew.job_duration_hours)

            if vp_status == "critical" or seals_status == "critical" or plungers_status == "critical":
                crew_has_critical = True
                pumps_needing_attention += 1

            crew_lines.append(f"  - Pump {pump.pump_id}:")
            crew_lines.append(f"    - Valve Packings: {pump.valve_packings_life}h {vp_emoji} ({vp_status})")
            crew_lines.append(f"    - Seals: {pump.seals_life}h {seals_emoji} ({seals_status})")
            crew_lines.append(f"    - Plungers: {pump.plungers_life}h {plungers_emoji} ({plungers_status})")

        if crew_has_critical:
            crews_with_critical += 1

        crew_details_lines.extend(crew_lines)

    context = PUMP_STATUS_CONTEXT_TEMPLATE.format(
        total_crews=len(crew_data.crews),
        total_pumps=total_pumps,
        crews_with_critical=crews_with_critical,
        pumps_needing_attention=pumps_needing_attention,
        crew_details="\n".join(crew_details_lines)
    )

    return CHATBOT_BASE_PROMPT.format(context_data=context)


def build_job_planning_context(
    crew_data: CrewData,
    order_plan: OrderPlan | None = None
) -> str:
    """
    Build context string for job planning questions.

    Args:
        crew_data: Current crew data
        order_plan: Generated order plan (if available)

    Returns:
        Formatted context string for LLM
    """
    # Find Crew A
    crew_a = None
    for crew in crew_data.crews:
        if crew.distance_to_crew_a is None:
            crew_a = crew
            break

    if crew_a is None:
        return CHATBOT_BASE_PROMPT.format(context_data="Error: Crew A not found in data.")

    # Calculate needs
    needs = calculate_needs(crew_data, "A")
    needs_lines = []
    for consumable, data in needs.items():
        display_name = consumable.replace("_", " ").title()
        status = "NEEDS ATTENTION" if data["total_needed"] > 0 else "OK"
        needs_lines.append(f"- {display_name}: {data['pumps_needing']} pumps need replacement, {data['total_needed']} total needed ({status})")

    # Spares on hand
    spares_text = f"- Valve Packings: {crew_a.spares.valve_packings}\n- Seals: {crew_a.spares.seals}\n- Plungers: {crew_a.spares.plungers}"

    # Nearby crews
    inventory = read_inventory(crew_data)
    nearby_lines = []
    if inventory["nearby_crews"]:
        for nearby in inventory["nearby_crews"]:
            # Look up crew for geography (with safe access)
            nearby_crew = next((c for c in crew_data.crews if c.crew_id == nearby['crew_id']), None)
            location = f", {getattr(nearby_crew, 'area', 'Unknown')}" if nearby_crew else ""
            nearby_lines.append(f"- Crew {nearby['crew_id']} ({nearby['distance']} mi{location}): VP={nearby['available']['valve_packings']}, Seals={nearby['available']['seals']}, Plungers={nearby['available']['plungers']}")
    else:
        nearby_lines.append("- No nearby crews within proximity threshold")

    # Auto-generate order plan if not provided (ensures consistent recommendations)
    if order_plan is None:
        order_plan = plan_order(
            needs=needs,
            crew_a_spares=crew_a.spares,
            nearby_crews=inventory["nearby_crews"],
            crew_id=crew_a.crew_id,
            job_duration_hours=crew_a.job_duration_hours
        )

    # Order plan status
    plan_lines = [f"Recommended order plan for {order_plan.job_duration_hours}-hour job:"]
    for item in order_plan.items:
        display_name = item.consumable_name.replace("_", " ").title()
        plan_lines.append(f"- {display_name}: Need {item.total_needed}, Have {item.on_hand}, Order {item.to_order}")
        if item.borrow_sources:
            borrows = ", ".join([f"Crew {b.crew_id}: {b.quantity}" for b in item.borrow_sources])
            plan_lines.append(f"  Borrowing: {borrows}")
    order_plan_status = "\n".join(plan_lines)

    context = JOB_PLANNING_CONTEXT_TEMPLATE.format(
        crew_id=crew_a.crew_id,
        job_duration=crew_a.job_duration_hours,
        num_pumps=len(crew_a.pumps),
        consumables_per_pump=crew_data.consumables_per_pump,
        needs_summary="\n".join(needs_lines),
        spares_on_hand=spares_text,
        nearby_crews="\n".join(nearby_lines),
        order_plan_status=order_plan_status
    )

    return CHATBOT_BASE_PROMPT.format(context_data=context)


def create_chatbot_llm(model: str = "llama3") -> ChatOllama:
    """
    Create a ChatOllama instance for the chatbot.

    Args:
        model: Ollama model name

    Returns:
        Configured ChatOllama instance
    """
    return ChatOllama(model=model, temperature=0.3)


def generate_chat_response(
    llm: ChatOllama,
    system_prompt: str,
    chat_history: list[ChatMessage],
    user_message: str
) -> str:
    """
    Generate a chatbot response given context and history.

    Args:
        llm: ChatOllama instance
        system_prompt: Context-aware system prompt
        chat_history: Previous chat messages
        user_message: Current user question

    Returns:
        Assistant response string
    """
    # Build messages list
    messages = [SystemMessage(content=system_prompt)]

    # Add chat history (limit to last 10 messages for context window)
    for msg in chat_history[-10:]:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        else:
            messages.append(AIMessage(content=msg.content))

    # Add current user message
    messages.append(HumanMessage(content=user_message))

    try:
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        return f"I encountered an error: {str(e)}. Please make sure Ollama is running."


def format_structured_response(response: ChatbotResponse) -> str:
    """
    Format a structured chatbot response as human-readable text.

    Args:
        response: Structured ChatbotResponse object

    Returns:
        Formatted string for display
    """
    lines = [response.answer]

    if response.recommendations:
        lines.append("\n**Recommendations:**")
        for rec in response.recommendations:
            consumable_display = rec.consumable.replace("_", " ").title()
            if rec.action == "borrow":
                lines.append(f"- {consumable_display}: Borrow {rec.quantity} from Crew {rec.source}")
            elif rec.action == "order":
                lines.append(f"- {consumable_display}: Order {rec.quantity}")
            else:
                lines.append(f"- {consumable_display}: No action needed")

    return "\n".join(lines)


def generate_structured_chat_response(
    llm: ChatOllama,
    system_prompt: str,
    chat_history: list[ChatMessage],
    user_message: str,
    order_plan: OrderPlan | None = None
) -> str:
    """
    Generate a chatbot response with programmatic recommendations.

    The LLM generates the narrative answer. Recommendations are appended
    programmatically from the order plan to ensure 100% consistency.

    Args:
        llm: ChatOllama instance
        system_prompt: Context-aware system prompt
        chat_history: Previous chat messages
        user_message: Current user question
        order_plan: Pre-calculated order plan for generating recommendations

    Returns:
        Formatted assistant response string
    """
    # Build messages list
    messages = [SystemMessage(content=system_prompt)]

    # Add chat history (limit to last 10 messages for context window)
    for msg in chat_history[-10:]:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        else:
            messages.append(AIMessage(content=msg.content))

    # Add current user message
    messages.append(HumanMessage(content=user_message))

    try:
        # Get LLM response for the narrative answer
        llm_response = llm.invoke(messages)
        answer = llm_response.content

        # Append order plan recommendations directly (no complex struct needed)
        if order_plan:
            answer += "\n\n**Order Plan Recommendations:**"
            for item in order_plan.items:
                name = item.consumable_name.replace("_", " ").title()
                if item.borrow_sources:
                    for src in item.borrow_sources:
                        answer += f"\n- {name}: Borrow {src.quantity} from Crew {src.crew_id}"
                elif item.to_order > 0:
                    answer += f"\n- {name}: Order {item.to_order}"
                else:
                    answer += f"\n- {name}: No action needed"

        return answer
    except Exception as e:
        return f"I encountered an error: {str(e)}. Please make sure Ollama is running."


def run_order_pipeline(
    crew_data: CrewData,
    weather_seed: int = DEFAULT_WEATHER_SEED,
) -> tuple[OrderPlan | None, str]:
    """
    Run the cost-optimized order pipeline and return formatted output.

    Uses weather and cost data to make cost-optimal borrow vs order decisions.

    Args:
        crew_data: Current crew data
        weather_seed: Seed for reproducible weather data

    Returns:
        Tuple of (OrderPlan, formatted_response_string)
    """
    crew_a = None
    for crew in crew_data.crews:
        if crew.distance_to_crew_a is None:
            crew_a = crew
            break

    if crew_a is None:
        return None, "Error: Crew A not found in data."

    needs = calculate_needs(crew_data, "A")
    inventory = read_inventory(crew_data)
    weather_data = check_weather.invoke({"crew_data": crew_data, "seed": weather_seed})
    cost_config = load_cost_config()

    order_plan = plan_order(
        needs=needs,
        crew_a_spares=crew_a.spares,
        nearby_crews=inventory["nearby_crews"],
        crew_id=crew_a.crew_id,
        job_duration_hours=crew_a.job_duration_hours,
        weather_data=weather_data,
        cost_config=cost_config,
    )

    formatted = _generate_recommendation(order_plan, inventory["nearby_crews"])
    return order_plan, formatted


def run_cost_pipeline(
    crew_data: CrewData,
    order_plan: OrderPlan | None = None,
    weather_seed: int = DEFAULT_WEATHER_SEED,
) -> str:
    """
    Run the full cost pipeline: order -> transfer -> cost.

    Args:
        crew_data: Current crew data
        order_plan: Pre-existing order plan (if available)
        weather_seed: Seed for reproducible weather data

    Returns:
        Formatted cost analysis string
    """
    # Step 1: Ensure we have an order plan
    if order_plan is None:
        order_plan, _ = run_order_pipeline(crew_data, weather_seed)
        if order_plan is None:
            return "Error: Could not generate order plan."

    # Step 2: Run transfer pipeline (uses same weather seed)
    transfer_result = _run_deterministic_transfer(order_plan, crew_data, weather_seed)
    transfer_plan = transfer_result["transfer_plan"]

    # Step 3: Run cost analysis
    cost_result = _run_deterministic_cost_analysis(order_plan, transfer_plan)

    # Step 4: Format output
    lines = []

    # Include order summary
    inventory = read_inventory(crew_data)
    lines.append(_generate_recommendation(order_plan, inventory["nearby_crews"]))
    lines.append("")

    # Include transfer summary if there are borrows
    transfer_summary = transfer_result.get("summary", "")
    if transfer_summary and "No transfers needed" not in transfer_summary:
        lines.append("---")
        lines.append("")
        lines.append(format_transfer_plan(transfer_plan))
        lines.append("")

    # Include cost comparison
    lines.append("---")
    lines.append("")
    lines.append(format_cost_comparison(cost_result["comparison"]))

    return "\n".join(lines)


def _build_order_analysis_prompt(
    order_plan: OrderPlan,
    cost_summary: dict | None,
    transfer_plan: TransferPlan,
    cost_config: CostConfig,
) -> str:
    """
    Build the dynamic system prompt for the order analysis / sensitivity pipeline.

    Injects current order plan data, cost rationale, and weather context so
    the LLM can explain decisions and interpret sensitivity results.
    """
    lines: list[str] = []

    lines.append("## Current Order Plan")
    for item in order_plan.items:
        name = item.consumable_name.replace("_", " ").title()
        shortfall = max(0, item.total_needed - item.on_hand)
        lines.append(f"\n### {name}")
        lines.append(f"- Total Needed: {item.total_needed} | On Hand: {item.on_hand} | Shortfall: {shortfall}")
        if shortfall == 0:
            lines.append("- Status: Covered by on-hand spares — no action needed")
        else:
            if item.borrow_sources:
                for src in item.borrow_sources:
                    lines.append(f"- Borrow {src.quantity} from Crew {src.crew_id} ({src.distance:.1f} mi)")
            if item.to_order > 0:
                lines.append(f"- Order from supplier: {item.to_order}")

    if cost_summary:
        lines.append("\n## Cost Rationale (per consumable)")
        for consumable, data in cost_summary.get("items", {}).items():
            name = consumable.replace("_", " ").title()
            action = data.get("action", "")
            borrow_cpu = data.get("borrow_cost_per_unit")
            order_cpu = data.get("order_cost_per_unit")
            savings_cpu = data.get("savings_per_unit")
            lines.append(f"\n### {name} → {action.upper()}")
            if borrow_cpu is not None:
                lines.append(f"- Borrow cost/unit: ${borrow_cpu:.2f}")
            if order_cpu is not None:
                lines.append(f"- Order cost/unit: ${order_cpu:.2f}")
            if savings_cpu is not None and savings_cpu != 0:
                lines.append(f"- Savings/unit by choosing {action}: ${abs(savings_cpu):.2f}")

        total = cost_summary.get("total_estimated_cost")
        total_if_ordered = cost_summary.get("total_if_all_ordered")
        total_savings = cost_summary.get("total_savings")
        if total is not None:
            lines.append(f"\n**Recommended plan total: ${total:.2f}**")
            lines.append(f"**Cost if everything ordered: ${total_if_ordered:.2f}**")
            lines.append(f"**Total savings: ${total_savings:.2f}**")

    lines.append("\n## Cost Configuration")
    lines.append(f"- Travel: ${cost_config.travel.cost_per_mile}/mi, ${cost_config.travel.cost_per_hour_labor}/hr labor, {cost_config.travel.average_speed_mph} mph avg speed")
    for name, pricing in cost_config.consumables.items():
        lines.append(f"- {name.replace('_', ' ').title()}: ${pricing.unit_price}/unit")
    lines.append(f"- Shipping: ${cost_config.shipping.base_cost} base + ${cost_config.shipping.per_unit_cost}/unit")

    if transfer_plan.segments:
        lines.append("\n## Current Weather at Source Crews")
        for seg in transfer_plan.segments:
            lines.append(f"- {seg.from_crew}: {seg.weather_condition} ({seg.weather_multiplier}x travel time multiplier), {seg.distance_miles:.1f} mi")

    return ORDER_ANALYSIS_PROMPT.format(order_context="\n".join(lines))


WHAT_IF_PHRASES = [
    "what if", "if weather", "if it rains", "if it storms", "if storm",
    "if distance", "if price", "if parts", "if cost", "if conditions",
    "what would happen", "would it change", "would the decision",
    "suppose", "assuming", "sensitivity", "scenario",
]


def _is_what_if_question(message: str) -> bool:
    lower = message.lower()
    return any(phrase in lower for phrase in WHAT_IF_PHRASES)


def _extract_sensitivity_params(user_message: str, llm) -> dict:
    """Ask the LLM to extract scenario params as JSON only — no tool-calling needed."""
    prompt = (
        "Extract scenario parameters from this what-if question. "
        "Return ONLY a JSON object — no explanation, no markdown, no text before or after:\n"
        '{"weather_scenario": "current"|"clear"|"rain"|"storm", '
        '"distance_multiplier": <float>, "price_change_pct": <float>}\n\n'
        f'Question: "{user_message}"'
    )
    content = llm.invoke([HumanMessage(content=prompt)]).content
    match = re.search(r'\{[^}]+\}', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"weather_scenario": "current", "distance_multiplier": 1.0, "price_change_pct": 0.0}


def _run_what_if_pipeline(
    user_message: str,
    chat_history: list["ChatMessage"],
    system_prompt: str,
    llm,
) -> str:
    """Deterministic what-if path: always invokes recalculate_sensitivity, LLM only interprets."""
    params = _extract_sensitivity_params(user_message, llm)
    tool_result = recalculate_sensitivity.invoke(params)

    history_msgs: list = []
    for msg in chat_history[-6:]:
        if msg.role == "user":
            history_msgs.append(HumanMessage(content=msg.content))
        else:
            history_msgs.append(AIMessage(content=msg.content))

    messages = [
        SystemMessage(content=system_prompt),
        *history_msgs,
        HumanMessage(content=(
            f"User asked: {user_message}\n\n"
            f"Sensitivity analysis result:\n{tool_result}\n\n"
            "Interpret this result clearly and concisely for the user."
        )),
    ]
    return llm.invoke(messages).content


def run_explain_pipeline(
    crew_data: CrewData,
    order_plan: OrderPlan,
    cost_summary: dict | None,
    user_message: str,
    chat_history: list["ChatMessage"],
    model: str,
    weather_seed: int = DEFAULT_WEATHER_SEED,
) -> str:
    """
    Run the LLM-powered explanation / sensitivity analysis pipeline.

    The LLM receives the full order plan context and has access to
    recalculate_sensitivity so it can answer both explanation questions
    and what-if scenario questions naturally.

    Args:
        crew_data: Current crew data
        order_plan: The existing order plan from session state
        cost_summary: Cost metadata from the order planning run
        user_message: The user's question
        chat_history: Previous chat messages for conversational context
        model: Ollama model name
        weather_seed: Seed used for reproducible base weather

    Returns:
        Assistant response string
    """
    # Build base transfer plan for the sensitivity tool context
    transfer_result = _run_deterministic_transfer(order_plan, crew_data, weather_seed)
    transfer_plan: TransferPlan = transfer_result["transfer_plan"]
    cost_config = load_cost_config()

    # Inject base data into the sensitivity tool's module-level context
    set_sensitivity_context(order_plan, transfer_plan, cost_config)

    # Build dynamic system prompt with all current plan data
    system_prompt = _build_order_analysis_prompt(order_plan, cost_summary, transfer_plan, cost_config)

    # Create LLM
    llm = create_chatbot_llm(model=model)

    # Two-path split: what-if → deterministic pipeline, explain → ReAct agent
    if _is_what_if_question(user_message):
        return _run_what_if_pipeline(user_message, chat_history, system_prompt, llm)

    # Explanation path: ReAct agent with sensitivity tool bound
    agent = create_react_agent(
        model=llm,
        tools=[recalculate_sensitivity],
        prompt=system_prompt,
    )

    # Build message list from history + current message
    history_msgs: list = []
    for msg in chat_history[-8:]:
        if msg.role == "user":
            history_msgs.append(HumanMessage(content=msg.content))
        else:
            history_msgs.append(AIMessage(content=msg.content))
    history_msgs.append(HumanMessage(content=user_message))

    try:
        result = agent.invoke({"messages": history_msgs})
        return result["messages"][-1].content
    except Exception as e:
        return f"I encountered an error during analysis: {str(e)}. Make sure Ollama is running."


def handle_chat_message(
    crew_data: CrewData,
    user_message: str,
    chat_history: list[ChatMessage],
    order_plan: OrderPlan | None = None,
    selected_model: str = "llama3",
    context_mode: str = "pump_status",
    cost_summary: dict | None = None,
) -> tuple[str, ChatIntent]:
    """
    Route a user message to the appropriate handler based on intent.

    For status: LLM responds freely with pump data context.
    For order: Deterministic pipeline output, no LLM.
    For cost: Full deterministic pipeline output, no LLM.
    For explain (job_planning): LLM with order plan context + sensitivity tool.

    Args:
        crew_data: Current crew data
        user_message: The user's chat message
        chat_history: Previous chat messages
        order_plan: Pre-existing order plan from session state (if available)
        selected_model: Ollama model name for LLM responses
        context_mode: "pump_status" or "job_planning"
        cost_summary: Cost metadata from agent result (for job planning context)

    Returns:
        Tuple of (response_string, detected_intent)
    """
    intent = classify_intent(user_message)

    # In job planning context, EXPLAIN and COST both go to the LLM analysis pipeline
    if context_mode == "job_planning" and intent in (ChatIntent.EXPLAIN, ChatIntent.COST):
        if order_plan is None:
            # Generate order plan first so the pipeline has something to explain
            order_plan, _ = run_order_pipeline(crew_data)
            if order_plan is None:
                return "Could not generate an order plan to analyze. Please try generating one first.", intent
        response = run_explain_pipeline(
            crew_data=crew_data,
            order_plan=order_plan,
            cost_summary=cost_summary,
            user_message=user_message,
            chat_history=chat_history,
            model=selected_model,
        )
        return response, ChatIntent.EXPLAIN

    if intent == ChatIntent.ORDER:
        if order_plan is not None:
            inventory = read_inventory(crew_data)
            response = _generate_recommendation(order_plan, inventory["nearby_crews"])
        else:
            _, response = run_order_pipeline(crew_data)
        return response, intent

    elif intent == ChatIntent.COST:
        response = run_cost_pipeline(crew_data, order_plan)
        return response, intent

    else:
        # STATUS intent: LLM answers freely with pump context
        system_prompt = build_pump_status_context(crew_data)
        llm = create_chatbot_llm(model=selected_model)
        response = generate_chat_response(
            llm=llm,
            system_prompt=system_prompt,
            chat_history=chat_history,
            user_message=user_message
        )
        return response, intent
