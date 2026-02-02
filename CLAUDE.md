# CLAUDE.md - Project Conventions

## Project Overview

Frac Consumables Planner - A LangChain agent-based application for planning pump consumable orders for fracturing crews.

## Architecture

```
/frac-consumables-planner
├── /data              # JSON data files (crews, scenarios)
├── /schemas           # Pydantic models
├── /generator         # Random data generation
├── /tools             # LangChain tools
├── /agent             # Agent orchestration
├── /prompts           # System prompts
└── /ui                # Streamlit application
```

## Key Conventions

### Pydantic Models

- All data structures use Pydantic v2 BaseModel
- Schemas live in `/schemas/` directory
- Use `Field()` with descriptions for all fields
- Validate ranges with `ge`, `le`, `gt`, `lt` constraints

```python
from pydantic import BaseModel, Field

class Example(BaseModel):
    value: int = Field(default=10, ge=1, le=100, description="Example value")
```

### Prompts

- All prompts live in `/prompts/prompts.py`
- Use constants for prompt strings (e.g., `SYSTEM_PROMPT`)
- Keep prompts as multi-line strings for readability

### LangChain Tools

- Tools are decorated with `@tool` from langchain
- Each tool has a clear docstring explaining inputs/outputs
- Tools should be stateless - receive all needed data as parameters

### Data Flow

1. `SimulationConfig` → `generate_crew_data()` → `CrewData`
2. `CrewData` → Agent Tools → `OrderPlan`
3. `OrderPlan` → Streamlit UI → User

### Naming Conventions

- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

### Type Hints

- Use type hints for all function signatures
- Use `list[Type]` instead of `List[Type]` (Python 3.10+)
- Use `dict[K, V]` instead of `Dict[K, V]`
- Use `X | None` instead of `Optional[X]`

## Dependencies

- **langchain** + **langchain-ollama**: Agent framework with local LLM
- **pydantic**: Data validation and schemas
- **streamlit**: Web UI
- **python-dotenv**: Environment configuration

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure Ollama is running with llama3
ollama pull llama3

# Run Streamlit app
streamlit run ui/app.py
```

## Testing

- Example scenarios in `/data/examples/` for testing various cases
- Use `seed` parameter in SimulationConfig for reproducible tests
