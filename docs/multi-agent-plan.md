# Multi-Agent System Plan: Transfer Coordinator & Cost Analyzer

## Overview
Building two new agents with proper dependencies:
1. **Transfer Coordinator Agent** - Plans routes with weather-adjusted travel times
2. **Cost Analyzer Agent** - Calculates costs based on transfer plan

---

# PHASE 1: Updated Folder Structure

## Current Structure
```
/frac-consumables-planner
├── /agent
│   └── orchestrator.py          # Order Planning Agent
├── /data
│   └── /examples
│       ├── scenario_3crews.json
│       └── scenario_5crews.json
├── /generator
│   └── data_generator.py
├── /prompts
│   ├── prompts.py               # Order agent prompts
│   └── chatbot_prompts.py
├── /schemas
│   ├── config.py
│   ├── crew.py
│   ├── order.py
│   └── chatbot_response.py
├── /tools
│   ├── needs_calculator.py
│   ├── inventory_reader.py
│   └── order_planner.py
└── /ui
    ├── app.py
    ├── chatbot.py
    └── /components
```

## New Structure (additions marked with NEW)
```
/frac-consumables-planner
├── /agent
│   ├── orchestrator.py              # Order Planning Agent
│   ├── transfer_coordinator.py      # NEW - Transfer Coordinator Agent
│   └── cost_analyzer.py             # NEW - Cost Analyzer Agent
├── /data
│   └── /examples
│       ├── scenario_3crews.json     # Updated with weather
│       ├── scenario_5crews.json     # Updated with weather
│       └── cost_config.json         # NEW - Pricing configuration
├── /generator
│   ├── data_generator.py            # Updated for weather
│   └── weather_generator.py         # NEW - Weather simulation
├── /prompts
│   ├── prompts.py
│   ├── chatbot_prompts.py
│   ├── transfer_prompts.py          # NEW
│   └── cost_prompts.py              # NEW
├── /schemas
│   ├── config.py
│   ├── crew.py                      # Updated with location coords
│   ├── order.py
│   ├── chatbot_response.py
│   ├── weather.py                   # NEW - Weather conditions
│   ├── transfer.py                  # NEW - Transfer/route plans
│   └── cost.py                      # NEW - Cost breakdowns
├── /tools
│   ├── needs_calculator.py
│   ├── inventory_reader.py
│   ├── order_planner.py
│   ├── weather_checker.py           # NEW - Get weather data
│   ├── route_planner.py             # NEW - Plan transfer routes
│   └── cost_calculator.py           # NEW - Calculate costs
└── /ui
    ├── app.py                       # Add new tabs
    ├── chatbot.py
    └── /components
        ├── pump_status.py
        ├── chatbot_ui.py
        ├── transfer_ui.py           # NEW - Transfer planning UI
        └── cost_ui.py               # NEW - Cost analysis UI
```

---

# PHASE 2: Mock Data Plan

## 2.1 Weather Mock Data

**Source:** Simulated based on location/area

**Schema:** Add to crew data
```json
{
  "crew_id": "A",
  "area": "Permian Basin",
  "weather": {
    "condition": "clear",
    "temperature_f": 75,
    "wind_mph": 10,
    "visibility_miles": 10
  }
}
```

**Weather Conditions & Multipliers:**
| Condition | Multiplier | Description |
|-----------|------------|-------------|
| clear | 1.0 | Normal driving |
| cloudy | 1.1 | Slightly cautious |
| rain | 1.3 | Slower speeds |
| heavy_rain | 1.6 | Much slower |
| storm | 2.0 | Hazardous |
| fog | 1.4 | Low visibility |

**Generator:** `weather_generator.py`
- Random weather per area
- Can be seeded for reproducibility
- Option to set specific weather for testing

## 2.2 Route/Distance Mock Data

**Current:** Already have `distance_to_crew_a` field

**Enhancement:** Add lat/long coordinates for realistic routing
```json
{
  "crew_id": "B",
  "coordinates": {
    "lat": 31.9973,
    "lng": -102.0779
  },
  "distance_to_crew_a": 4.0
}
```

## 2.3 Cost Mock Data

**File:** `data/examples/cost_config.json`
```json
{
  "travel": {
    "cost_per_mile": 2.50,
    "cost_per_hour_labor": 75.00,
    "average_speed_mph": 30
  },
  "consumables": {
    "valve_packings": {
      "unit_price": 150.00,
      "supplier_lead_time_days": 2
    },
    "seals": {
      "unit_price": 85.00,
      "supplier_lead_time_days": 1
    },
    "plungers": {
      "unit_price": 250.00,
      "supplier_lead_time_days": 3
    }
  },
  "shipping": {
    "base_cost": 50.00,
    "per_unit_cost": 5.00,
    "expedited_multiplier": 2.0
  }
}
```

## 2.4 Updated Scenario File Example

**File:** `data/examples/scenario_3crews_with_weather.json`
```json
{
  "consumables_per_pump": 1,
  "weather_data": {
    "A": {"condition": "clear", "multiplier": 1.0},
    "B": {"condition": "rain", "multiplier": 1.3},
    "C": {"condition": "clear", "multiplier": 1.0}
  },
  "crews": [
    {
      "crew_id": "A",
      "coordinates": {"lat": 31.9686, "lng": -102.0779},
      "area": "Permian Basin",
      "job_duration_hours": 50,
      "..."
    }
  ]
}
```

---

# PHASE 3: End-to-End Simulation Walkthrough

## Scenario: Crew A needs 5 Valve Packings

### Step 1: Order Planning Agent (Existing)
**Input:** Crew data with needs
**Output:**
```
OrderPlan:
- Valve Packings: Need 5, Have 0, Borrow 5 from Crew B
- Seals: Need 5, Have 5, No action
- Plungers: Need 0, No action
```

### Step 2: Transfer Coordinator Agent (NEW)
**Input:** OrderPlan + Weather Data
**Process:**
1. Check weather at Crew A (clear, 1.0x)
2. Check weather at Crew B (rain, 1.3x)
3. Calculate route: A → B → A
4. Base distance: 4.0 miles each way = 8.0 miles total
5. Base time: 8.0 miles / 30 mph = 0.27 hours
6. Weather adjustment: Average multiplier = (1.0 + 1.3) / 2 = 1.15
7. Adjusted time: 0.27 × 1.15 = 0.31 hours (18.6 minutes)

**Output:**
```
TransferPlan:
- Route: Crew A → Crew B → Crew A
- Distance: 8.0 miles
- Base time: 16 minutes
- Weather delay: +3 minutes (rain at Crew B)
- Adjusted time: 19 minutes
- Pickup manifest:
  - Crew B: 5 Valve Packings
```

### Step 3: Cost Analyzer Agent (NEW)
**Input:** TransferPlan + OrderPlan + CostConfig
**Process:**
1. Calculate borrow cost:
   - Travel: 8.0 miles × $2.50 = $20.00
   - Labor: 0.31 hours × $75.00 = $23.25
   - Total borrow: $43.25

2. Calculate order cost (alternative):
   - 5 VP × $150.00 = $750.00
   - Shipping: $50.00 + (5 × $5.00) = $75.00
   - Total order: $825.00

3. Compare:
   - Borrow: $43.25
   - Order: $825.00
   - Savings: $781.75 (94.8%)

**Output:**
```
CostBreakdown:
- Borrow option: $43.25
  - Travel: $20.00
  - Labor: $23.25
- Order option: $825.00
  - Parts: $750.00
  - Shipping: $75.00
- Recommendation: BORROW (saves $781.75)
```

### Step 4: Final Summary to User
```
RECOMMENDATION SUMMARY
═══════════════════════════════════════
Order Plan: Borrow 5 Valve Packings from Crew B

Transfer Details:
- Route: Your location → Crew B → Return
- Distance: 8.0 miles round trip
- Weather: Rain at Crew B (allow extra time)
- Estimated time: 19 minutes

Cost Analysis:
- Borrowing cost: $43.25
- Ordering cost: $825.00
- You save: $781.75 by borrowing

Action Items:
1. Contact Crew B to confirm availability
2. Allow extra travel time due to rain
3. Pickup: 5 Valve Packings
═══════════════════════════════════════
```

---

# PHASE 4: Implementation Checklist

## 4.1 Data Layer (Do First)
- [ ] Create `schemas/weather.py`
- [ ] Create `schemas/transfer.py`
- [ ] Create `schemas/cost.py`
- [ ] Update `schemas/crew.py` with coordinates
- [ ] Create `data/examples/cost_config.json`
- [ ] Create `generator/weather_generator.py`
- [ ] Update scenario files with weather

## 4.2 Transfer Coordinator Agent
- [ ] Create `tools/weather_checker.py`
- [ ] Create `tools/route_planner.py`
- [ ] Create `prompts/transfer_prompts.py`
- [ ] Create `agent/transfer_coordinator.py`
- [ ] Create `ui/components/transfer_ui.py`

## 4.3 Cost Analyzer Agent
- [ ] Create `tools/cost_calculator.py`
- [ ] Create `prompts/cost_prompts.py`
- [ ] Create `agent/cost_analyzer.py`
- [ ] Create `ui/components/cost_ui.py`

## 4.4 Integration
- [ ] Update `ui/app.py` with new tabs
- [ ] Update chatbot to include cost/transfer info
- [ ] End-to-end testing with mock data

---

# Agent Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                               │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │  Pump    │  │    Job       │  │  Transfer   │  │    Cost      │  │
│  │  Status  │  │  Planning    │  │  Planning   │  │  Analysis    │  │
│  └──────────┘  └──────────────┘  └─────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AGENT LAYER                                  │
│                                                                      │
│  ┌─────────────────┐    ┌─────────────────────┐    ┌──────────────┐ │
│  │ Order Planning  │───▶│ Transfer Coordinator│───▶│ Cost Analyzer│ │
│  │     Agent       │    │       Agent         │    │    Agent     │ │
│  └─────────────────┘    └─────────────────────┘    └──────────────┘ │
│         │                        │                        │         │
│         ▼                        ▼                        ▼         │
│  ┌─────────────┐         ┌─────────────┐          ┌─────────────┐  │
│  │ • calc_needs│         │ • check_    │          │ • calc_     │  │
│  │ • read_inv  │         │   weather   │          │   borrow    │  │
│  │ • plan_order│         │ • plan_route│          │ • calc_order│  │
│  └─────────────┘         └─────────────┘          │ • compare   │  │
│      TOOLS                    TOOLS               └─────────────┘  │
│                                                        TOOLS        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                   │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │  Crew    │  │  Weather │  │ Transfer │  │   Cost   │            │
│  │  Data    │  │   Data   │  │   Plan   │  │  Config  │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

# Data Flow

```
User Request: "Plan order for Crew A"
         │
         ▼
┌─────────────────────────────────────┐
│      ORDER PLANNING AGENT           │
│  Input: CrewData                    │
│  Output: OrderPlan                  │
│    - What to borrow                 │
│    - What to order                  │
│    - From which crews               │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│    TRANSFER COORDINATOR AGENT       │
│  Input: OrderPlan + WeatherData     │
│  Output: TransferPlan               │
│    - Optimal route                  │
│    - Weather-adjusted times         │
│    - Pickup manifest                │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│       COST ANALYZER AGENT           │
│  Input: TransferPlan + CostConfig   │
│  Output: CostBreakdown              │
│    - Borrow cost                    │
│    - Order cost                     │
│    - Recommendation                 │
└─────────────────────────────────────┘
         │
         ▼
    Final Recommendation
```
