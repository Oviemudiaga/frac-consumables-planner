# Project Conventions

This document outlines the development conventions for the Frac Consumables Planner project.

## Architecture Principles

1. **Separation of Concerns**
   - `/schemas`: Data models only (no business logic)
   - `/tools`: LangChain tools (focused, single-purpose functions)
   - `/agent`: Agent orchestration and coordination
   - `/prompts`: All prompt text in one place
   - `/ui`: Presentation layer only
   - `/data`: Static data files

2. **Data Flow Direction**
   ```
   UI → Agent → Tools → Data
   Data → Tools → Agent → UI
   ```
   - UI never calls tools directly
   - Tools never call each other
   - Agent orchestrates all tool usage

## Code Conventions

### Pydantic Models

All data structures use Pydantic v2 for validation:

```python
from pydantic import BaseModel, Field

class Example(BaseModel):
    """Always include a docstring."""
    field_name: str
    optional_field: int | None = None
    field_with_default: float = 100.0
```

**Rules:**
- Use type hints (`str`, `int`, `list[str]`, not `List[str]`)
- Use `|` for unions (Python 3.10+ syntax)
- Include docstrings for all models and fields
- Use Field() only when needed (validators, constraints, descriptions)
- Models in `/schemas` should be pure data (no methods except validators)

### LangChain Tools

Tools use the `@tool` decorator:

```python
from langchain.tools import tool

@tool
def example_tool(param: str) -> dict:
    """
    Tool description (shown to LLM).

    Args:
        param: Parameter description

    Returns:
        Return value description
    """
    # Implementation
    ...
```

**Rules:**
- One tool per file
- Tool name = function name (snake_case)
- Docstring is shown to the LLM (be clear and concise)
- Return Pydantic models when possible for type safety
- Tools should be stateless and deterministic
- Import Pydantic models from `/schemas`, not define locally

### Prompts

All prompts live in `/prompts/prompts.py`:

```python
SYSTEM_PROMPT = """
Clear instructions for the agent.
Use triple-quoted strings for readability.
"""

TEMPLATE = """
Use f-string style placeholders: {variable_name}
"""
```

**Rules:**
- Use UPPER_SNAKE_CASE for prompt constants
- Include context and decision rules clearly
- Format with triple quotes for readability
- Use `{placeholders}` for template variables
- Document what each prompt is for

### Agent Orchestrator

The agent in `/agent/orchestrator.py`:

```python
def create_agent() -> AgentExecutor:
    """Create agent with tools bound."""
    # LLM setup
    # Tool binding
    # Return configured agent
    ...

def run_planning_session(...) -> OrderPlan:
    """Execute full workflow."""
    # Invoke agent
    # Parse result
    # Return structured output
    ...
```

**Rules:**
- Keep agent configuration in `create_agent()`
- Use `run_planning_session()` as main entry point
- Always return structured Pydantic models
- Handle errors gracefully
- Log agent reasoning for debugging

### Streamlit UI

UI in `/ui/app.py`:

```python
def main():
    """Main app entry point."""
    st.set_page_config(...)

    # Sidebar for inputs
    with st.sidebar:
        ...

    # Main content
    st.title(...)
    ...

if __name__ == "__main__":
    main()
```

**Rules:**
- Single-page app (no multipage complexity yet)
- Use session state for persistence
- Call agent through `run_planning_session()` only
- Display OrderPlan results in editable form
- Clear error messages for user

## File Organization

```
/frac-consumables-planner
├── /data               # Static datasets
├── /schemas            # Pydantic models
├── /tools              # LangChain tools
├── /agent              # Agent orchestrator
├── /prompts            # Prompt templates
├── /ui                 # Streamlit app
├── CLAUDE.md           # This file
├── requirements.txt    # Dependencies
└── README.md           # User documentation
```

## Dependencies

See `requirements.txt` for full list. Key dependencies:
- **langchain**: Agent framework
- **langchain-ollama**: Ollama integration
- **pydantic**: Data validation
- **streamlit**: UI framework

## Development Workflow

1. **Phase 1**: Requirements gathering
2. **Phase 2**: Architecture design
3. **Phase 3**: Skeleton creation (current)
4. **Phase 4**: Implementation
5. **Phase 5**: Testing and refinement

## Testing Approach

- Unit tests for tools (validate calculations)
- Integration tests for agent (verify tool orchestration)
- UI tests for Streamlit (manual testing initially)

## Common Patterns

### Reading Static Data

```python
import json
from pathlib import Path

def load_crews_data():
    """Load crews from data/crews.json."""
    data_path = Path(__file__).parent.parent / "data" / "crews.json"
    with open(data_path) as f:
        return json.load(f)
```

### Returning Tool Results

```python
from schemas.order import OrderPlan

@tool
def example_tool() -> OrderPlan:
    """Return Pydantic model for type safety."""
    return OrderPlan(
        crew_id="A",
        # ... fields
    )
```

### Agent Invocation

```python
# In UI
order_plan = run_planning_session(
    pumps=12,
    hours=200,
    crew_id="A"
)

# Display results
st.write(order_plan.recommendation)
for item in order_plan.items:
    st.write(f"{item.consumable_name}: {item.to_order}")
```

## Notes for Claude

- Follow these conventions strictly
- When unsure, ask rather than improvise
- Keep functions focused and single-purpose
- Document all public APIs
- Type hints are mandatory
- Docstrings are mandatory for public functions
