# Phase 1 Output: Frac Consumables Planner

## 1. Problem Statement

Fracturing crews shut down mid-job because they run out of consumables (valve packings, seals, valves). Shutdowns are expensive — idle equipment, delayed production. Crews also over-order because they can't see what's available nearby, tying up capital in redundant inventory.

**One sentence:** This tool prevents costly mid-job shutdowns by calculating consumable needs proactively and leveraging surplus from nearby crews to minimize ordering.

---

## 2. User

**Team Lead (Crew A)** — responsible for planning the frac job and ensuring no shutdown due to missing parts.

---

## 3. Today's Pain

- Estimates parts needed from gut feel
- Calls other crew leads manually to check inventory
- Over-orders "just in case," tying up capital
- Discovers shortage mid-job → shutdown, scramble, delays

---

## 4. MVP Scope

An agentic workflow that:
1. Calculates consumable needs based on job parameters and remaining life
2. Reads nearby crew surplus inventory
3. Computes what to borrow vs. order
4. Presents recommendation with explanation
5. Allows user to modify quantities
6. Submits order on approval (mock confirmation)

**In scope:**
- 3 consumables: valve packings, seals, valves
- Static dataset for Crews A, B, C
- Remaining life in hours (average per crew)
- LangChain agent with tool binding
- Ollama (local LLM)
- Single-page Streamlit UI
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
| **Needs Calculator** | Tool | `(pumps × 5) = qty needed per consumable` |
| **Inventory Reader** | Tool | Read Crews A, B, C inventory and surplus from static data |
| **Order Planner** | Tool | `qty needed - on hand (if life sufficient) - borrow = order qty` |
| **Orchestrator Agent** | LangChain Agent | Chains tools, determines if order needed, explains reasoning |
| **Streamlit UI** | UI | Single page: job plan, nearby inventory, order form |

---

## 6. Data Flow

```
User inputs job params (pumps, hours)
              ↓
     [Orchestrator Agent]
              ↓
    ┌─────────┼─────────┐
    ↓         ↓         ↓
[Needs    [Inventory  [Order
Calculator] Reader]   Planner]
    ↓         ↓         ↓
    └─────────┴─────────┘
              ↓
   Agent returns recommendation
              ↓
   Streamlit displays order form
              ↓
   User modifies / approves
              ↓
   "Order sent" confirmation
```

---

## 7. Inputs

### Static Dataset

| Crew | Pumps | Distance | Valve Packings | Seals | Valves |
|------|-------|----------|----------------|-------|--------|
| A | 12 | — | 10 qty / 50 hrs life | 15 qty / 60 hrs | 8 qty / 40 hrs |
| B | 8 | 3 mi | 20 qty / 150 hrs (10 surplus) | 25 qty / 200 hrs (15 surplus) | 12 qty / 180 hrs (6 surplus) |
| C | 6 | 4 mi | 12 qty / 180 hrs (5 surplus) | 10 qty / 160 hrs (5 surplus) | 8 qty / 150 hrs (3 surplus) |

### User Input

- Crew A pump count: 12
- Planned job duration: 200 hours

### Calculation Rules

- Each pump needs 5 of each consumable
- Total needed = pumps × 5
- Item is usable only if remaining life ≥ job duration
- Borrow from nearby crews (within 5 mi) before ordering

---

## 8. Outputs

### Agent Recommendation (natural language)

> "Based on your 200-hour job with 12 pumps, you need 60 of each consumable. Your current inventory has insufficient remaining life. Borrowing 15 valve packings, 20 seals, 9 valves from nearby crews. Ordering the remainder."

### Order Plan (structured)

| Item | Needed | Borrow | Order |
|------|--------|--------|-------|
| Valve Packings | 60 | 15 (10 B + 5 C) | 45 |
| Seals | 60 | 20 (15 B + 5 C) | 40 |
| Valves | 60 | 9 (6 B + 3 C) | 51 |

### On Approval

"Order sent" confirmation message

---

## 9. UI Layout (Single Page)

| Section | Position | Content |
|---------|----------|---------|
| Crew A Job Plan | Top left | Pump count, duration, current inventory, remaining life, calculated needs |
| Nearby Crews | Top right | Crews B & C: inventory, remaining life, surplus |
| Order Plan | Bottom | Agent explanation, editable order table, Approve & Order button |

### Wireframe

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  FRAC CONSUMABLES PLANNER                                                       │
├────────────────────────────────────┬────────────────────────────────────────────┤
│                                    │                                            │
│  CREW A - JOB PLAN                 │  NEARBY CREWS (within 5 mi)                │
│  ┌──────────────────────────────┐  │  ┌────────────────────────────────────┐   │
│  │ Pumps:     [12]              │  │  │ CREW B (3 mi) - 8 pumps            │   │
│  │ Duration:  [200] hrs         │  │  │ ┌────────────┬─────┬─────┬───────┐ │   │
│  │ Start:     Feb 5             │  │  │ │ Item       │ Qty │ Life│Surplus│ │   │
│  └──────────────────────────────┘  │  │ ├────────────┼─────┼─────┼───────┤ │   │
│                                    │  │ │ Valve Pack │ 20  │ 150 │ 10    │ │   │
│  CURRENT INVENTORY                 │  │ │ Seals      │ 25  │ 200 │ 15    │ │   │
│  ┌────────────┬─────┬─────┬─────┐  │  │ │ Valves     │ 12  │ 180 │ 6     │ │   │
│  │ Item       │ Qty │ Life│Status│  │  │ └────────────┴─────┴─────┴───────┘ │   │
│  ├────────────┼─────┼─────┼─────┤  │  │                                    │   │
│  │ Valve Pack │ 10  │ 50  │ ⚠️   │  │  │ CREW C (4 mi) - 6 pumps            │   │
│  │ Seals      │ 15  │ 60  │ ⚠️   │  │  │ ┌────────────┬─────┬─────┬───────┐ │   │
│  │ Valves     │ 8   │ 40  │ ⚠️   │  │  │ │ Item       │ Qty │ Life│Surplus│ │   │
│  └────────────┴─────┴─────┴─────┘  │  │ ├────────────┼─────┼─────┼───────┤ │   │
│                                    │  │ │ Valve Pack │ 12  │ 180 │ 5     │ │   │
│  CALCULATED NEEDS                  │  │ │ Seals      │ 10  │ 160 │ 5     │ │   │
│  ┌────────────┬────────┬─────────┐ │  │ │ Valves     │ 8   │ 150 │ 3     │ │   │
│  │ Item       │ Needed │Shortfall│ │  │ └────────────┴─────┴─────┴───────┘ │   │
│  ├────────────┼────────┼─────────┤ │  │                                    │   │
│  │ Valve Pack │ 60     │ 60      │ │  │ TOTAL SURPLUS                      │   │
│  │ Seals      │ 60     │ 60      │ │  │ Valve Pack: 15 | Seals: 20 | Valves: 9│
│  │ Valves     │ 60     │ 60      │ │  └────────────────────────────────────┘   │
│  └────────────┴────────┴─────────┘ │                                            │
│                                    │                                            │
│      [ GENERATE ORDER PLAN ]       │                                            │
├────────────────────────────────────┴────────────────────────────────────────────┤
│                                                                                 │
│  ORDER PLAN                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │ "Based on your 200-hour job with 12 pumps, you need 60 of each. Your     │ │
│  │  current inventory is insufficient. Borrowing 15 valve packings, 20       │ │
│  │  seals, 9 valves from nearby crews. Ordering the remainder."              │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  ┌────────────┬────────┬─────────────────────┬─────────┬──────────┐           │
│  │ Item       │ Needed │ Borrow              │ Order   │ Edit     │           │
│  ├────────────┼────────┼─────────────────────┼─────────┼──────────┤           │
│  │ Valve Pack │ 60     │ 10 (B) + 5 (C)      │ [45]    │ ✏️       │           │
│  │ Seals      │ 60     │ 15 (B) + 5 (C)      │ [40]    │ ✏️       │           │
│  │ Valves     │ 60     │ 6 (B) + 3 (C)       │ [51]    │ ✏️       │           │
│  └────────────┴────────┴─────────────────────┴─────────┴──────────┘           │
│                                                                                 │
│  Estimated Cost: $12,450                [ CANCEL ]    [ APPROVE & ORDER ]       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Tech Stack

| Layer | Choice |
|-------|--------|
| LLM | Ollama (local) |
| Agent Framework | LangChain + tool binding |
| Structured Output | Pydantic |
| UI | Streamlit |
| Language | Python |

---

## 11. Success Criteria

- [ ] User inputs job duration and pump count
- [ ] Agent calculates needs, checks nearby inventory, computes order
- [ ] Agent explains reasoning in natural language
- [ ] UI shows editable order form
- [ ] User can modify quantities before approval
- [ ] "Order sent" confirmation on approval
- [ ] Total time from input to order: < 60 seconds

---

## Next Step

**Phase 2: Architecture** — Define folder structure, data flow, and dependencies.
