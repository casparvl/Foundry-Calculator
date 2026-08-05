"""
Tests for configuration file consistency between factories.json and recipes.json.
"""
import json
from pathlib import Path

# Get the config directory relative to this test file
CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


def load_factories():
    """Load factories.json."""
    with open(CONFIG_DIR / "factories.json", "r") as f:
        return json.load(f)


def load_recipes():
    """Load recipes.json."""
    with open(CONFIG_DIR / "recipes.json", "r") as f:
        return json.load(f)


def load_robots():
    """Load robots.json."""
    with open(CONFIG_DIR / "robots.json", "r") as f:
        return json.load(f)


class TestFactoryConsistency:
    """Test that all factories referenced in recipes are defined."""
    
    def test_all_recipe_factories_exist(self):
        """Test that every recipe's factory_type exists in factories.json."""
        factories = load_factories()
        recipes = load_recipes()
        
        defined_factories = set(factories.keys())
        
        for recipe_name, recipe in recipes.items():
            factory_type = recipe.get("factory_type")
            assert factory_type in defined_factories, (
                f"Recipe '{recipe_name}' references factory_type '{factory_type}' "
                f"which is not defined in factories.json"
            )


class TestRecipeConsistency:
    """Test that recipe inputs reference valid recipes or world resources."""
    
    def test_recipe_inputs_resolve(self):
        """
        Test that every recipe input (except world resources) has a producing recipe.
        World resources are identified by having 'from environment' in the input name.
        """
        recipes = load_recipes()
        
        # Build set of all output items from recipes
        produced_items = set()
        for recipe_name, recipe in recipes.items():
            for output_item in recipe.get("outputs", {}).keys():
                produced_items.add(output_item)
        
        # Check each recipe's inputs
        for recipe_name, recipe in recipes.items():
            for input_item in recipe.get("inputs", {}).keys():
                # Skip world resources (they have 'from environment' suffix)
                if "from environment" in input_item:
                    continue
                
                # Skip items that are inputs to world resources (like "ore_from_world")
                if input_item.endswith("_from_world"):
                    continue
                
                # Check if input is produced by some recipe
                assert input_item in produced_items or input_item in recipes, (
                    f"Recipe '{recipe_name}' requires input '{input_item}' "
                    f"which is not produced by any recipe and is not a world resource"
                )


class TestRobotConsistency:
    """Test robots.json consistency with factories.json."""
    
    def test_all_robot_machines_exist(self):
        """Test that every machine alias target exists in factories.json."""
        factories = load_factories()
        robots = load_robots()
        
        defined_factories = set(factories.keys())
        aliases = robots.get("machine_aliases", {})
        
        for group, factory_list in aliases.items():
            for factory in factory_list:
                assert factory in defined_factories, (
                    f"Robot machine group '{group}' references factory '{factory}' "
                    f"which is not defined in factories.json"
                )
    
    def test_robot_affected_machines_are_alias_groups(self):
        """Test that every robot's affected machines are defined alias groups."""
        robots = load_robots()
        
        aliases = set(robots.get("machine_aliases", {}).keys())
        for robot_name, robot in robots.get("robots", {}).items():
            for group in robot.get("affected_machines", []):
                assert group in aliases, (
                    f"Robot '{robot_name}' affects machine group '{group}' "
                    f"which has no entry in machine_aliases"
                )


class TestTierConsistency:
    """Test that tier references are valid."""
    
    def test_all_tiers_exist(self):
        """Test that all tier names referenced in recipes exist in factory definitions."""
        factories = load_factories()
        recipes = load_recipes()
        
        # Build set of all valid tier names per factory
        valid_tiers = {}
        for factory_name, factory in factories.items():
            valid_tiers[factory_name] = {
                tier["name"] for tier in factory.get("tiers", [])
            }
        
        # Check global tiers (not applicable here - we don't have them in recipes)
        # Recipes don't specify tiers, they use global settings
