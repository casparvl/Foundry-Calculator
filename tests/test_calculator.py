"""
Unit tests for the calculator module.
"""
import pytest
from src.calculator import ProductionChainSolver

# Sample factory and recipe data for testing
SAMPLE_FACTORIES = {
    "Assembler": {
        "tiers": [
            {"name": "Tier 1", "speed_multiplier": 1.0, "power_kw": 550},
            {"name": "Tier 2", "speed_multiplier": 2.0, "power_kw": 1100}
        ]
    },
    "Miner": {
        "tiers": [
            {"name": "Tier 1", "speed_multiplier": 1.0, "power_kw": 200}
        ]
    }
}

SAMPLE_RECIPES = {
    "ItemA": {
        "factory_type": "Assembler",
        "inputs": {"ItemB": 25, "ItemC": 50},
        "outputs": {"ItemA": 10}
    },
    "ItemB": {
        "factory_type": "Assembler",
        "inputs": {"ItemC": 10, "ItemD": 4},
        "outputs": {"ItemB": 10}
    },
    "ItemC": {
        "factory_type": "Miner",
        "inputs": {"ore_from_world": 100},
        "outputs": {"ItemC": 100},
        "resource_type": "ore"
    },
    "ItemD": {
        "factory_type": "Miner",
        "inputs": {"olumite_from_world": 50},
        "outputs": {"ItemD": 50},
        "resource_type": "olumite"
    }
}

SAMPLE_ROBOTS = {
    "workstation_levels": {"1": 1.0, "2": 2.0, "3": 4.0},
    "machine_aliases": {
        "Assembler": ["Assembler"],
        "Miner": ["Miner"]
    },
    "robots": {
        "Speed Bot": {
            "robot_type": "Bot",
            "affected_machines": ["Assembler"],
            "buff_type": "speed",
            "buff_percentage": 0.5,
            "power_increase_percentage": 0.1
        },
        "Efficiency Bot": {
            "robot_type": "Bot",
            "affected_machines": ["Assembler"],
            "buff_type": "efficiency",
            "buff_percentage": 0.2,
            "power_increase_percentage": 0.1
        },
        "Miner Eff Robot": {
            "robot_type": "Robot",
            "affected_machines": ["Miner"],
            "buff_type": "efficiency",
            "buff_percentage": 0.3,
            "power_increase_percentage": 0.2
        }
    }
}


@pytest.fixture
def solver():
    return ProductionChainSolver(SAMPLE_FACTORIES, SAMPLE_RECIPES, SAMPLE_ROBOTS)


class TestFactoryCount:
    """Test factory count calculations (should be fractional)."""
    
    def test_simple_factory_count(self, solver):
        """Test basic factory count calculation without modifiers."""
        from src.models import CalculationRequest
        
        request = CalculationRequest(
            outputs=[{"item": "ItemA", "rate": 20}],
            global_tiers={"Assembler": "Tier 1"},
            research_efficiency={"ore": 0.0, "olumite": 0.0}
        )
        
        result = solver.calculate(request)
        
        # 20/min requested, base rate 10/min with 2 outputs per cycle
        # = 20/10 = 2 factories
        chain = result["production_chain"]
        item_a = next(n for n in chain if n["item"] == "ItemA")
        assert item_a["factories"]["count"] == pytest.approx(2.0)
    
    def test_fractional_factory_count(self, solver):
        """Test fractional factory count (no rounding)."""
        from src.models import CalculationRequest
        
        request = CalculationRequest(
            outputs=[{"item": "ItemA", "rate": 15}],
            global_tiers={"Assembler": "Tier 1"},
            research_efficiency={"ore": 0.0, "olumite": 0.0}
        )
        
        result = solver.calculate(request)
        
        # 15/min requested, base rate 10/min
        # = 15/10 = 1.5 factories
        chain = result["production_chain"]
        item_a = next(n for n in chain if n["item"] == "ItemA")
        assert item_a["factories"]["count"] == pytest.approx(1.5)
    
    def test_tier_speed_multiplier(self, solver):
        """Test that tier speed multiplier affects factory count."""
        from src.models import CalculationRequest
        
        request = CalculationRequest(
            outputs=[{"item": "ItemA", "rate": 20}],
            global_tiers={"Assembler": "Tier 2"},  # 2x speed
            research_efficiency={"ore": 0.0, "olumite": 0.0}
        )
        
        result = solver.calculate(request)
        
        # 20/min requested, base rate 10/min * 2 (tier) = 20/min effective
        # = 20/20 = 1 factory
        chain = result["production_chain"]
        item_a = next(n for n in chain if n["item"] == "ItemA")
        assert item_a["factories"]["count"] == pytest.approx(1.0)


class TestModifiers:
    """Test robot-based buff applications."""
    
    def test_speed_robot(self, solver):
        """Test speed robot increases effective rate."""
        from src.models import CalculationRequest
        
        request = CalculationRequest(
            outputs=[{"item": "ItemA", "rate": 20}],
            global_tiers={"Assembler": "Tier 1"},
            global_robots={"Assembler": "Speed Bot"},
            workstation_level=1,
            research_efficiency={"ore": 0.0, "olumite": 0.0}
        )
        
        result = solver.calculate(request)
        
        # 20/min requested, base rate 10/min * (1 + 0.5) = 15/min effective
        # = 20/15 = 1.333 factories
        chain = result["production_chain"]
        item_a = next(n for n in chain if n["item"] == "ItemA")
        assert item_a["factories"]["count"] == pytest.approx(1.333, rel=0.01)
        # power = 1.333 * 550 kW * (1 + 0.1) = 806.67 kW
        assert item_a["power_kw"] == pytest.approx(806.67, rel=0.01)
    
    def test_efficiency_robot(self, solver):
        """Test efficiency robot reduces input requirements."""
        from src.models import CalculationRequest
        
        request = CalculationRequest(
            outputs=[{"item": "ItemA", "rate": 20}],
            global_tiers={"Assembler": "Tier 1"},
            global_robots={"Assembler": "Efficiency Bot"},
            workstation_level=1,
            research_efficiency={"ore": 0.0, "olumite": 0.0}
        )
        
        result = solver.calculate(request)
        
        chain = result["production_chain"]
        item_a = next(n for n in chain if n["item"] == "ItemA")
        
        # Without efficiency: 20/min ItemA * (5/2) = 50/min ItemB
        # With 20% efficiency: 50/1.2 = 41.67/min ItemB
        item_b_input = item_a["inputs_required"]["ItemB"]
        assert item_b_input["rate"] == pytest.approx(41.67, rel=0.01)
    
    def test_workstation_scales_buff_and_power(self, solver):
        """Workstation level multiplies both the buff and the power increase."""
        from src.models import CalculationRequest
        
        request = CalculationRequest(
            outputs=[{"item": "ItemA", "rate": 20}],
            global_tiers={"Assembler": "Tier 1"},
            global_robots={"Assembler": "Speed Bot"},
            workstation_level=3,
            research_efficiency={"ore": 0.0, "olumite": 0.0}
        )
        
        result = solver.calculate(request)
        
        chain = result["production_chain"]
        item_a = next(n for n in chain if n["item"] == "ItemA")
        # speed = 0.5 * 4 = 2.0 → effective 30/min → 20/30 = 0.667 factories
        assert item_a["factories"]["count"] == pytest.approx(0.667, rel=0.01)
        # power = 0.667 * 550 kW * (1 + 0.1 * 4) = 0.667 * 550 * 1.4 = 513.33 kW
        assert item_a["power_kw"] == pytest.approx(513.33, rel=0.01)
    
    def test_default_robot_selected(self, solver):
        """Highest-efficiency robot is chosen as the per-factory default."""
        # Default for Assembler should be Efficiency Bot (0.2 > Speed Bot's none)
        assert solver._default_robot("Assembler") == "Efficiency Bot"
        # Default for Miner should be Miner Eff Robot (only efficiency candidate)
        assert solver._default_robot("Miner") == "Miner Eff Robot"
    
    def test_recipe_override_robot_replaces_global(self, solver):
        """Per-recipe robot override replaces the global robot."""
        from src.models import CalculationRequest
        
        request = CalculationRequest(
            outputs=[{"item": "ItemA", "rate": 20}],
            global_tiers={"Assembler": "Tier 1"},
            global_robots={"Assembler": "Speed Bot"},
            recipe_overrides={"ItemA": {"robot": "Efficiency Bot"}},
            workstation_level=1,
            research_efficiency={"ore": 0.0, "olumite": 0.0}
        )
        
        result = solver.calculate(request)
        
        chain = result["production_chain"]
        item_a = next(n for n in chain if n["item"] == "ItemA")
        # Efficiency Bot has no speed buff → count = 20/10 = 2
        assert item_a["factories"]["count"] == pytest.approx(2.0)
        # ...but inputs are reduced by its efficiency
        assert item_a["inputs_required"]["ItemB"]["rate"] == pytest.approx(41.67, rel=0.01)
    
    def test_recipe_override_none_disables_robot(self, solver):
        """robot=None in an override disables the global robot for that recipe."""
        from src.models import CalculationRequest
        
        request = CalculationRequest(
            outputs=[{"item": "ItemA", "rate": 20}],
            global_tiers={"Assembler": "Tier 1"},
            global_robots={"Assembler": "Speed Bot"},
            recipe_overrides={"ItemA": {"robot": None}},
            workstation_level=1,
            research_efficiency={"ore": 0.0, "olumite": 0.0}
        )
        
        result = solver.calculate(request)
        
        chain = result["production_chain"]
        item_a = next(n for n in chain if n["item"] == "ItemA")
        # No speed buff → count = 20/10 = 2
        assert item_a["factories"]["count"] == pytest.approx(2.0)


class TestResearchEfficiency:
    """Test research efficiency for basic resources."""
    
    def test_ore_research_efficiency(self, solver):
        """Test ore research efficiency reduces world consumption."""
        from src.models import CalculationRequest
        
        request = CalculationRequest(
            outputs=[{"item": "ItemA", "rate": 20}],
            global_tiers={"Assembler": "Tier 1"},
            global_robots={"Assembler": None, "Miner": None},
            workstation_level=1,
            research_efficiency={"ore": 0.1, "olumite": 0.0}
        )
        
        result = solver.calculate(request)
        
        # World consumption = calculated_rate / (1 + research_efficiency)
        raw_resources = result["raw_resources"]
        assert "ore_from_world" in raw_resources
        assert raw_resources["ore_from_world"]["world_consumption"] == pytest.approx(
            raw_resources["ore_from_world"]["total_per_min"] / 1.1, rel=0.01
        )
    
    def test_olumite_research_efficiency(self, solver):
        """Test olumite research efficiency reduces world consumption."""
        from src.models import CalculationRequest
        
        request = CalculationRequest(
            outputs=[{"item": "ItemA", "rate": 20}],
            global_tiers={"Assembler": "Tier 1"},
            global_robots={"Assembler": None, "Miner": None},
            workstation_level=1,
            research_efficiency={"ore": 0.0, "olumite": 0.1}
        )
        
        result = solver.calculate(request)
        
        raw_resources = result["raw_resources"]
        assert "olumite_from_world" in raw_resources
        assert raw_resources["olumite_from_world"]["world_consumption"] == pytest.approx(
            raw_resources["olumite_from_world"]["total_per_min"] / 1.1, rel=0.01
        )


class TestPowerCalculation:
    """Test power consumption calculations."""
    
    def test_proportional_power(self, solver):
        """Test that power is proportional to fractional factories."""
        from src.models import CalculationRequest
        
        request = CalculationRequest(
            outputs=[{"item": "ItemA", "rate": 15}],  # 1.5 factories at Tier 1
            global_tiers={"Assembler": "Tier 1"},
            research_efficiency={"ore": 0.0, "olumite": 0.0}
        )
        
        result = solver.calculate(request)
        
        chain = result["production_chain"]
        item_a = next(n for n in chain if n["item"] == "ItemA")
        
        # 1.5 factories * 550 kW = 825 kW (proportional, not rounded)
        assert item_a["power_kw"] == pytest.approx(825.0)
    
    def test_total_power_aggregation(self, solver):
        """Test that total power is aggregated correctly."""
        from src.models import CalculationRequest
        
        request = CalculationRequest(
            outputs=[{"item": "ItemA", "rate": 20}],
            global_tiers={"Assembler": "Tier 1"},
            research_efficiency={"ore": 0.0, "olumite": 0.0}
        )
        
        result = solver.calculate(request)
        
        # Should have total_power_kw in result
        assert "total_power_kw" in result
        assert result["total_power_kw"] > 0


class TestSharedInputs:
    """Test aggregation of shared inputs."""
    
    def test_shared_input_aggregation(self, solver):
        """Test that items needed by multiple recipes are summed."""
        from src.models import CalculationRequest
        
        # ItemC is used by both ItemA and ItemB
        request = CalculationRequest(
            outputs=[{"item": "ItemA", "rate": 10}, {"item": "ItemB", "rate": 10}],
            global_tiers={"Assembler": "Tier 1"},
            global_robots={"Assembler": None},
            research_efficiency={"ore": 0.0, "olumite": 0.0}
        )
        
        result = solver.calculate(request)
        
        chain = result["production_chain"]
        
        # Find ItemC node and verify it accounts for both usages
        item_c = next((n for n in chain if n["item"] == "ItemC"), None)
        assert item_c is not None
        # Should be sum of ItemA's need + ItemB's need
