"""
Unit tests for the calculator module.
"""
import pytest
from src.calculator import ProductionChainSolver
from src.models import ModifierRequest

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
        "inputs": {"ItemB": 5, "ItemC": 10},
        "outputs": {"ItemA": 2},
        "base_rate_per_min": 10
    },
    "ItemB": {
        "factory_type": "Assembler",
        "inputs": {"ItemC": 5, "ItemD": 2},
        "outputs": {"ItemB": 5},
        "base_rate_per_min": 10
    },
    "ItemC": {
        "factory_type": "Miner",
        "inputs": {"ore_from_world": 1},
        "outputs": {"ItemC": 1},
        "base_rate_per_min": 100,
        "resource_type": "ore"
    },
    "ItemD": {
        "factory_type": "Miner",
        "inputs": {"olumite_from_world": 1},
        "outputs": {"ItemD": 1},
        "base_rate_per_min": 50,
        "resource_type": "olumite"
    }
}


@pytest.fixture
def solver():
    return ProductionChainSolver(SAMPLE_FACTORIES, SAMPLE_RECIPES)


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
    """Test modifier applications."""
    
    def test_speed_modifier(self, solver):
        """Test speed modifier increases effective rate."""
        from src.models import CalculationRequest, ModifierRequest
        
        request = CalculationRequest(
            outputs=[{"item": "ItemA", "rate": 20}],
            global_tiers={"Assembler": "Tier 1"},
            global_modifiers={"Assembler": ModifierRequest(speed=0.5, efficiency=0.0, energy=1.0)},
            research_efficiency={"ore": 0.0, "olumite": 0.0}
        )
        
        result = solver.calculate(request)
        
        # 20/min requested, base rate 10/min * 1.5 (speed) = 15/min effective
        # = 20/15 = 1.333 factories
        chain = result["production_chain"]
        item_a = next(n for n in chain if n["item"] == "ItemA")
        assert item_a["factories"]["count"] == pytest.approx(1.333, rel=0.01)
    
    def test_efficiency_modifier(self, solver):
        """Test efficiency modifier reduces input requirements."""
        from src.models import CalculationRequest, ModifierRequest
        
        request = CalculationRequest(
            outputs=[{"item": "ItemA", "rate": 20}],
            global_tiers={"Assembler": "Tier 1"},
            global_modifiers={"Assembler": ModifierRequest(speed=0.0, efficiency=0.2, energy=1.0)},
            research_efficiency={"ore": 0.0, "olumite": 0.0}
        )
        
        result = solver.calculate(request)
        
        chain = result["production_chain"]
        item_a = next(n for n in chain if n["item"] == "ItemA")
        
        # Without efficiency: 20/min ItemA * (5/2) = 50/min ItemB
        # With 20% efficiency: 50/1.2 = 41.67/min ItemB
        item_b_input = item_a["inputs_required"]["ItemB"]
        assert item_b_input["rate"] == pytest.approx(41.67, rel=0.01)
    
    def test_energy_modifier(self, solver):
        """Test energy modifier affects power consumption."""
        from src.models import CalculationRequest, ModifierRequest
        
        request = CalculationRequest(
            outputs=[{"item": "ItemA", "rate": 20}],
            global_tiers={"Assembler": "Tier 1"},
            global_modifiers={"Assembler": ModifierRequest(speed=0.0, efficiency=0.0, energy=1.2)},
            research_efficiency={"ore": 0.0, "olumite": 0.0}
        )
        
        result = solver.calculate(request)
        
        chain = result["production_chain"]
        item_a = next(n for n in chain if n["item"] == "ItemA")
        
        # 2 factories * 550 kW * 1.2 energy modifier = 1320 kW
        assert item_a["power_kw"] == pytest.approx(1320.0)


class TestResearchEfficiency:
    """Test research efficiency for basic resources."""
    
    def test_ore_research_efficiency(self, solver):
        """Test ore research efficiency reduces world consumption."""
        from src.models import CalculationRequest
        
        request = CalculationRequest(
            outputs=[{"item": "ItemA", "rate": 20}],
            global_tiers={"Assembler": "Tier 1"},
            global_modifiers={"Assembler": ModifierRequest(speed=0.0, efficiency=0.0, energy=1.0)},
            research_efficiency={"ore": 0.1, "olumite": 0.0}
        )
        
        result = solver.calculate(request)
        
        # Calculate required ItemC
        chain = result["production_chain"]
        item_a = next(n for n in chain if n["item"] == "ItemA")
        item_c_needed = item_a["inputs_required"]["ItemC"]["rate"]
        
        # World consumption = calculated_rate / (1 + research_efficiency)
        raw_resources = result["raw_resources"]
        assert "ore" in raw_resources
        assert raw_resources["ore"]["world_consumption"] == pytest.approx(
            raw_resources["ore"]["total_per_min"] / 1.1, rel=0.01
        )
    
    def test_olumite_research_efficiency(self, solver):
        """Test olumite research efficiency reduces world consumption."""
        from src.models import CalculationRequest
        
        request = CalculationRequest(
            outputs=[{"item": "ItemA", "rate": 20}],
            global_tiers={"Assembler": "Tier 1"},
            global_modifiers={"Assembler": ModifierRequest(speed=0.0, efficiency=0.2, energy=1.0)},
            research_efficiency={"ore": 0.0, "olumite": 0.1}
        )
        
        result = solver.calculate(request)
        
        raw_resources = result["raw_resources"]
        assert "olumite" in raw_resources
        assert raw_resources["olumite"]["world_consumption"] == pytest.approx(
            raw_resources["olumite"]["total_per_min"] / 1.1, rel=0.01
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
            global_modifiers={"Assembler": ModifierRequest(speed=0.0, efficiency=0.0, energy=1.0)},
            research_efficiency={"ore": 0.0, "olumite": 0.0}
        )
        
        result = solver.calculate(request)
        
        chain = result["production_chain"]
        
        # Find ItemC node and verify it accounts for both usages
        item_c = next((n for n in chain if n["item"] == "ItemC"), None)
        assert item_c is not None
        # Should be sum of ItemA's need + ItemB's need
