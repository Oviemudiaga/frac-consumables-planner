# Phase 1 Output: Frac Consumables Planner (Generalized)

## 1. Problem Statement

Fracturing crews shut down mid-job because they run out of consumables (valve packings, seals, plungers). Shutdowns are expensive — idle equipment, delayed production. Crews also over-order because they can't see what's available nearby, tying up capital in redundant inventory.

**One sentence:** This tool prevents costly mid-job shutdowns by calculating consumable needs proactively and leveraging surplus from nearby crews to minimize ordering.

---

## 2. User

**Team Lead (Crew A)** — responsible for planning the frac job and ensuring no shutdown due to missing parts.

**Secondary use:** Simulation and scenario planning — test different crew configurations, distances, and inventory levels.

---

## 3. Today's Pain

- Estimates parts needed from gut feel
- Calls other crew leads manually to check inventory
- Over-orders "just in case," tying up capital
- Discovers shortage mid-job → shutdown, scramble, delays
- No way to simulate "what if" scenarios before committing

---

## 4. MVP Scope

An agentic workflow that:
1. Generates or loads crew data based on configurable parameters
2. Calculates consumable needs based on per-pump remaining life vs job duration
3. Checks available spares from nearby crews (any number of crews)
4. Computes what to borrow vs. order using deterministic logic
5. Presents recommendation with explanation
6. Allows user to modify quantities and regenerate scenarios
7. Submits order on approval (mock confirmation)

**In scope:**
- 3 consumables: valve packings, seals, plungers
- **Configurable number of crews** (2+)
- **Configurable pumps per crew**
- **Configurable thresholds** (proximity, consumables per pump)
- **Data generator** for simulation scenarios
- Per-pump remaining life in hours
- Separate spares inventory per crew
- Each crew has their own job duration
- N-case deterministic borrow logic (generalized for N crews)
- LangChain agent with tool binding
- Ollama (local LLM)
- Single-page Streamlit UI with configuration panel
- "Order sent" confirmation on approval

**Out of scope:**
- Real inventory systems
- Multiple vendors / pricing
- Unexpected breakdowns
- Real procurement integration

---

## 5. Core Components

| Component | Type | Responsibility |
|-----------|------|----------------|
| **Config Manager** | Module | Store and validate simulation parameters |
| **Data Generator** | Module | Generate randomized crew data based on config |
| **Needs Calculator** | Tool | Count pumps where life < job duration, multiply by consumables_per_pump |
| **Inventory Reader** | Tool | Read all crews' pump data, spares, compute available spares |
| **Order Planner** | Tool | Apply N-crew borrow logic, compute order qty |
| **Orchestrator Agent** | LangChain Agent | Chains tools, determines if order needed, explains reasoning |
| **Streamlit UI** | UI | Config panel + job plan + nearby inventory + order form |

---

## 6. Configurable Parameters

| Parameter | Description | Default | Range |
|-----------|-------------|---------|-------|
| `num_crews` | Total crews including Crew A | 3 | 2-10 |
| `pumps_per_crew` | Number of pumps per crew (can vary) | 3-5 | 1-20 |
| `proximity_threshold_miles` | Max distance to consider for borrowing | 10 | 1-50 |
| `consumables_per_pump` | Parts needed per pump | 5 | 1-10 |
| `job_duration_range` | Min/max job hours for generation | 40-80 | 10-500 |
| `remaining_life_range` | Min/max remaining life for generation | 30-100 | 10-200 |
| `spares_range` | Min/max spares per consumable | 0-20 | 0-100 |
| `distance_range` | Min/max distance from Crew A | 1-15 | 0.5-100 |

---

## 7. Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     STREAMLIT UI                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ SIMULATION SETTINGS (toggleable panel)                    │  │
│  │ - Num crews, pumps, thresholds, ranges                    │  │
│  │ - [GENERATE NEW DATA] [LOAD FROM FILE] [RESET]            │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
            User clicks "Generate" or "Load"
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DATA GENERATOR                              │
│  - Creates N crews with M pumps each                            │
│  - Randomizes remaining life, spares, distances                 │
│  - Returns CrewData matching config                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     STREAMLIT UI                                │
│  - Displays Crew A status                                       │
│  - Displays all nearby crews                                    │
│  - User clicks [GENERATE ORDER PLAN]                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR AGENT                            │
│  1. Calls needs_calculator for Crew A                           │
│  2. Calls inventory_reader for all crews                        │
│  3. Calls order_planner with N-crew borrow logic                │
│  4. Returns recommendation + OrderPlan                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     STREAMLIT UI                                │
│  - Displays order plan                                          │
│  - User modifies / approves                                     │
│  - "Order sent" confirmation                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Calculation Rules

### Step 1: Count Pumps Needing Replacement (Per Consumable)

For each consumable type:
```
pumps_needing_replacement = count of pumps where remaining_life < job_duration
parts_needed = pumps_needing_replacement × consumables_per_pump
```

### Step 2: Calculate Shortfall

```
shortfall = parts_needed - spares_on_hand
```

If shortfall ≤ 0, no borrowing or ordering needed for this consumable.

### Step 3: Calculate Available Spares from Nearby Crews

For each nearby crew (within proximity_threshold_miles):
```
their_pumps_needing = count of pumps where remaining_life < their_job_duration
their_parts_needed = their_pumps_needing × consumables_per_pump
available_spares = their_total_spares - their_parts_needed
```

### Step 4: Apply N-Crew Borrow Logic (Generalized)

```
Given:
  - shortfall: what Crew A needs
  - nearby_crews: list sorted by distance (closest first)
  - Each crew has: available_spares

Algorithm:
  1. Filter crews within proximity threshold
  2. Sort by distance (closest first)
  3. Check if ANY single crew can fully fulfill
     - If multiple can → use closest
     - If only one can → use that one
  4. If no single crew can fulfill:
     - Accumulate from closest to furthest until fulfilled
  5. If all crews combined cannot fulfill:
     - Borrow all available from all crews
     - Order remainder

Pseudocode:
  remaining = shortfall
  borrow_plan = []
  
  # Check for single-crew fulfillment (prioritize closer)
  for crew in nearby_crews (sorted by distance):
      if crew.available >= shortfall:
          borrow_plan = [(crew.id, shortfall)]
          remaining = 0
          break
  
  # If no single crew can fulfill, accumulate from all
  if remaining > 0:
      borrow_plan = []
      for crew in nearby_crews (sorted by distance):
          take = min(crew.available, remaining)
          if take > 0:
              borrow_plan.append((crew.id, take))
              remaining -= take
          if remaining == 0:
              break
  
  to_order = remaining
  return borrow_plan, to_order
```

---

## 9. Inputs

### Configuration Schema

```python
class SimulationConfig(BaseModel):
    num_crews: int = 3                          # Total crews (including A)
    pumps_per_crew_min: int = 3
    pumps_per_crew_max: int = 5
    proximity_threshold_miles: float = 10.0
    consumables_per_pump: int = 5
    job_duration_min: int = 40
    job_duration_max: int = 80
    remaining_life_min: int = 30
    remaining_life_max: int = 100
    spares_min: int = 0
    spares_max: int = 20
    distance_min: float = 1.0
    distance_max: float = 15.0
    seed: int | None = None                     # For reproducible generation
```

### Generated Data Structure

```python
class CrewData(BaseModel):
    crews: list[Crew]                           # Variable length
    proximity_threshold_miles: float
    consumables_per_pump: int
```

### Example: 4 Crews Generated

```json
{
  "crews": [
    {
      "crew_id": "A",
      "job_duration_hours": 50,
      "distance_to_crew_a": null,
      "pumps": [
        {"pump_id": 1, "valve_packings_life": 55, "seals_life": 65, "plungers_life": 85},
        {"pump_id": 2, "valve_packings_life": 58, "seals_life": 45, "plungers_life": 90},
        {"pump_id": 3, "valve_packings_life": 40, "seals_life": 75, "plungers_life": 85}
      ],
      "spares": {"valve_packings": 0, "seals": 5, "plungers": 10}
    },
    {
      "crew_id": "B",
      "job_duration_hours": 40,
      "distance_to_crew_a": 4.0,
      "pumps": [...],
      "spares": {"valve_packings": 16, "seals": 7, "plungers": 6}
    },
    {
      "crew_id": "C",
      "job_duration_hours": 50,
      "distance_to_crew_a": 2.5,
      "pumps": [...],
      "spares": {"valve_packings": 10, "seals": 5, "plungers": 15}
    },
    {
      "crew_id": "D",
      "job_duration_hours": 60,
      "distance_to_crew_a": 8.0,
      "pumps": [...],
      "spares": {"valve_packings": 12, "seals": 8, "plungers": 4}
    }
  ],
  "proximity_threshold_miles": 10,
  "consumables_per_pump": 5
}
```

---

## 10. Outputs

### Order Plan (Structured)

```python
OrderPlan(
    crew_id="A",
    job_duration_hours=50,
    pump_count=3,
    config=SimulationConfig(...),               # Config used for this run
    items=[
        OrderLineItem(
            consumable_name="valve_packings",
            pumps_needing_replacement=1,
            total_needed=5,
            spares_on_hand=0,
            shortfall=5,
            borrow=[
                BorrowSource(crew_id="C", quantity=0),   # Closer but no availability
                BorrowSource(crew_id="B", quantity=5)    # Has availability
            ],
            borrow_total=5,
            to_order=0,
            unit_cost=100.0
        ),
        ...
    ],
    total_order_cost=0.0,
    recommendation="..."
)
```

---

## 11. UI Layout (Single Page with Config Panel)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  FRAC CONSUMABLES PLANNER                                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ▼ SIMULATION SETTINGS (collapsible)                                            │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │  Crews: [3] ←slider     Proximity: [10] mi    Consumables/pump: [5]       │ │
│  │  Pumps/crew: [3]-[5]    Job duration: [40]-[80] hrs                       │ │
│  │  Remaining life: [30]-[100] hrs    Spares: [0]-[20]                       │ │
│  │  Distance range: [1]-[15] mi       Seed: [____] (optional)                │ │
│  │                                                                           │ │
│  │  [ GENERATE NEW DATA ]  [ LOAD FROM FILE ]  [ EXPORT DATA ]  [ RESET ]    │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
├────────────────────────────────────┬────────────────────────────────────────────┤
│                                    │                                            │
│  CREW A - JOB PLAN                 │  NEARBY CREWS (within threshold)           │
│  Job Duration: 50 hrs              │                                            │
│                                    │  ┌──────────────────────────────────────┐ │
│  PUMP STATUS                       │  │ Crew C (2.5 mi) - Job: 50 hrs        │ │
│  ┌──────┬───────┬───────┬───────┐  │  │ Pumps: 4  |  Available: VP:0 S:0 P:15│ │
│  │ Pump │ VPack │ Seals │ Plngr │  │  ├──────────────────────────────────────┤ │
│  ├──────┼───────┼───────┼───────┤  │  │ Crew B (4 mi) - Job: 40 hrs          │ │
│  │ 1    │ 55 ✓  │ 65 ✓  │ 85 ✓  │  │  │ Pumps: 3  |  Available: VP:16 S:7 P:6│ │
│  │ 2    │ 58 ✓  │ 45 ⚠️ │ 90 ✓  │  │  ├──────────────────────────────────────┤ │
│  │ 3    │ 40 ⚠️ │ 75 ✓  │ 85 ✓  │  │  │ Crew D (8 mi) - Job: 60 hrs          │ │
│  └──────┴───────┴───────┴───────┘  │  │ Pumps: 4  |  Available: VP:8 S:5 P:2 │ │
│                                    │  └──────────────────────────────────────┘ │
│  SPARES: VP:0 | S:5 | P:10         │                                            │
│                                    │  TOTAL AVAILABLE NEARBY                    │
│  CALCULATED NEEDS                  │  VP: 24 | Seals: 12 | Plungers: 23         │
│  ┌────────────┬────────┬─────────┐ │                                            │
│  │ Item       │ Needed │Shortfall│ │                                            │
│  ├────────────┼────────┼─────────┤ │                                            │
│  │ Valve Pack │ 5      │ 5       │ │                                            │
│  │ Seals      │ 5      │ 0       │ │                                            │
│  │ Plungers   │ 0      │ 0       │ │                                            │
│  └────────────┴────────┴─────────┘ │                                            │
│                                    │                                            │
│      [ GENERATE ORDER PLAN ]       │                                            │
├────────────────────────────────────┴────────────────────────────────────────────┤
│                                                                                 │
│  ORDER PLAN                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │ "Pump 3 needs valve packings (40 hrs < 50 hr job). Crew C is closer but  │ │
│  │  has no surplus. Borrowing 5 from Crew B. No order needed."              │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  ┌────────────┬────────┬──────────┬─────────────────────┬─────────┬──────────┐ │
│  │ Item       │ Needed │ On Hand  │ Borrow              │ Order   │ Edit     │ │
│  ├────────────┼────────┼──────────┼─────────────────────┼─────────┼──────────┤ │
│  │ Valve Pack │ 5      │ 0        │ 5 from B            │ [0]     │ ✏️       │ │
│  │ Seals      │ 5      │ 5        │ —                   │ [0]     │ ✏️       │ │
│  │ Plungers   │ 0      │ 10       │ —                   │ [0]     │ ✏️       │ │
│  └────────────┴────────┴──────────┴─────────────────────┴─────────┴──────────┘ │
│                                                                                 │
│  Estimated Cost: $0                 [ CANCEL ]    [ APPROVE & ORDER ]           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 12. Tech Stack

| Layer | Choice |
|-------|--------|
| LLM | Ollama (local) |
| Agent Framework | LangChain + tool binding |
| Structured Output | Pydantic |
| UI | Streamlit |
| Language | Python |
| Data Generation | Python random (with seed support) |

---

## 13. Success Criteria

- [ ] User can configure simulation parameters via sliders/inputs
- [ ] User can generate new random crew data
- [ ] User can load data from file or export generated data
- [ ] System handles any number of crews (2-10)
- [ ] System handles any number of pumps per crew
- [ ] Borrow logic works with N crews (prioritizes closer, accumulates if needed)
- [ ] Agent calculates needs and explains reasoning
- [ ] UI shows all nearby crews with availability
- [ ] User can modify quantities before approval
- [ ] "Order sent" confirmation on approval
- [ ] Same seed produces same data (reproducibility)

---

## Next Step

**Phase 2: Architecture** — Define folder structure, data flow, and dependencies.
