# Frac Consumables Planner — Multi-Agent Architecture

> Powered by LangChain + LangGraph | ReAct Pattern | Ollama (llama3)

## System Architecture

```mermaid
flowchart TD
    subgraph UI["USER INTERFACE — Streamlit"]
        PS["Pump Status\nHealth monitoring"]
        JP["Job Planning\nGenerate order plans"]
        CHAT["Chatbot Assistant\nIntent-driven AI chat"]
        IR["Intent Router"]
        I_S["STATUS"]
        I_O["ORDER"]
        I_C["COST"]
    end

    subgraph LLM["LLM BACKBONE"]
        OLLAMA["Ollama\nllama3 - temperature 0\nLocal inference"]
    end

    subgraph A1["ORCHESTRATOR AGENT"]
        A1_T1["calculate_needs\nPumps x consumables"]
        A1_T2["read_inventory\nOn-hand + nearby spares"]
        A1_T3["plan_order\nCost-optimized borrow vs order"]
        A1_OUT(["OrderPlan"])
        A1_FB["Deterministic Fallback"]
    end

    subgraph A2["TRANSFER COORDINATOR"]
        A2_T1["check_weather\nAll crew locations"]
        A2_T2["get_route_weather\nPer-segment conditions"]
        A2_T3["plan_route\nOptimized multi-crew route"]
        A2_OUT(["TransferPlan"])
    end

    subgraph A3["COST ANALYZER"]
        A3_T1["calculate_borrow_cost\nTravel + labor costs"]
        A3_T2["calculate_order_cost\nParts + shipping costs"]
        A3_T3["compare_costs\nRecommends cheapest option"]
        A3_OUT(["CostBreakdown"])
    end

    subgraph DATA["DATA LAYER"]
        CREW["Crew Data\nJSON scenarios"]
        COSTCFG["Cost Config\nPricing rules"]
        MODELS["Pydantic Models\nType-safe schemas"]
    end

    subgraph OUTPUT["STRUCTURED OUTPUT"]
        O_ORDER["OrderPlan\nWhat to borrow and order"]
        O_TRANSFER["TransferPlan\nRoutes and timing"]
        O_COST["CostBreakdown\nSavings and recommendation"]
    end

    CHAT --> IR
    IR --> I_S
    IR --> I_O
    IR --> I_C

    JP -- "Generate Order" --> OLLAMA
    I_O --> OLLAMA
    I_C --> OLLAMA
    I_S --> OLLAMA

    OLLAMA --> A1
    OLLAMA --> A2
    OLLAMA --> A3

    A1_T1 --> A1_T2
    A1_T2 --> A1_T3
    A1_T3 --> A1_OUT
    A1_OUT --> A2
    A2_T1 --> A2_T2
    A2_T2 --> A2_T3
    A2_T3 --> A2_OUT
    A2_OUT --> A3
    A3_T1 --> A3_T2
    A3_T2 --> A3_T3
    A3_T3 --> A3_OUT

    A1 --> CREW
    A2 --> CREW
    A3 --> COSTCFG
    A1 --> COSTCFG

    A1_OUT --> O_ORDER
    A2_OUT --> O_TRANSFER
    A3_OUT --> O_COST

    style A1 fill:#2d1b1b,stroke:#e74c3c,stroke-width:2px,color:#fff
    style A2 fill:#2d2010,stroke:#e67e22,stroke-width:2px,color:#fff
    style A3 fill:#2d2800,stroke:#f39c12,stroke-width:2px,color:#fff
    style OLLAMA fill:#1565c0,color:#fff
    style LLM fill:#0d47a1,color:#fff
    style OUTPUT fill:#e8f5e9,stroke:#81c784
    style DATA fill:#eceff1,stroke:#b0bec5
```

## Agent Descriptions

| Agent | Purpose | Tools | Status |
|-------|---------|-------|--------|
| **Orchestrator** | Plans consumable orders for Crew A. Tries LLM-guided tool calls first, falls back to deterministic pipeline. | `calculate_needs`, `read_inventory`, `plan_order` | Active |
| **Transfer Coordinator** | Plans logistics routes for borrowing consumables between crews. | `check_weather`, `get_route_weather`, `plan_route` | Defined |
| **Cost Analyzer** | Compares borrow vs order costs with weather-adjusted pricing. | `calculate_borrow_cost`, `calculate_order_cost`, `compare_costs` | Defined |
| **Chatbot** | Conversational assistant with intent routing (STATUS / ORDER / COST). | Direct LLM call | Active |

## ReAct Loop

Each agent follows the ReAct (Reason + Act) pattern:

```mermaid
flowchart TD
    R["Reason\nAnalyze current state"] --> A["Act\nCall a tool"]
    A --> O["Observe\nProcess tool result"]
    O --> R
    O --> D["Done\nReturn final answer"]

    style R fill:#7c4dff,color:#fff
    style A fill:#00c853,color:#fff
    style O fill:#ff6d00,color:#fff
    style D fill:#1565c0,color:#fff
```

## Decision Flow — Cost-Optimized

```mermaid
flowchart LR
    NEED["Shortfall\ndetected"] --> CHECK{"Nearby crew\nhas spares?"}
    CHECK -- "Yes" --> COMPARE{"Borrow cost/unit\nless than\nOrder cost/unit?"}
    CHECK -- "No" --> ORDER["Order from\nsupplier"]
    COMPARE -- "Yes" --> BORROW["Borrow from\nnearby crew"]
    COMPARE -- "No" --> ORDER

    style BORROW fill:#27ae60,color:#fff
    style ORDER fill:#e74c3c,color:#fff
    style COMPARE fill:#f39c12,color:#fff
```

## Cost Formulas

### Borrow Cost
```
trip_distance  = crew_distance x 2  (round trip)
travel_cost    = trip_distance x cost_per_mile
travel_time    = trip_distance / average_speed_mph
labor_cost     = travel_time x weather_multiplier x cost_per_hour_labor
borrow_total   = travel_cost + labor_cost
cost_per_unit  = borrow_total / quantity_borrowed
```

### Order Cost
```
shipping_per_unit = (base_shipping + per_unit_cost x quantity) / quantity
cost_per_unit     = unit_price + shipping_per_unit
```

### Weather Multipliers
| Condition | Multiplier | Effect |
|-----------|-----------|--------|
| Clear | 1.0x | No impact |
| Rain | 1.3x | Moderate delay |
| Heavy Rain | 1.6x | Significant delay |
| Storm | 2.0x | Major delay |
