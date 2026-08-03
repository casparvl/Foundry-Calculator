# Foundry Calculator - Implementation Plan

## Overview

Build a web-based resource calculator for the Foundry automation game that calculates production chains, resource requirements, and factory needs based on user-defined output targets.

---

## Tech Stack

- **Backend:** Python 3 + FastAPI
- **Frontend:** HTML5 + Vanilla JavaScript + Bootstrap 5
- **Graph Visualization:** vis.js
- **Configuration:** JSON files
- **Testing:** pytest + httpx

---

## Data Models

### Item Types (Inferred)
- **Basic - Ore:** Consumed from world, affected by ore research efficiency
- **Basic - Olumite:** Liquid resource, consumed from world, affected by olumite research efficiency
- **Intermediate/Finished:** Items produced from other items (no fundamental distinction)

### Modifier Types (Independent)
- **Speed Modifier:** Increases production rate proportionally
- **Efficiency Modifier:** Reduces input requirements (recipes) or world consumption (miners)
- **Energy Modifier:** Changes power consumption of factories

---

## Configuration Files

### `config/factories.json`
```json
{
  "FactoryName": {
    "tiers": [
      {
        "name": "Tier 1",
        "speed_multiplier": 1.0,
        "power_kw": 550
      },
      {
        "name": "Tier 2",
        "speed_multiplier": 2.0,
        "power_kw": 1100
      }
    ]
  }
}
```

### `config/recipes.json`
```json
{
  "ItemName": {
    "factory_type": "FactoryName",
    "factory_tier": "Tier 1",
    "inputs": {"ItemA": 5, "ItemB": 10},
    "outputs": {"ItemName": 2},
    "base_rate_per_min": 10,
    "resource_type": "ore" // Optional: "ore" or "olumite" for basic resources
  }
}
```

**Key Design Decisions:**
- Recipes are the source of truth (contains factory_type)
- Factory definitions only contain tier information (no recipe duplication)
- `resource_type` field signals basic resources consumed from world

---

## Core Calculation Engine

### Algorithm Flow

1. **Build Production Graph (Bottom-Up)**
   - For each requested output item:
     - Find its recipe
     - Calculate required factory count
     - Recursively process all inputs
     - Aggregate shared inputs (sum if same item needed by multiple recipes)

2. **Calculate World Consumption**
   - For items with `resource_type` in miner recipes:
     - Apply research efficiency modifier
     - Calculate: `world_consumption = calculated_rate / (1 + research_efficiency)`

3. **Calculate Power**
   - For each (factory, recipe) pair:
     - `power = factory_count × tier_power_kw × energy_modifier`
   - Sum total, track per-factory-type breakdown

### Key Formulas

| Concept | Formula | Notes |
|---------|---------|-------|
| **Factory Count** | `requested_rate / effective_rate` | Fractional, no rounding |
| **Effective Rate** | `base_rate × tier_speed × (1 + speed_modifier)` | Speed affects rate only |
| **Input Rate** | `output_rate × (input/output_ratio) / (1 + efficiency_modifier)` | Based on actual output |
| **World Consumption** | `calculated_rate / (1 + research_efficiency)` | For basic resources only |
| **Power** | `factories_needed × tier_power_kw` | Proportional to fractional factories |
| **Modifiers** | Independent | Speed and efficiency don't interact |

### Display Strategy
- Show fractional factory counts (e.g., "1.67 factories")
- Show precise rates (2 decimal places)
- No rounding anywhere

---

## API Design

### Endpoints

```
GET  /api/factories
  → Returns all factory definitions with tiers

GET  /api/recipes
  → Returns all recipe definitions

POST /api/calculate
  → Main calculation endpoint
  Body:
  {
    "outputs": [{"item": "ItemA", "rate": 20}],
    "global_tiers": {"Assembler": "Tier 2"},
    "recipe_overrides": {
      "ItemA": {"tier": "Tier 1", "modifiers": {"speed": 0.10, "efficiency": 0.20, "energy": 1.0}}
    },
    "global_modifiers": {
      "Assembler": {"speed": 0.0, "efficiency": 0.20, "energy": 1.0}
    },
    "research_efficiency": {"ore": 0.10, "olumite": 0.0}
  }
  
GET  /api/calculate/{id}
  → Retrieve cached calculation result

DELETE /api/calculate/{id}
  → Clear cached calculation
```

---

## Frontend Views

### Main Interface (`templates/index.html`)

**Section 1: Configuration Panel**
- **Desired Outputs:** Dynamic list with "Add Item" button
  - Dropdown to select item (populated from /api/recipes)
  - Input field for rate per minute
  - Delete button for each row

- **Global Settings:** Collapsible accordion
  - Factory tier dropdowns (one per factory type)
  - Global modifier inputs (speed, efficiency, energy) per factory type

- **Recipe Overrides:** Collapsible accordion
  - Per-recipe tier and modifier overrides
  - Toggle to enable/disable override for each recipe

**Section 2: Results Display**
- **View Toggle:** [Table View] | [Graph View]

- **Table View:**
  - Expandable rows showing production chain
  - Each row: Item → Factory → Inputs → Outputs → Power
  - Summary section: Total resources, total power

- **Graph View:**
  - Nodes: Production stages (items)
  - Edges: Flow rates between stages
  - Color coding: Basic (green), Intermediate/Finished (blue)
  - Hover tooltips with detailed numbers

**Section 3: Summary Panel**
- Total power consumption (kW)
- Total raw resource requirements (per minute)
- World consumption rates (with research efficiency applied)
- Factory counts by type

---

## File Structure

```
Foundry-Calculator/
├── config/
│   ├── factories.json
│   └── recipes.json
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, routes
│   ├── models.py            # Pydantic models
│   ├── calculator.py        # Core calculation engine
│   └── utils.py             # Helpers (caching, formatting)
├── templates/
│   └── index.html           # Main UI
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── app.js           # Main frontend logic
│       ├── calculator.js    # API calls, data processing
│       └── graph.js         # vis.js graph rendering
├── tests/
│   ├── __init__.py
│   ├── test_calculator.py   # Unit tests
│   └── test_api.py          # Integration tests
├── requirements.txt
├── INSTALLATION.md
└── README.md
```

---

## Implementation Phases

### Phase 1: Foundation
1. Set up project structure
2. Define Pydantic data models
3. Create sample config files (abstract items)
4. Implement basic calculation engine (no modifiers yet)

### Phase 2: Core Logic
5. Add modifier support (speed, efficiency, energy)
6. Implement research efficiency for basic resources
7. Add power calculation
8. Write unit tests for calculation engine

### Phase 3: API
9. Implement FastAPI endpoints
10. Add caching for calculations
11. Write API integration tests
12. Verify example from FIRST_PROMPT.md matches expected output

### Phase 4: Frontend
13. Build HTML forms and layouts
14. Implement API integration
15. Build table view with expandable rows
16. Add graph visualization with vis.js
17. Polish UI/UX

### Phase 5: Documentation
18. Write INSTALLATION.md
19. Add example configurations
20. Final testing and cleanup

---

## Testing Strategy

### Unit Tests (`tests/test_calculator.py`)
- Test factory count calculations (fractional)
- Test modifier applications (speed, efficiency, energy - independent)
- Test research efficiency on basic resources
- Test aggregation of shared inputs
- Test power calculations (proportional)

### Integration Tests (`tests/test_api.py`)
- Test /api/factories endpoint
- Test /api/recipes endpoint
- Test /api/calculate endpoint with various inputs
- Test /api/calculate/{id} retrieval
- Verify FIRST_PROMPT.md example produces expected output

---

## Example from FIRST_PROMPT.md

**Inputs:**
- Request: 20/min ItemA
- Recipe A: 5×B + 10×C → 2×A, base rate 10/min in Assembler
- Recipe B: 5×C + 2×D → 5×B, base rate 10/min in Assembler
- Assembler tiers: Tier 1 (550kW), Tier 2 (1100kW, 2× speed)
- Global modifier: Assembler efficiency +20%
- Research efficiency: ore +10%

**Expected Output:**
- To produce 20/min ItemA: 2 Assemblers (Tier 1), inputs: (50/1.2)×B/min + (100/1.2)×C/min
- To produce (100/1.2)/min ItemB: (100/1.2)/50 Assemblers, inputs: ((100/1.2)/1.2)×C/min + ((2/5)×(100/1.2)/1.2)×D/min
- Raw resources: C and D as basic, with research efficiency applied to world consumption

---

## Key Design Decisions

1. **No rounding:** All calculations remain fractional throughout
2. **Independent modifiers:** Speed and efficiency don't interact
3. **Proportional power:** Idle time doesn't consume power
4. **Recipes as source of truth:** Factory type stored in recipes, not factories
5. **Inferred item types:** Basic resources identified by `resource_type` field, not hardcoded categories

---

## Clarifications Made

1. **Tech Stack:** Python + FastAPI + HTML/JS + vis.js
2. **Config Files:** `config/factories.json` and `config/recipes.json`
3. **Calculations:** Fractional factories, proportional power, independent modifiers
4. **Display:** No rounding, show precise values
5. **Item Types:** No distinction between intermediate/finished products
6. **Power Consumption:** `factories_needed × tier_power_kw` (proportional)
7. **Modifiers:** Speed and efficiency are completely independent

---

## Next Steps

1. Confirm final plan is correct
2. Begin implementation (Phase 1: Foundation)
