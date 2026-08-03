# Foundry Calculator

A resource calculator for the Foundry automation game that calculates production chains, resource requirements, and factory needs based on user-defined output targets.

## Features

- **Production Chain Solver**: Calculate all required resources for desired output rates
- **Factory Planning**: Determine how many factories of each type are needed
- **Resource Tracking**: Track raw resource consumption including world depletion rates
- **Power Calculation**: Calculate total power consumption based on actual utilization
- **Modifier Support**: Apply speed, efficiency, and energy modifiers globally or per-recipe
- **Visualization**: View results as a table or interactive graph

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the server:
   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port 8000
   ```

3. Open http://localhost:8000 in your browser

## Documentation

- [Installation Guide](INSTALLATION.md)
- [Implementation Plan](.opencode/plans/plan.md)

## Testing

```bash
pytest -v
```

## Configuration

Edit `config/factories.json` and `config/recipes.json` to define your game's factories and recipes.
