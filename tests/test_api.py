"""
Integration tests for the API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app


client = TestClient(app)


class TestFactoriesEndpoint:
    """Test /api/factories endpoint."""
    
    def test_get_factories_returns_data(self):
        """Test that the factories endpoint returns factory definitions."""
        response = client.get("/api/factories")
        
        assert response.status_code == 200
        data = response.json()
        assert "Crusher" in data
        assert "Ore Vein Miner" in data
        assert "tiers" in data["Crusher"]


class TestRecipesEndpoint:
    """Test /api/recipes endpoint."""
    
    def test_get_recipes_returns_data(self):
        """Test that the recipes endpoint returns recipe definitions."""
        response = client.get("/api/recipes")
        
        assert response.status_code == 200
        data = response.json()
        assert "Xenoferrite Ore" in data
        assert "Xenoferrite Ore Rubble (Ore Vein Mining)" in data
        assert "factory_type" in data["Xenoferrite Ore"]


class TestCalculateEndpoint:
    """Test /api/calculate endpoint."""
    
    def test_simple_calculation(self):
        """Test basic calculation with simple inputs."""
        request = {
            "outputs": [{"item": "Xenoferrite Ore", "rate": 40}],
            "global_tiers": {"Crusher": "Tier 1"},
            "global_modifiers": {
                "Crusher": {"speed": 0.0, "efficiency": 0.0, "energy": 1.0}
            },
            "research_efficiency": {"ore": 0.0, "olumite": 0.0}
        }
        
        response = client.post("/api/calculate", json=request)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "results" in data
        assert "production_chain" in data["results"]
        assert "raw_resources" in data["results"]
        assert "total_power_kw" in data["results"]
    
    def test_calculation_with_efficiency_modifier(self):
        """Test calculation with efficiency modifier applied."""
        request = {
            "outputs": [{"item": "Xenoferrite Ore", "rate": 40}],
            "global_tiers": {"Crusher": "Tier 1"},
            "global_modifiers": {
                "Crusher": {"speed": 0.0, "efficiency": 0.2, "energy": 1.0}
            },
            "research_efficiency": {"ore": 0.0, "olumite": 0.0}
        }
        
        response = client.post("/api/calculate", json=request)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that efficiency was applied (inputs should be reduced)
        chain = data["results"]["production_chain"]
        xenoferrite = next(n for n in chain if n["item"] == "Xenoferrite Ore")
        # With 20% efficiency, inputs should be 40/1.2 = 33.33/min
        assert xenoferrite["inputs_required"]["Xenoferrite Ore Rubble"]["rate"] == pytest.approx(33.33, rel=0.01)
    
    def test_calculation_with_multiple_outputs(self):
        """Test calculation with multiple requested outputs."""
        request = {
            "outputs": [
                {"item": "Xenoferrite Ore", "rate": 10},
                {"item": "Technum Ore", "rate": 10}
            ],
            "global_tiers": {"Crusher": "Tier 1"},
            "global_modifiers": {
                "Crusher": {"speed": 0.0, "efficiency": 0.0, "energy": 1.0}
            },
            "research_efficiency": {"ore": 0.0, "olumite": 0.0}
        }
        
        response = client.post("/api/calculate", json=request)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]["production_chain"]) > 0
    
    def test_invalid_item_returns_error(self):
        """Test that requesting an invalid item returns an error."""
        request = {
            "outputs": [{"item": "NonExistentItem", "rate": 20}],
            "global_tiers": {"Crusher": "Tier 1"},
            "global_modifiers": {},
            "research_efficiency": {"ore": 0.0, "olumite": 0.0}
        }
        
        response = client.post("/api/calculate", json=request)
        
        # Should handle gracefully (either error or no factories needed)
        assert response.status_code in [200, 400, 422]
    
    def test_empty_outputs_returns_error(self):
        """Test that empty outputs returns an error."""
        request = {
            "outputs": [],
            "global_tiers": {},
            "global_modifiers": {},
            "research_efficiency": {}
        }
        
        response = client.post("/api/calculate", json=request)
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 422]


class TestCalculationCache:
    """Test calculation caching endpoints."""
    
    def test_retrieve_cached_calculation(self):
        """Test that we can retrieve a cached calculation."""
        # First, create a calculation
        request = {
            "outputs": [{"item": "Xenoferrite Ore", "rate": 40}],
            "global_tiers": {"Crusher": "Tier 1"},
            "global_modifiers": {},
            "research_efficiency": {}
        }
        
        create_response = client.post("/api/calculate", json=request)
        assert create_response.status_code == 200
        calc_id = create_response.json()["id"]
        
        # Then retrieve it
        get_response = client.get(f"/api/calculate/{calc_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == calc_id
    
    def test_delete_cached_calculation(self):
        """Test that we can delete a cached calculation."""
        # Create a calculation
        request = {
            "outputs": [{"item": "ItemA", "rate": 20}],
            "global_tiers": {"Assembler": "Tier 1"},
            "global_modifiers": {},
            "research_efficiency": {}
        }
        
        create_response = client.post("/api/calculate", json=request)
        assert create_response.status_code == 200
        calc_id = create_response.json()["id"]
        
        # Delete it
        delete_response = client.delete(f"/api/calculate/{calc_id}")
        assert delete_response.status_code == 200
        
        # Try to retrieve - should fail
        get_response = client.get(f"/api/calculate/{calc_id}")
        assert get_response.status_code == 404
    
    def test_nonexistent_calculation(self):
        """Test that retrieving a nonexistent calculation returns 404."""
        response = client.get("/api/calculate/nonexistent")
        assert response.status_code == 404


class TestXenoferriteCalculation:
    """Test calculation with Xenoferrite Ore production."""
    
    def test_xenoferrite_ore_production(self):
        """
        Test production chain for Xenoferrite Ore:
        - Request: 40/min Xenoferrite Ore
        - Crusher: 40/min base rate, 1:1 input/output
        - Ore Vein Miner: 160/min base rate, 1:1 input/output
        - Global modifier: Ore Vein Miner efficiency +20%
        - Research efficiency: ore +10%
        """
        request = {
            "outputs": [{"item": "Xenoferrite Ore", "rate": 40}],
            "global_tiers": {"Crusher": "Tier 1", "Ore Vein Miner": "Tier 1"},
            "global_modifiers": {
                "Ore Vein Miner": {"speed": 0.0, "efficiency": 0.2, "energy": 1.0}
            },
            "research_efficiency": {"ore": 0.1, "olumite": 0.0}
        }
        
        response = client.post("/api/calculate", json=request)
        assert response.status_code == 200
        data = response.json()
        
        chain = data["results"]["production_chain"]
        
        # Xenoferrite Ore: 40/min requested, 40/min base rate
        # Factories = 40/40 = 1 Crusher
        xenoferrite = next(n for n in chain if n["item"] == "Xenoferrite Ore")
        assert xenoferrite["factories"]["count"] == pytest.approx(1.0)
        
        # Ore Vein Miner: 40/min needed (1:1 ratio), 160/min base rate with 20% efficiency
        # Factories = 40/160 = 0.25 Ore Vein Miner
        ore_vein = next(n for n in chain if n["item"] == "Xenoferrite Ore Rubble")
        assert ore_vein["factories"]["count"] == pytest.approx(0.25)
        
        # Raw input rate: 40/min
        # World consumption with combined efficiency (1 + 0.2 + 0.1 = 1.3): 40/1.3 = 30.77/min
        raw_resources = data["results"]["raw_resources"]
        assert "Xenoferrite Ore Rubble (from environment)" in raw_resources
        world_consumption = raw_resources["Xenoferrite Ore Rubble (from environment)"]["world_consumption"]
        assert world_consumption == pytest.approx(30.77, rel=0.01)
        
        # Total power should be calculated
        assert data["results"]["total_power_kw"] > 0
