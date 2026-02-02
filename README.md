# Frac Consumables Planner

An intelligent agent-based system for planning consumable orders for hydraulic fracturing crews.

## Overview

This application helps frac crews optimize consumable orders by:
- Calculating required quantities based on job parameters (pumps × hours)
- Checking available inventory across nearby crews
- Recommending borrowing from surplus inventory before ordering
- Generating cost-optimized order plans

## Features

- **Intelligent Agent**: LangChain agent with LLM reasoning (Ollama/llama3)
- **Smart Borrowing**: Automatically identifies surplus from crews within proximity threshold
- **Remaining Life Validation**: Only uses consumables with sufficient remaining life
- **Cost Optimization**: Minimizes ordering by maximizing borrowing
- **Interactive UI**: Streamlit interface with editable order forms
- **Structured Output**: Pydantic models ensure type safety throughout

## Architecture

```
Streamlit UI → Agent → Tools (calculate, read inventory, plan) → Static Data
                ↓
         OrderPlan (Pydantic)
                ↓
         Editable Order Form
```

## Project Structure

```
/frac-consumables-planner
├── /data               # Static crew inventory data
├── /schemas            # Pydantic models for data validation
├── /tools              # LangChain tools for agent
├── /agent              # Agent orchestrator
├── /prompts            # System prompts and templates
├── /ui                 # Streamlit application
├── CLAUDE.md           # Development conventions
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## Prerequisites

1. **Python 3.10+**
2. **Ollama** installed and running
   - Install from [ollama.com](https://ollama.com)
   - Pull the llama3 model: `ollama pull llama3`

## Installation

```bash
# Clone the repository
cd frac-consumables-planner

# Install dependencies
pip install -r requirements.txt

# Verify Ollama is running
ollama list  # Should show llama3 model
```

## Usage

```bash
# Run the Streamlit app
streamlit run ui/app.py
```

The app will open in your browser at `http://localhost:8501`

### Workflow

1. **Enter Job Parameters**
   - Number of pumps
   - Job duration in hours

2. **Review Agent Recommendation**
   - Agent calculates needs
   - Checks inventory across crews
   - Proposes borrowing strategy

3. **Edit Order if Needed**
   - Modify quantities in the order table
   - Adjust borrowing sources

4. **Approve Order**
   - Click "Approve & Order"
   - Receive confirmation

## Data Model

### Crews (data/crews.json)

```json
{
  "crew_id": "A",
  "pumps": 12,
  "distance_miles": null,
  "inventory": [
    {
      "name": "valve_packings",
      "quantity": 10,
      "remaining_life_hours": 50,
      "surplus": 0
    }
  ]
}
```

### Order Plan Output

```python
OrderPlan(
    crew_id="A",
    pump_count=12,
    job_duration_hours=200,
    items=[
        OrderLineItem(
            consumable_name="valve_packings",
            total_needed=60,
            on_hand_usable=0,
            borrow=[BorrowSource(crew_id="B", quantity=10)],
            borrow_total=10,
            to_order=50,
            unit_cost=100.0
        )
    ],
    total_order_cost=5000.0,
    recommendation="..."
)
```

## Business Logic

### Consumables Calculation
```
quantity_needed = (pumps × hours) / consumables_per_pump
```

### Borrowing Rules
- Only from crews within `proximity_threshold_miles` (default: 5 miles)
- Only from `surplus` inventory
- Prioritize closer crews

### Remaining Life Validation
- Consumable must have `remaining_life_hours > job_duration_hours`
- Otherwise, excluded from usable inventory

## Development

See [CLAUDE.md](CLAUDE.md) for development conventions and patterns.

### Phase Status

- ✅ Phase 1: Requirements gathering
- ✅ Phase 2: Architecture design
- ✅ Phase 3: Skeleton creation
- ⏳ Phase 4: Implementation (upcoming)
- ⏳ Phase 5: Testing and refinement

## Contributing

This is a prototype project for internal use. Follow conventions in CLAUDE.md.

## License

Internal use only.

## Contact

For questions or issues, contact the development team.
