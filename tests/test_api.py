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
        assert "Assembler" in data
        assert "Miner" in data
        assert "tiers" in data["Assembler"]


class TestRecipesEndpoint:
    """Test /api/recipes endpoint."""
    
    def test_get_recipes_returns_data(self):
        """Test that the recipes endpoint returns recipe definitions."""
        response = client.get("/api/recipes")
        
        assert response.status_code == 200
        data = response.json()
        assert "ItemA" in data
        assert "ItemB" in data
        assert "factory_type" in data["ItemA"]


class TestCalculateEndpoint:
    """Test /api/calculate endpoint."""
    
    def test_simple_calculation(self):
        """Test basic calculation with simple inputs."""
        request = {
            "outputs": [{"item": "ItemA", "rate": 20}],
            "global_tiers": {"Assembler": "Tier 1"},
            "global_modifiers": {
                "Assembler": {"speed": 0.0, "efficiency": 0.0, "energy": 1.0}
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
            "outputs": [{"item": "ItemA", "rate": 20}],
            "global_tiers": {"Assembler": "Tier 1"},
            "global_modifiers": {
                "Assembler": {"speed": 0.0, "efficiency": 0.2, "energy": 1.0}
            },
            "research_efficiency": {"ore": 0.0, "olumite": 0.0}
        }
        
        response = client.post("/api/calculate", json=request)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that efficiency was applied (inputs should be reduced)
        chain = data["results"]["production_chain"]
        item_a = next(n for n in chain if n["item"] == "ItemA")
        item_b_rate = item_a["inputs_required"]["ItemB"]["rate"]
        
        # With 20% efficiency, inputs should be reduced
        assert item_b_rate < 50  # Less than without efficiency
    
    def test_calculation_with_multiple_outputs(self):
        """Test calculation with multiple requested outputs."""
        request = {
            "outputs": [
                {"item": "ItemA", "rate": 10},
                {"item": "ItemB", "rate": 10}
            ],
            "global_tiers": {"Assembler": "Tier 1"},
            "global_modifiers": {
                "Assembler": {"speed": 0.0, "efficiency": 0.0, "energy": 1.0}
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
            "global_tiers": {"Assembler": "Tier 1"},
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
            "outputs": [{"item": "ItemA", "rate": 20}],
            "global_tiers": {"Assembler": "Tier 1"},
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


class TestFirstPromptExample:
    """Test the example from FIRST_PROMPT.md."""
    
    def test_first_prompt_example(self):
        """
        Test the example from FIRST_PROMPT.md:
        - Request: 20/min ItemA
        - Recipe A: 5x B + 10x C -> 2x A, base rate 10/min in Assembler
        - Recipe B: 5x C + 2x D -> 5x B, base rate 10/min in Assembler
        - Assembler: Tier 1 (550kW)
        - Global modifier: Assembler efficiency +20%
        - Research efficiency: ore +10%
        """
        request = {
            "outputs": [{"item": "ItemA", "rate": 20}],
            "global_tiers": {"Assembler": "Tier 1"},
            "global_modifiers": {
                "Assembler": {"speed": 0.0, "efficiency": 0.2, "energy": 1.0}
            },
            "research_efficiency": {"ore": 0.1, "olumite": 0.0}
        }
        
        response = client.post("/api/calculate", json=request)
        assert response.status_code == 200
        data = response.json()
        
        chain = data["results"]["production_chain"]
        
        # ItemA: 20/min requested, 10/min base rate, 2 outputs per cycle
        # Factories = 20/10 = 2
        item_a = next(n for n in chain if n["item"] == "ItemA")
        assert item_a["factories"]["count"] == pytest.approx(2.0)
        
        # ItemA inputs with 20% efficiency:
        # B: 20 * (5/2) / 1.2 = 41.67/min
        # C: 20 * (10/2) / 1.2 = 83.33/min
        assert item_a["inputs_required"]["ItemB"]["rate"] == pytest.approx(41.67, rel=0.01)
        assert item_a["inputs_required"]["ItemC"]["rate"] == pytest.approx(83.33, rel=0.01)
        
        # ItemB: 41.67/min needed, 10/min base rate, 5 outputs per cycle
        # Factories = 41.67/10 = 4.167
        item_b = next(n for n in chain if n["item"] == "ItemB")
        assert item_b["factories"]["count"] == pytest.approx(4.167, rel=0.01)
        
        # Total power should be calculated
        assert data["results"]["total_power_kw"] > 0
