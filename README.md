# Frac Consumables Planner

A LangChain agent-based application for planning pump consumable orders for fracturing crews.

## Overview

This application helps Crew A plan their consumable orders by:
1. Analyzing pump remaining life vs job duration
2. Checking available spares on hand
3. Finding borrowing opportunities from nearby crews
4. Generating an optimized order plan

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure Ollama is running
ollama pull llama3

# Run the application
streamlit run ui/app.py
```

## Project Structure

```
/frac-consumables-planner
├── /data              # Crew data and example scenarios
├── /schemas           # Pydantic data models
├── /generator         # Random data generation
├── /tools             # LangChain agent tools
├── /agent             # Agent orchestration
├── /prompts           # System prompts
├── /ui                # Streamlit UI
├── CLAUDE.md          # Project conventions
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

## Requirements

- Python 3.10+
- Ollama with llama3 model

## Documentation

See [CLAUDE.md](CLAUDE.md) for project conventions and development guidelines.
