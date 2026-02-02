# Architecture Diagram Prompt

Copy and paste everything below the line into a Claude session to generate the architecture diagram.

---

Generate a comprehensive, professional architecture diagram for the following system using Mermaid syntax. Make it visually clear with subgraphs, color coding, and directional flow. Include ALL components described below.

# System: Frac Consumables Planner

An AI-powered application that helps oil & gas fracturing crews optimize pump consumable orders by analyzing pump health, finding nearby crew inventory, checking weather conditions, and comparing borrow vs. order costs.

## Tech Stack
- LangGraph (StateGraph) for agent orchestration — all agents are deterministic sequential pipelines (NOT ReAct)
- LangChain + LangChain-Ollama for LLM integration (used only for chat, not for calculations)
- Pydantic v2 for data models
- Streamlit for web UI
- Ollama (local LLM, e.g. llama3)

## Data Models (Pydantic Schemas)

1. **CrewData** (root container)
   - crews: list[Crew] (A = primary, B-J = nearby)
   - proximity_threshold_miles
   - consumables_per_pump (default 5)

2. **Crew**
   - crew_id, job_duration_hours, distance_to_crew_a (None for Crew A)
   - pumps: list[Pump] (each has valve_packings_life, seals_life, plungers_life in hours remaining)
   - spares: Spares (counts of each consumable on-hand)
   - country, region, area (geographic hierarchy)

3. **OrderPlan** -> OrderLineItem[] -> BorrowSource[]
   - Per consumable: total_needed, on_hand, borrow_sources (crew_id + quantity + distance), to_order

4. **TransferPlan** -> RouteSegment[]
   - Route from Crew A -> source crews -> back to Crew A
   - Each segment: distance, base_travel_time, weather_condition, weather_multiplier, adjusted_travel_time

5. **CostConfig** -> TravelCostConfig + ConsumablePricing + ShippingCostConfig
   - Travel: cost_per_mile ($2.50), cost_per_hour_labor ($75), average_speed (30 mph)
   - Shipping: base_cost ($50), per_unit ($5), expedited_multiplier (2x)

6. **CostBreakdown** -> ItemCostBreakdown[]
   - Per consumable: borrow_cost vs order_cost -> recommended_action
   - Totals: travel_cost, total_borrow_cost, total_order_cost, savings

7. **WeatherCondition** (enum): CLEAR(1.0x), CLOUDY(1.1x), RAIN(1.3x), HEAVY_RAIN(1.6x), STORM(2.0x), FOG(1.4x)

8. **SimulationConfig** -> feeds into data generation with seed for reproducibility

## Three LangGraph Agents (all deterministic StateGraph pipelines, NOT ReAct)

### Agent 1: Orchestrator (6 nodes, sequential)
State: PlannerState (TypedDict)
Nodes:
1. `extract_crew_info` -> Find Crew A (distance_to_crew_a is None), extract job_duration
2. `calc_needs` -> For each pump: if remaining_life < job_duration, count consumables needed (calls calculate_needs tool)
3. `read_inventory` -> Get Crew A spares + nearby crews' available spares sorted by distance (calls read_inventory tool)
4. `gather_context` -> Generate weather for all crews + load CostConfig (calls check_weather tool + load_cost_config)
5. `plan_order` -> COST-OPTIMIZED: compare borrow_cost_per_unit vs order_cost_per_unit per consumable, borrow where cheaper, order the rest (calls plan_order tool)
6. `generate_recommendation` -> Format human-readable output + compute cost_summary
Flow: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> END
Output: OrderPlan + recommendation text + cost_summary

### Agent 2: Transfer Coordinator (3 nodes, sequential)
State: TransferState (TypedDict)
Input: Requires OrderPlan from Agent 1
Nodes:
1. `check_weather` -> Generate weather for all crews (calls check_weather tool)
2. `plan_route` -> Build route segments (Crew A -> sources -> Crew A), apply weather multipliers to travel times (calls plan_transfer_route tool)
3. `format_summary` -> Human-readable transfer plan (calls format_transfer_plan)
Flow: 1 -> 2 -> 3 -> END
Output: TransferPlan with weather-adjusted travel times

### Agent 3: Cost Analyzer (4 nodes, sequential)
State: CostState (TypedDict)
Input: Requires OrderPlan from Agent 1 AND TransferPlan from Agent 2
Nodes:
1. `load_config` -> Load or create default CostConfig (calls load_cost_config)
2. `calc_borrow_cost` -> distance x $/mile + time x $/hour, weather-adjusted (calls calculate_borrow_cost tool)
3. `calc_order_cost` -> parts + shipping (calls calculate_order_cost tool)
4. `compare_costs` -> Side-by-side comparison, recommendation, savings (calls compare_costs tool + format_cost_comparison)
Flow: 1 -> 2 -> 3 -> 4 -> END
Output: CostBreakdown with recommendation

### How the Agents Connect

IMPORTANT: The three agents are NOT chained within a single LangGraph. Each is an independent StateGraph with its own TypedDict state. They are composed PROCEDURALLY by the chatbot layer (ui/chatbot.py), which acts as the "orchestrator of orchestrators."

The data dependency chain is:
- Orchestrator produces OrderPlan
- Transfer Coordinator consumes OrderPlan, produces TransferPlan
- Cost Analyzer consumes OrderPlan + TransferPlan, produces CostBreakdown

Shared tools (not shared nodes):
- check_weather tool is used by both Orchestrator (node 4) and Transfer Coordinator (node 1)
- load_cost_config() is used by both Orchestrator (node 4) and Cost Analyzer (node 1)
- Weather is generated twice with the same seed (identical results) for state isolation

## Tools (LangChain @tool decorated)

| Tool | Input | Output | Used By |
|------|-------|--------|---------|
| calculate_needs | CrewData, crew_id | dict of consumables with pumps_needing, total_needed | Orchestrator node 2 |
| read_inventory | CrewData | crew_a_spares + nearby crews available (spares - their needs) | Orchestrator node 3 |
| plan_order | needs, spares, nearby, weather, cost_config | OrderPlan (cost-optimized) | Orchestrator node 5 |
| check_weather | CrewData, seed | Weather for all crews | Orchestrator node 4, Transfer node 1 |
| plan_transfer_route | OrderPlan, CrewData, weather_data | TransferPlan with route segments | Transfer node 2 |
| calculate_borrow_cost | TransferPlan, CostConfig | travel + labor costs | Cost node 2 |
| calculate_order_cost | OrderPlan, CostConfig | parts + shipping costs | Cost node 3 |
| compare_costs | OrderPlan, TransferPlan, CostConfig | Borrow vs order recommendation | Cost node 4 |
| recalculate_sensitivity | weather_scenario, distance_mult, price_change_pct | What-if cost comparison | EXPLAIN pipeline only |

## Intent Router + Chatbot (the orchestrator of orchestrators)

The chatbot layer (ui/chatbot.py) uses an LLM-based intent router to classify user messages into four intents, then dispatches to the appropriate pipeline:

### Intent: STATUS
- LLM responds freely with pump health context
- No agents called
- Used in both tabs

### Intent: ORDER
- If order_plan exists in session -> just formats it (no agent called)
- If no order_plan -> runs Orchestrator logic only (needs -> inventory -> weather -> plan_order)
- Transfer and Cost agents: NOT called
- Deterministic, no LLM

### Intent: COST
- Chains ALL THREE agents sequentially:
  1. Orchestrator (if no order_plan exists)
  2. Transfer Coordinator (needs OrderPlan)
  3. Cost Analyzer (needs OrderPlan + TransferPlan)
- Deterministic, no LLM

### Intent: EXPLAIN (only in job_planning tab)
- Runs Transfer Coordinator (to build context for sensitivity tool)
- Requires order_plan to already exist (generates one if missing)
- Does NOT call Cost Analyzer
- Two sub-paths:
  - "What if..." questions -> deterministic: extract params with LLM, run recalculate_sensitivity tool, LLM interprets results
  - "Why..." questions -> ReAct agent with sensitivity tool bound, LLM reasons freely

### Fallback
- If Ollama unavailable, keyword-based intent classification replaces LLM classification

## Streamlit UI (Two Tabs)

### Tab 1: Pump Status Dashboard
- Geographic cascading filters (Country -> Region -> Area)
- Crew cards with pump health table (red=critical, yellow=marginal, green=healthy)
- Health logic: ratio = remaining_life / job_duration. Below 1.0 = critical, 1.0-1.5 = marginal, above 1.5 = healthy
- Spares inventory display
- Chatbot (context_mode="pump_status") — STATUS intent only

### Tab 2: Job Planning
- "Generate Order Plan" button -> runs Orchestrator agent (full 6-node pipeline)
- Order summary table (consumable, needed, on-hand, borrow, order, costs, decision)
- Total cost metrics (recommended cost, if-all-ordered cost, savings)
- Editable order quantities
- "Approve & Order" button
- Chatbot (context_mode="job_planning") — all four intents active

### "Generate Order Plan" Button Flow
1. Creates compiled Orchestrator StateGraph
2. Runs all 6 nodes sequentially
3. Stores result in Streamlit session_state (order_plan, recommendation, weather_data, cost_summary)
4. Renders order summary table with cost metrics

## Data Generation
- SimulationConfig -> generate_crew_data() -> CrewData
- Random pumps with remaining_life, random spares, random distances
- Geographic hierarchy: 5 countries, 13 regions, ~30 oilfield areas (Permian Basin, Eagle Ford, Bakken, etc.)
- Seed parameter for reproducibility
- Also supports loading from JSON scenario files in /data/examples/

## Key Architecture Principles
1. Deterministic pipelines for ALL calculations (never LLM-generated numbers)
2. LLM only used for: intent classification, status Q&A, what-if explanations, sensitivity interpretation
3. No global state — TypedDict state flows through LangGraph nodes within each agent
4. Agents are independent StateGraphs composed procedurally by the chatbot layer
5. Cost optimization: per-unit borrow vs order comparison with weather adjustments
6. Weather affects transfer times via multipliers (1.0x-2.0x)
7. Nearby crew availability = their spares minus their own needs
8. The chatbot is the "orchestrator of orchestrators" — it decides which agents to invoke based on intent

## Diagram Requirements
- Show the complete data flow from user interaction through all three agents
- Show the Streamlit UI layer connecting to the chatbot/intent router
- Show the intent router dispatching to four different paths (STATUS, ORDER, COST, EXPLAIN)
- Show the agent dependency chain: Orchestrator -> Transfer Coordinator -> Cost Analyzer
- Clearly show that agents are INDEPENDENT graphs composed by the chatbot layer, not nested
- Show all tools grouped by which agent uses them
- Show the schema relationships (CrewData -> OrderPlan -> TransferPlan -> CostBreakdown)
- Use subgraphs for: UI Layer, Intent Router, Agent Layer (with sub-boxes per agent), Tools Layer, Data/Schema Layer
- Use color coding: blue for UI, green for agents, orange for tools, purple for schemas, red for LLM
- Show both the "Generate Order Plan" button flow AND the chatbot intent-based flows
- Make arrows show data flow direction with labels describing what's passed
- Include the health check logic (ratio-based: critical/marginal/healthy)
- Show shared tools (check_weather, load_cost_config) connecting to multiple agents
- Show the EXPLAIN pipeline's two sub-paths (what-if vs why)
