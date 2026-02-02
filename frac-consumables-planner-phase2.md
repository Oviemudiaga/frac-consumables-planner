# Phase 2 Output: Architecture

## 1. Folder Structure

```
/frac-consumables-planner
│
├── /data
│   └── crews.json              # Static dataset for Crews A, B, C
│
├── /schemas
│   ├── __init__.py
│   ├── crew.py                 # Pydantic models for crew/inventory data
│   └── order.py                # Pydantic models for order plan output
│
├── /tools
│   ├── __init__.py
│   ├── needs_calculator.py     # Tool: calculate consumables needed
│   ├── inventory_reader.py     # Tool: read crew inventory from static data
│   └── order_planner.py        # Tool: compute borrow vs order quantities
│
├── /agent
│   ├── __init__.py
│   └── orchestrator.py         # LangChain agent with tools bound
│
├── /prompts
│   └── prompts.py              # Agent system prompt and templates
│
├── /ui
│   └── app.py                  # Streamlit single-page app
│
├── CLAUDE.md                   # Project conventions
├── requirements.txt            # Dependencies
└── README.md                   # Project overview
```

---

## 2. What Lives in Each Folder

| Folder/File | Purpose |
|-------------|---------|
| `/data/crews.json` | Static dataset: Crews A, B, C with pump count, distance, inventory, remaining life, surplus |
| `/schemas/crew.py` | Pydantic models: `Crew`, `Consumable`, `Inventory` |
| `/schemas/order.py` | Pydantic models: `OrderPlan`, `OrderLineItem`, `BorrowSource` |
| `/tools/needs_calculator.py` | Tool that takes pumps + hours → returns qty needed per consumable |
| `/tools/inventory_reader.py` | Tool that reads crews.json → returns inventory and surplus data |
| `/tools/order_planner.py` | Tool that takes needs + inventory → returns borrow plan + order qty |
| `/agent/orchestrator.py` | Creates LangChain agent, binds tools, handles invocation |
| `/prompts/prompts.py` | `SYSTEM_PROMPT` for agent behavior, `RECOMMENDATION_TEMPLATE` for output |
| `/ui/app.py` | Streamlit app: displays job plan, nearby inventory, order form, handles approval |
| `CLAUDE.md` | Conventions for Pydantic, prompts, tools |
| `requirements.txt` | Python dependencies |

---

## 3. Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              STREAMLIT UI                                   │
│                              /ui/app.py                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    User inputs: pumps=12, hours=200
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATOR AGENT                                │
│                          /agent/orchestrator.py                             │
│                                                                             │
│   1. Receives user request                                                  │
│   2. Calls tools in sequence                                                │
│   3. Returns recommendation + structured order plan                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    Agent calls tools as needed
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐         ┌─────────────────┐         ┌─────────────────┐
│    NEEDS      │         │   INVENTORY     │         │     ORDER       │
│  CALCULATOR   │         │    READER       │         │    PLANNER      │
│───────────────│         │─────────────────│         │─────────────────│
│ Input:        │         │ Input:          │         │ Input:          │
│  - pumps: 12  │         │  - crew_ids     │         │  - needs        │
│  - hours: 200 │         │  - proximity: 5 │         │  - inventory    │
│               │         │                 │         │  - surplus      │
│ Output:       │         │ Output:         │         │                 │
│  - valve_pack │         │  - crew A inv   │         │ Output:         │
│    ings: 60   │         │  - crew B inv   │         │  - borrow_plan  │
│  - seals: 60  │         │  - crew C inv   │         │  - order_qty    │
│  - valves: 60 │         │  - surplus qty  │         │  - total_cost   │
└───────────────┘         └─────────────────┘         └─────────────────┘
                                    │
                          Reads from static data
                                    │
                                    ▼
                          ┌─────────────────┐
                          │  /data/crews.json│
                          └─────────────────┘


RETURN FLOW:
─────────────────────────────────────────────────────────────────────────────

Agent returns to Streamlit:
  - recommendation: str (natural language explanation)
  - order_plan: OrderPlan (Pydantic model)

                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              STREAMLIT UI                                   │
│                                                                             │
│   1. Displays agent recommendation                                          │
│   2. Shows editable order form (from OrderPlan)                             │
│   3. User modifies quantities if needed                                     │
│   4. User clicks "Approve & Order"                                          │
│   5. Shows "Order sent" confirmation                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Detailed Component Interactions

### Step-by-Step Flow

| Step | Component | Action | Input | Output |
|------|-----------|--------|-------|--------|
| 1 | Streamlit | User enters job params | — | `{pumps: 12, hours: 200}` |
| 2 | Streamlit | Calls agent | `{pumps: 12, hours: 200}` | — |
| 3 | Agent | Calls `needs_calculator` | `{pumps: 12, hours: 200}` | `{valve_packings: 60, seals: 60, valves: 60}` |
| 4 | Agent | Calls `inventory_reader` | `{crew_ids: ["A", "B", "C"]}` | `List[CrewInventory]` with qty, life, surplus |
| 5 | Agent | Calls `order_planner` | needs + inventory | `OrderPlan` with borrow sources + order qty |
| 6 | Agent | Generates recommendation | OrderPlan | Natural language explanation |
| 7 | Agent | Returns to Streamlit | — | `{recommendation: str, order_plan: OrderPlan}` |
| 8 | Streamlit | Displays order form | OrderPlan | Editable table |
| 9 | Streamlit | User approves | Modified quantities | — |
| 10 | Streamlit | Shows confirmation | — | "Order sent" message |

---

## 5. External Dependencies

### requirements.txt

```
# LLM & Agent
langchain>=0.1.0
langchain-ollama>=0.1.0

# Structured Output
pydantic>=2.0.0

# UI
streamlit>=1.30.0

# Utilities
python-dotenv>=1.0.0
```

### External Requirements

| Requirement | Purpose | Setup |
|-------------|---------|-------|
| **Ollama** | Local LLM runtime | Install from ollama.com, run `ollama pull llama3` |
| **Python 3.10+** | Runtime | — |

---

## 6. Pydantic Schemas (Preview)

### /schemas/crew.py

```python
from pydantic import BaseModel, Field

class Consumable(BaseModel):
    name: str
    quantity: int
    remaining_life_hours: int
    surplus: int = 0

class Crew(BaseModel):
    crew_id: str
    pumps: int
    distance_miles: float | None = None  # None for Crew A (self)
    inventory: list[Consumable]
```

### /schemas/order.py

```python
from pydantic import BaseModel, Field

class BorrowSource(BaseModel):
    crew_id: str
    quantity: int

class OrderLineItem(BaseModel):
    consumable_name: str
    total_needed: int
    on_hand_usable: int
    borrow: list[BorrowSource]
    borrow_total: int
    to_order: int
    unit_cost: float = 100.0  # Mock cost

class OrderPlan(BaseModel):
    crew_id: str
    job_duration_hours: int
    pump_count: int
    items: list[OrderLineItem]
    total_order_cost: float
    recommendation: str
```

---

## 7. Static Data Structure (Preview)

### /data/crews.json

```json
{
  "crews": [
    {
      "crew_id": "A",
      "pumps": 12,
      "distance_miles": null,
      "inventory": [
        {"name": "valve_packings", "quantity": 10, "remaining_life_hours": 50, "surplus": 0},
        {"name": "seals", "quantity": 15, "remaining_life_hours": 60, "surplus": 0},
        {"name": "valves", "quantity": 8, "remaining_life_hours": 40, "surplus": 0}
      ]
    },
    {
      "crew_id": "B",
      "pumps": 8,
      "distance_miles": 3,
      "inventory": [
        {"name": "valve_packings", "quantity": 20, "remaining_life_hours": 150, "surplus": 10},
        {"name": "seals", "quantity": 25, "remaining_life_hours": 200, "surplus": 15},
        {"name": "valves", "quantity": 12, "remaining_life_hours": 180, "surplus": 6}
      ]
    },
    {
      "crew_id": "C",
      "pumps": 6,
      "distance_miles": 4,
      "inventory": [
        {"name": "valve_packings", "quantity": 12, "remaining_life_hours": 180, "surplus": 5},
        {"name": "seals", "quantity": 10, "remaining_life_hours": 160, "surplus": 5},
        {"name": "valves", "quantity": 8, "remaining_life_hours": 150, "surplus": 3}
      ]
    }
  ],
  "proximity_threshold_miles": 5,
  "consumables_per_pump": 5
}
```

---

## Phase 2 Summary

| Question | Answer |
|----------|--------|
| **Folder structure** | 6 folders: data, schemas, tools, agent, prompts, ui |
| **What lives where** | Static data in /data, Pydantic in /schemas, LangChain tools in /tools, agent in /agent, Streamlit in /ui |
| **Data flow** | Streamlit → Agent → Tools (calculate, read, plan) → Agent returns OrderPlan → Streamlit displays → User approves |
| **Dependencies** | langchain, langchain-ollama, pydantic, streamlit, python-dotenv |

---

## Next Step

**Phase 3: Skeleton** — Create empty project structure with docstrings and CLAUDE.md.
