# Phase 2 Output: Architecture (Generalized)

## 1. Folder Structure

```
/frac-consumables-planner
│
├── /data
│   ├── crews.json              # Default/example data (can be overwritten)
│   └── examples/               # Pre-built scenarios for testing
│       ├── scenario_3crews.json
│       ├── scenario_5crews.json
│       └── scenario_stress.json
│
├── /schemas
│   ├── __init__.py
│   ├── config.py               # SimulationConfig schema
│   ├── crew.py                 # Pump, Spares, Crew, CrewData schemas
│   └── order.py                # BorrowSource, OrderLineItem, OrderPlan schemas
│
├── /generator
│   ├── __init__.py
│   └── data_generator.py       # Generate random crew data from config
│
├── /tools
│   ├── __init__.py
│   ├── needs_calculator.py     # Tool: count pumps needing replacement
│   ├── inventory_reader.py     # Tool: read crew data, compute available spares
│   └── order_planner.py        # Tool: N-crew borrow logic
│
├── /agent
│   ├── __init__.py
│   └── orchestrator.py         # LangChain agent with tools bound
│
├── /prompts
│   └── prompts.py              # Agent system prompt and templates
│
├── /ui
│   └── app.py                  # Streamlit single-page app with config panel
│
├── CLAUDE.md                   # Project conventions
├── requirements.txt            # Dependencies
└── README.md                   # Project overview
```

---

## 2. What Lives in Each Folder

| Folder/File | Purpose |
|-------------|---------|
| `/data/crews.json` | Default crew data (overwritten when generating) |
| `/data/examples/` | Pre-built scenarios for quick testing |
| `/schemas/config.py` | `SimulationConfig` — all configurable parameters |
| `/schemas/crew.py` | `Pump`, `Spares`, `Crew`, `CrewData` — crew data models |
| `/schemas/order.py` | `BorrowSource`, `OrderLineItem`, `OrderPlan` — output models |
| `/generator/data_generator.py` | Functions to generate random crew data based on config |
| `/tools/needs_calculator.py` | Tool that counts pumps where life < job duration |
| `/tools/inventory_reader.py` | Tool that reads crews, computes available spares |
| `/tools/order_planner.py` | Tool that applies N-crew borrow logic |
| `/agent/orchestrator.py` | Creates LangChain agent, binds tools |
| `/prompts/prompts.py` | `SYSTEM_PROMPT` for agent |
| `/ui/app.py` | Streamlit app with config panel + main interface |
| `CLAUDE.md` | Project conventions |
| `requirements.txt` | Python dependencies |

---

## 3. Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              STREAMLIT UI                                       │
│                              /ui/app.py                                         │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ CONFIG PANEL                                                              │  │
│  │ - Sliders/inputs for all SimulationConfig parameters                      │  │
│  │ - [Generate] [Load] [Export] [Reset] buttons                              │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                    User clicks "Generate New Data"
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DATA GENERATOR                                        │
│                      /generator/data_generator.py                               │
│                                                                                 │
│   Input: SimulationConfig                                                       │
│   Output: CrewData (N crews, M pumps each, randomized values)                   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                    Returns generated CrewData
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              STREAMLIT UI                                       │
│  - Stores CrewData in session state                                             │
│  - Displays Crew A pump status                                                  │
│  - Displays all nearby crews (sorted by distance)                               │
│  - User clicks [Generate Order Plan]                                            │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATOR AGENT                                    │
│                          /agent/orchestrator.py                                 │
│                                                                                 │
│   1. Receives CrewData + config                                                 │
│   2. Calls tools in sequence                                                    │
│   3. Returns recommendation + OrderPlan                                         │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                      Agent calls tools
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│     NEEDS       │         │   INVENTORY     │         │     ORDER       │
│   CALCULATOR    │         │    READER       │         │    PLANNER      │
│─────────────────│         │─────────────────│         │─────────────────│
│ Input:          │         │ Input:          │         │ Input:          │
│  - crew_data    │         │  - crew_data    │         │  - needs        │
│  - config       │         │  - config       │         │  - crew A spares│
│                 │         │                 │         │  - nearby avail │
│ Logic:          │         │ Logic:          │         │  - config       │
│  For each       │         │  For each crew: │         │                 │
│  consumable:    │         │  - their needs  │         │ Logic:          │
│  count pumps    │         │  - their spares │         │  N-crew borrow  │
│  where life <   │         │  - available    │         │  algorithm      │
│  job_duration   │         │  Filter by      │         │                 │
│                 │         │  proximity      │         │ Output:         │
│ Output:         │         │  Sort by dist   │         │  - borrow plan  │
│  {consumable:   │         │                 │         │  - order qty    │
│   needed: X}    │         │ Output:         │         │  - total_cost   │
│                 │         │  nearby_crews[] │         │                 │
└─────────────────┘         └─────────────────┘         └─────────────────┘
                                      │
                                      ▼
                      Agent returns to Streamlit:
                        - recommendation: str
                        - order_plan: OrderPlan
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              STREAMLIT UI                                       │
│                                                                                 │
│   1. Displays agent recommendation                                              │
│   2. Shows editable order form                                                  │
│   3. User modifies quantities if needed                                         │
│   4. User clicks "Approve & Order"                                              │
│   5. Shows "Order sent" confirmation                                            │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. External Dependencies

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

## 5. Pydantic Schemas

### /schemas/config.py

```python
"""
Simulation configuration schema.
"""

from pydantic import BaseModel, Field


class SimulationConfig(BaseModel):
    """Configuration for data generation and simulation."""
    
    # Crew configuration
    num_crews: int = Field(default=3, ge=2, le=10, description="Total crews including Crew A")
    pumps_per_crew_min: int = Field(default=3, ge=1, le=20, description="Min pumps per crew")
    pumps_per_crew_max: int = Field(default=5, ge=1, le=20, description="Max pumps per crew")
    
    # Thresholds
    proximity_threshold_miles: float = Field(default=10.0, ge=1, le=50, description="Max distance for borrowing")
    consumables_per_pump: int = Field(default=5, ge=1, le=10, description="Parts needed per pump")
    
    # Generation ranges
    job_duration_min: int = Field(default=40, ge=10, le=500, description="Min job hours")
    job_duration_max: int = Field(default=80, ge=10, le=500, description="Max job hours")
    remaining_life_min: int = Field(default=30, ge=10, le=200, description="Min remaining life hours")
    remaining_life_max: int = Field(default=100, ge=10, le=200, description="Max remaining life hours")
    spares_min: int = Field(default=0, ge=0, le=100, description="Min spares per consumable")
    spares_max: int = Field(default=20, ge=0, le=100, description="Max spares per consumable")
    distance_min: float = Field(default=1.0, ge=0.5, le=100, description="Min distance from Crew A")
    distance_max: float = Field(default=15.0, ge=0.5, le=100, description="Max distance from Crew A")
    
    # Reproducibility
    seed: int | None = Field(default=None, description="Random seed for reproducible generation")
```

### /schemas/crew.py

```python
"""
Pydantic models for crew and pump data.
"""

from pydantic import BaseModel, Field


class Pump(BaseModel):
    """A single pump with remaining life per consumable."""
    
    pump_id: int = Field(description="Pump identifier (1, 2, 3, ...)")
    valve_packings_life: int = Field(description="Remaining life in hours")
    seals_life: int = Field(description="Remaining life in hours")
    plungers_life: int = Field(description="Remaining life in hours")


class Spares(BaseModel):
    """Spare parts inventory."""
    
    valve_packings: int = Field(default=0, description="Valve packing spares")
    seals: int = Field(default=0, description="Seal spares")
    plungers: int = Field(default=0, description="Plunger spares")


class Crew(BaseModel):
    """A fracturing crew."""
    
    crew_id: str = Field(description="Unique identifier (A, B, C, ...)")
    job_duration_hours: int = Field(description="Planned job duration")
    distance_to_crew_a: float | None = Field(default=None, description="Distance from Crew A (None for A)")
    pumps: list[Pump] = Field(description="List of pumps")
    spares: Spares = Field(description="Spare parts on hand")


class CrewData(BaseModel):
    """Root model for all crew data."""
    
    crews: list[Crew] = Field(description="All crews (variable length)")
    proximity_threshold_miles: float = Field(default=10.0)
    consumables_per_pump: int = Field(default=5)
```

### /schemas/order.py

```python
"""
Pydantic models for order plan output.
"""

from pydantic import BaseModel, Field
from .config import SimulationConfig


class BorrowSource(BaseModel):
    """A source crew for borrowing."""
    
    crew_id: str = Field(description="Crew to borrow from")
    quantity: int = Field(description="Quantity to borrow")
    distance: float = Field(description="Distance from Crew A")


class OrderLineItem(BaseModel):
    """A single line item in the order plan."""
    
    consumable_name: str = Field(description="valve_packings, seals, or plungers")
    pumps_needing_replacement: int = Field(description="Pumps where life < job duration")
    total_needed: int = Field(description="pumps × consumables_per_pump")
    spares_on_hand: int = Field(description="Crew A's spares")
    shortfall: int = Field(description="total_needed - spares_on_hand")
    borrow: list[BorrowSource] = Field(default_factory=list, description="Borrow sources")
    borrow_total: int = Field(description="Sum of borrowed quantities")
    to_order: int = Field(description="shortfall - borrow_total")
    unit_cost: float = Field(default=100.0, description="Cost per unit")


class OrderPlan(BaseModel):
    """Complete order plan."""
    
    crew_id: str = Field(description="Always 'A'")
    job_duration_hours: int = Field(description="Crew A's job duration")
    pump_count: int = Field(description="Crew A's pump count")
    nearby_crews_count: int = Field(description="Crews within proximity threshold")
    items: list[OrderLineItem] = Field(description="Order line items")
    total_order_cost: float = Field(description="Sum of (to_order × unit_cost)")
    recommendation: str = Field(description="Agent's explanation")
```

---

## 6. Data Generator

### /generator/data_generator.py

```python
"""
Generate random crew data based on SimulationConfig.
"""

import random
import string
from schemas.config import SimulationConfig
from schemas.crew import Pump, Spares, Crew, CrewData


def generate_crew_data(config: SimulationConfig) -> CrewData:
    """
    Generate randomized crew data based on configuration.
    
    Args:
        config: SimulationConfig with all parameters
    
    Returns:
        CrewData with N crews, each with M pumps
    """
    if config.seed is not None:
        random.seed(config.seed)
    
    crews = []
    crew_letters = list(string.ascii_uppercase)  # A, B, C, D, ...
    
    for i in range(config.num_crews):
        crew_id = crew_letters[i]
        
        # Generate pumps for this crew
        num_pumps = random.randint(config.pumps_per_crew_min, config.pumps_per_crew_max)
        pumps = []
        for p in range(1, num_pumps + 1):
            pump = Pump(
                pump_id=p,
                valve_packings_life=random.randint(config.remaining_life_min, config.remaining_life_max),
                seals_life=random.randint(config.remaining_life_min, config.remaining_life_max),
                plungers_life=random.randint(config.remaining_life_min, config.remaining_life_max)
            )
            pumps.append(pump)
        
        # Generate spares
        spares = Spares(
            valve_packings=random.randint(config.spares_min, config.spares_max),
            seals=random.randint(config.spares_min, config.spares_max),
            plungers=random.randint(config.spares_min, config.spares_max)
        )
        
        # Job duration
        job_duration = random.randint(config.job_duration_min, config.job_duration_max)
        
        # Distance (None for Crew A)
        distance = None
        if i > 0:  # Not Crew A
            distance = round(random.uniform(config.distance_min, config.distance_max), 1)
        
        crew = Crew(
            crew_id=crew_id,
            job_duration_hours=job_duration,
            distance_to_crew_a=distance,
            pumps=pumps,
            spares=spares
        )
        crews.append(crew)
    
    return CrewData(
        crews=crews,
        proximity_threshold_miles=config.proximity_threshold_miles,
        consumables_per_pump=config.consumables_per_pump
    )


def load_crew_data(filepath: str) -> CrewData:
    """Load crew data from JSON file."""
    import json
    with open(filepath, 'r') as f:
        data = json.load(f)
    return CrewData(**data)


def save_crew_data(crew_data: CrewData, filepath: str) -> None:
    """Save crew data to JSON file."""
    import json
    with open(filepath, 'w') as f:
        json.dump(crew_data.model_dump(), f, indent=2)
```

---

## 7. Tool Logic (Pseudocode)

### needs_calculator.py

```python
@tool
def calculate_needs(crew_data: CrewData, crew_id: str = "A") -> dict:
    """
    Count pumps needing replacement for each consumable.
    
    Returns: {consumable: {pumps_needing: int, total_needed: int}}
    """
    crew = get_crew_by_id(crew_data, crew_id)
    job_duration = crew.job_duration_hours
    consumables_per_pump = crew_data.consumables_per_pump
    
    results = {}
    for consumable in ["valve_packings", "seals", "plungers"]:
        pumps_needing = 0
        for pump in crew.pumps:
            life = getattr(pump, f"{consumable}_life")
            if life < job_duration:
                pumps_needing += 1
        
        results[consumable] = {
            "pumps_needing": pumps_needing,
            "total_needed": pumps_needing * consumables_per_pump
        }
    
    return results
```

### inventory_reader.py

```python
@tool
def read_inventory(crew_data: CrewData) -> dict:
    """
    Read all crews, compute available spares for nearby crews.
    
    Returns: {
        crew_a_spares: Spares,
        nearby_crews: [{crew_id, distance, available: {consumable: int}}]
    }
    """
    crew_a = get_crew_by_id(crew_data, "A")
    proximity = crew_data.proximity_threshold_miles
    consumables_per_pump = crew_data.consumables_per_pump
    
    nearby = []
    for crew in crew_data.crews:
        if crew.crew_id == "A":
            continue
        if crew.distance_to_crew_a > proximity:
            continue
        
        # Calculate what this crew needs
        their_needs = {}
        for consumable in ["valve_packings", "seals", "plungers"]:
            pumps_needing = sum(
                1 for p in crew.pumps 
                if getattr(p, f"{consumable}_life") < crew.job_duration_hours
            )
            their_needs[consumable] = pumps_needing * consumables_per_pump
        
        # Available = spares - their needs
        available = {}
        for consumable in ["valve_packings", "seals", "plungers"]:
            their_spares = getattr(crew.spares, consumable)
            available[consumable] = max(0, their_spares - their_needs[consumable])
        
        nearby.append({
            "crew_id": crew.crew_id,
            "distance": crew.distance_to_crew_a,
            "available": available
        })
    
    # Sort by distance (closest first)
    nearby.sort(key=lambda x: x["distance"])
    
    return {
        "crew_a_spares": crew_a.spares,
        "nearby_crews": nearby
    }
```

### order_planner.py

```python
@tool
def plan_order(
    needs: dict, 
    crew_a_spares: Spares, 
    nearby_crews: list,
    consumables_per_pump: int
) -> OrderPlan:
    """
    Apply N-crew borrow logic for each consumable.
    """
    items = []
    
    for consumable in ["valve_packings", "seals", "plungers"]:
        total_needed = needs[consumable]["total_needed"]
        spares_on_hand = getattr(crew_a_spares, consumable)
        shortfall = max(0, total_needed - spares_on_hand)
        
        if shortfall == 0:
            items.append(OrderLineItem(
                consumable_name=consumable,
                pumps_needing_replacement=needs[consumable]["pumps_needing"],
                total_needed=total_needed,
                spares_on_hand=spares_on_hand,
                shortfall=0,
                borrow=[],
                borrow_total=0,
                to_order=0
            ))
            continue
        
        # Apply N-crew borrow logic
        borrow, to_order = apply_n_crew_borrow_logic(shortfall, nearby_crews, consumable)
        
        items.append(OrderLineItem(
            consumable_name=consumable,
            pumps_needing_replacement=needs[consumable]["pumps_needing"],
            total_needed=total_needed,
            spares_on_hand=spares_on_hand,
            shortfall=shortfall,
            borrow=borrow,
            borrow_total=sum(b.quantity for b in borrow),
            to_order=to_order
        ))
    
    return OrderPlan(
        crew_id="A",
        job_duration_hours=crew_a.job_duration_hours,
        pump_count=len(crew_a.pumps),
        nearby_crews_count=len(nearby_crews),
        items=items,
        total_order_cost=sum(item.to_order * item.unit_cost for item in items),
        recommendation=""
    )


def apply_n_crew_borrow_logic(
    shortfall: int, 
    nearby_crews: list,  # Already sorted by distance
    consumable: str
) -> tuple[list[BorrowSource], int]:
    """
    Generalized N-crew borrow algorithm.
    
    1. Check if any single crew can fully fulfill → use closest one that can
    2. If no single crew can, accumulate from closest to furthest
    3. Order whatever remains
    
    Returns: (list[BorrowSource], to_order)
    """
    if shortfall <= 0:
        return [], 0
    
    # Step 1: Check for single-crew fulfillment
    for crew in nearby_crews:
        if crew["available"][consumable] >= shortfall:
            return [BorrowSource(
                crew_id=crew["crew_id"],
                quantity=shortfall,
                distance=crew["distance"]
            )], 0
    
    # Step 2: No single crew can fulfill — accumulate from all
    borrow = []
    remaining = shortfall
    
    for crew in nearby_crews:
        available = crew["available"][consumable]
        if available <= 0:
            continue
        
        take = min(available, remaining)
        borrow.append(BorrowSource(
            crew_id=crew["crew_id"],
            quantity=take,
            distance=crew["distance"]
        ))
        remaining -= take
        
        if remaining == 0:
            break
    
    # Step 3: Order remainder
    to_order = remaining
    
    return borrow, to_order
```

---

## 8. Example Scenarios

### /data/examples/scenario_3crews.json

Standard 3-crew setup (matches original Phase 1).

### /data/examples/scenario_5crews.json

5 crews with varying distances to test accumulation logic.

### /data/examples/scenario_stress.json

10 crews, 20 pumps each, low spares — tests edge cases.

---

## 9. Phase 2 Summary

| Question | Answer |
|----------|--------|
| **Folder structure** | 7 folders: data, schemas, generator, tools, agent, prompts, ui |
| **New components** | SimulationConfig, DataGenerator, N-crew borrow logic |
| **What's configurable** | Crews, pumps, thresholds, ranges, seed |
| **Data flow** | Config → Generator → CrewData → Tools → OrderPlan → UI |
| **Dependencies** | langchain, langchain-ollama, pydantic, streamlit |

---

## Next Step

**Phase 3: Skeleton** — Create project structure with empty files and CLAUDE.md.
