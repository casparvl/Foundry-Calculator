# Installation Instructions

## Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

## Setup

### 1. Clone the repository (if not already done)

```bash
cd /gpfs/home4/casparl/Foundry-Calculator
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the server

```bash
cd /gpfs/home4/casparl/Foundry-Calculator
source venv/bin/activate
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### 5. Access the application

Open your web browser and navigate to:
```
http://localhost:8000
```

## Configuration Files

### `config/factories.json`

Defines factory types and their tiers. Each tier has:
- `name`: Tier name (e.g., "Tier 1", "Tier 2")
- `speed_multiplier`: Production speed multiplier
- `power_kw`: Power consumption in kilowatts at full capacity

### `config/recipes.json`

Defines recipes. Each recipe has:
- `factory_type`: Type of factory that produces this item
- `inputs`: Dictionary of input items and their per-minute consumption rates
- `outputs`: Dictionary of output items and their per-minute production rates. The primary (first) output's amount is the factory's throughput used to derive factory counts; other amounts are scaled relative to it
- `resource_type` (optional): "ore", "olumite", or "infinite" for basic resources mined from the world

### `config/robots.json`

Defines robot workstation settings:
- `workstation_levels`: Map of workstation level to its effective multiplier (1 → 1.0, 2 → 2.0, 3 → 4.0). The multiplier scales both the robot's buff percentage and its power increase.
- `machine_aliases`: Map of in-game machine groups (e.g. "Miner", "Chemical Building") to the factory types defined in `factories.json`. Robots reference machine groups through their `affected_machines`.
- `robots`: Each robot has:
  - `robot_type`: Robot family (Aquatic, Bot, Drone, Robot)
  - `affected_machines`: List of machine groups it boosts (must exist in `machine_aliases`)
  - `buff_type`: "speed" (raises effective production rate) or "efficiency" (reduces input consumption)
  - `buff_percentage`: Buff as a decimal (e.g. 0.25 for +25%)
  - `power_increase_percentage`: Additional power draw as a decimal (e.g. 0.15 for +15%)

## Running Tests

### Unit Tests

```bash
pytest tests/test_calculator.py -v
```

### Integration Tests (API)

```bash
pytest tests/test_api.py -v
```

### All Tests

```bash
pytest -v
```

## Usage Examples

### Basic Calculation

1. Open the application in your browser
2. Click "+ Add Output"
3. Select an item from the dropdown
4. Enter the desired rate per minute
5. Click "Calculate"
6. View the results in Table View or Graph View

### Advanced Configuration

**Global Settings:**
- Select factory tiers for each factory type
- Select a robot workstation level (I, II, or III) — a higher level multiplies both the robot buff and its power increase
- Pick a robot for each factory type (options are filtered to robots that affect that factory; "None" disables buffs). Defaults are the highest-efficiency robots per factory
- Set research efficiency for ore and olumite

**Recipe Overrides:**
- Override tier selection for individual recipes
- Override the robot for specific recipes (or explicitly set "None" to disable the global robot for that recipe)

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.104.1 | Web framework |
| uvicorn | 0.24.0 | ASGI server |
| pydantic | 2.5.0 | Data validation |
| jinja2 | 3.1.2 | Template engine |
| pytest | 7.4.3 | Testing framework |
| httpx | 0.25.2 | HTTP client for testing |

## Notes

- All calculations are fractional (no rounding)
- Power consumption is proportional to actual factory utilization
- Robot buffs (speed/efficiency) and power increases are scaled by the workstation level multiplier
- Basic resources (ores, olumite) have research efficiency applied to world consumption
