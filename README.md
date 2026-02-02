# Frac Consumables Planner

A multi-agent application for planning pump consumable orders for fracturing crews, built with LangGraph, LangChain, and Streamlit.

## Overview

This application helps fracturing crews optimize their consumable orders (valve packings, seals, plungers) by:

1. **Analyzing pump health** — comparing remaining consumable life vs job duration to identify critical, marginal, and healthy pumps
2. **Checking inventory** — spares on hand and available inventory from nearby crews (their spares minus their own needs)
3. **Simulating weather** — generating weather conditions that affect transfer travel times via multipliers (1.0x–2.0x)
4. **Cost-optimized ordering** — comparing per-unit borrow cost vs order cost for each consumable, choosing whichever is cheaper
5. **Transfer route planning** — building weather-adjusted routes from Crew A through source crews and back
6. **What-if analysis** — sensitivity analysis for weather, distance, and price changes

## Architecture

Three independent LangGraph StateGraph agents, composed procedurally by an intent-routed chatbot:

### Orchestrator Agent (6 nodes)
`extract_crew_info` → `calc_needs` → `read_inventory` → `gather_context` → `plan_order` → `generate_recommendation` → END

Produces an **OrderPlan** with cost-optimized borrow vs order decisions.

### Transfer Coordinator Agent (3 nodes)
`check_weather` → `plan_route` → `format_summary` → END

Consumes an OrderPlan, produces a **TransferPlan** with weather-adjusted travel times.

### Cost Analyzer Agent (4 nodes)
`load_config` → `calc_borrow_cost` → `calc_order_cost` → `compare_costs` → END

Consumes an OrderPlan + TransferPlan, produces a **CostBreakdown** with recommendation and savings.

### Agent Composition

Agents are independent — not nested or chained within a single graph. The chatbot layer dispatches them based on user intent:

| Intent | Agents Called | LLM Used? |
|--------|-------------|-----------|
| **STATUS** — pump health questions | None | Yes — responds freely with pump context |
| **ORDER** — "what should I order?" | Orchestrator only | No — deterministic |
| **COST** — cost comparison | Orchestrator → Transfer → Cost | No — deterministic |
| **EXPLAIN** — "why?" / "what if?" | Orchestrator (if needed) → Transfer | Yes — interprets sensitivity results |

## UI

Two-tab Streamlit interface:

- **Pump Status** — geographic filtering, pump health dashboard with color-coded status, chatbot for fleet questions
- **Job Planning** — generate order plan button, order summary with cost metrics, editable quantities, chatbot for planning questions and what-if analysis

### Health Status Logic
- `remaining_life / job_duration >= 1.5` → Healthy (green)
- `>= 1.0` → Marginal (yellow)
- `< 1.0` → Critical (red) — pump will fail before job ends

## Project Structure

```
/frac-consumables-planner
├── /agent             # LangGraph agents (orchestrator, transfer, cost, intent router)
├── /data              # Crew data and example scenarios
├── /docs              # Architecture docs and diagram prompts
├── /generator         # Random data + weather generation
├── /prompts           # Chatbot system prompts
├── /schemas           # Pydantic v2 models (crew, order, transfer, cost, weather)
├── /tools             # LangChain tools (needs, inventory, planning, cost, weather, sensitivity)
├── /ui                # Streamlit app, chatbot logic, UI components
├── CLAUDE.md          # Project conventions
├── requirements.txt   # Python dependencies
└── README.md
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure Ollama is running with a model
ollama pull llama3

# Run the application
streamlit run ui/app.py
```

## Requirements

- Python 3.10+
- Ollama with llama3 (or any compatible model)

## Documentation

- [CLAUDE.md](CLAUDE.md) — project conventions and development guidelines
- [docs/architecture-diagram-prompt.md](docs/architecture-diagram-prompt.md) — comprehensive architecture description for generating diagrams
