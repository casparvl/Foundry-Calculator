"""
Core calculation engine for the Foundry Calculator.
"""
from typing import Dict, List, Any, Optional
from src.models import (
    Factory, FactoryTier, CalculationRequest,
    ProductionNode, FactoryInfo, InputOutputInfo, RawResourceInfo
)
import math


class ProductionChainSolver:
    """
    Solves production chains and calculates resource requirements.
    
    All calculations are fractional (no rounding).
    Modifiers are applied independently.
    """
    
    def __init__(self, factories: Dict[str, Any], recipes: Dict[str, Any],
                 robots: Optional[Dict[str, Any]] = None):
        self.factories = factories
        self.recipes = recipes
        self.robots = robots if robots is not None else {}
        self._calculation_cache: Dict[str, Any] = {}
        # Build reverse lookup: output item → recipe name.
        # Fracking alternative recipes produce the same ore item as their
        # standard "from environment" counterparts; they are tracked separately
        # so the fracking toggle can choose between the two producers.
        self._output_to_recipe: Dict[str, str] = {}
        self._fracking_recipes: Dict[str, str] = {}
        for recipe_name, recipe_data in recipes.items():
            is_fracking = bool(recipe_data.get("fracking"))
            for output_item in recipe_data.get("outputs", {}):
                if is_fracking:
                    self._fracking_recipes[output_item] = recipe_name
                else:
                    self._output_to_recipe[output_item] = recipe_name
    
    def calculate(self, request: CalculationRequest) -> Dict[str, Any]:
        """
        Calculate the complete production chain for the given request.
        
        Args:
            request: The calculation request with outputs and settings
            
        Returns:
            Complete calculation result with production chain, raw resources, and power
        """
        # Build production graph
        production_chain = []
        raw_resources: Dict[str, RawResourceInfo] = {}
        total_power = 0.0
        
        # Track all items needed at each level
        items_needed: Dict[str, float] = {}
        for output in request.outputs:
            item = output["item"]
            rate = output["rate"]
            items_needed[item] = items_needed.get(item, 0) + rate
        
        # Phase 1: propagate demands to a fixpoint (order-independent).
        # Each recipe only propagates the delta of demand it hasn't seen yet, so
        # consumers at any depth contribute fully regardless of processing order.
        propagated: Dict[str, float] = {}
        pending = list(items_needed.keys())
        while pending:
            item = pending.pop()
            delta = items_needed.get(item, 0.0) - propagated.get(item, 0.0)
            if delta <= 0:
                continue
            propagated[item] = items_needed.get(item, 0.0)
            
            # Check if item has a recipe (direct or via output lookup)
            recipe_name = self._recipe_for(item, request.resolve_fracking)
            if not recipe_name:
                # Basic resource or world input: nothing to propagate
                continue
            recipe = self.recipes[recipe_name]
            if "resource_type" in recipe:
                # World resource recipe: inputs come from the environment
                continue
            
            factory_type = recipe["factory_type"]
            robot_name = self._robot_for(request, factory_type, recipe_name)
            _, efficiency_modifier, _ = self._robot_effects(
                robot_name, request.workstation_level
            )
            efficiency = 1 + efficiency_modifier
            if recipe.get("fracking"):
                # Ore research efficiency also reduces fracking fluid consumption
                efficiency += request.research_efficiency.get("ore", 0.0)
            primary_output_amount = list(recipe["outputs"].values())[0]
            
            for input_item, input_amount in recipe["inputs"].items():
                input_rate = (
                    delta * input_amount / primary_output_amount / efficiency
                )
                if input_rate > 0:
                    items_needed[input_item] = (
                        items_needed.get(input_item, 0) + input_rate
                    )
                    pending.append(input_item)
        
        # Phase 2: build nodes for every produced item using the final demands
        processed_items = set()
        queue = list(items_needed.keys())
        
        while queue:
            item = queue.pop(0)
            if item in processed_items:
                continue
            processed_items.add(item)
            
            # Check if item has a recipe (direct or via output lookup)
            recipe_name = self._recipe_for(item, request.resolve_fracking)
            if not recipe_name:
                # This is a basic resource without a recipe
                if item not in raw_resources:
                    raw_resources[item] = RawResourceInfo(
                        total_per_min=items_needed[item],
                        type="basic"
                    )
                continue
            
            # Process this item's production
            recipe = self.recipes[recipe_name]
            factory_type = recipe["factory_type"]
            
            # Get tier (global or recipe override)
            global_tier = request.global_tiers.get(factory_type)
            if not global_tier:
                tiers = self.factories.get(factory_type, {}).get("tiers", [])
                global_tier = tiers[-1]["name"] if tiers else "Tier 1"
            override_tier = None
            if recipe_name in request.recipe_overrides:
                override_tier = request.recipe_overrides[recipe_name].tier
            selected_tier = override_tier if override_tier else global_tier
            
            # Get robot (recipe override, global selection, or default)
            robot_name = self._robot_for(request, factory_type, recipe_name)
            speed_modifier, efficiency_modifier, power_multiplier = self._robot_effects(
                robot_name, request.workstation_level
            )
            
            # Calculate effective rate (primary output amount = throughput per factory)
            primary_output_amount = list(recipe["outputs"].values())[0]
            tier_info = self._get_tier_info(factory_type, selected_tier)
            effective_rate = (
                primary_output_amount 
                * tier_info.speed_multiplier 
                * (1 + speed_modifier)
            )
            
            # Calculate factory count
            factory_count = items_needed[item] / effective_rate
            
            # Calculate inputs required
            inputs_required = {}
            is_world_resource = "resource_type" in recipe
            
            for input_item, input_amount in recipe["inputs"].items():
                # Calculate input rate based on output ratio
                input_rate = (items_needed[item] * input_amount / primary_output_amount)
                
                if is_world_resource:
                    # For world resources, don't apply factory efficiency yet
                    # Will apply both factory + research efficiency for world_consumption
                    inputs_required[input_item] = InputOutputInfo(
                        rate=input_rate,
                        source="world"
                    )
                    # Do NOT add to processing queue - consumed from world
                else:
                    # Apply efficiency modifier for regular recipes.
                    # Fracking recipes also benefit from ore research efficiency.
                    efficiency = 1 + efficiency_modifier
                    if recipe.get("fracking"):
                        efficiency += request.research_efficiency.get("ore", 0.0)
                    input_rate /= efficiency
                    
                    inputs_required[input_item] = InputOutputInfo(
                        rate=input_rate,
                        source="recipe"
                    )
                    
                    if input_item in items_needed and input_item not in processed_items:
                        queue.append(input_item)
            
            # Calculate power (proportional to factory count)
            power_kw = factory_count * tier_info.power_kw * power_multiplier
            total_power += power_kw
            
            # Get actual output item name from recipe
            output_item = list(recipe["outputs"].keys())[0]
            output_rate = items_needed[item]
            
            # Create production node
            node = ProductionNode(
                recipe_name=recipe_name,
                item=item,
                requested_rate=items_needed[item],
                factories=FactoryInfo(
                    type=factory_type,
                    tier=selected_tier,
                    count=factory_count
                ),
                inputs_required=inputs_required,
                outputs_produced={output_item: output_rate},
                power_kw=power_kw,
                fracking=bool(recipe.get("fracking"))
            )
            production_chain.append(node)
            
            # Handle world resources (mined from environment or infinite)
            if is_world_resource:
                resource_type = recipe["resource_type"]
                
                if resource_type == "infinite":
                    # Infinite resources: no efficiency reduction
                    for input_item, input_amount in recipe["inputs"].items():
                        raw_input_rate = items_needed[item] * input_amount / primary_output_amount
                        raw_resources[input_item] = RawResourceInfo(
                            total_per_min=raw_input_rate,
                            type=resource_type,
                            world_consumption=raw_input_rate
                        )
                else:
                    # Ore/olumite resources: apply both robot + research efficiency
                    research_eff = request.research_efficiency.get(resource_type, 0.0)
                    for input_item, input_amount in recipe["inputs"].items():
                        raw_input_rate = items_needed[item] * input_amount / primary_output_amount
                        total_efficiency = 1 + efficiency_modifier + research_eff
                        world_consumption = raw_input_rate / total_efficiency
                        raw_resources[input_item] = RawResourceInfo(
                            total_per_min=raw_input_rate,
                            type=resource_type,
                            world_consumption=world_consumption
                        )
        
        # Build final result
        result = {
            "production_chain": [node.dict() for node in production_chain],
            "raw_resources": {k: v.dict() for k, v in raw_resources.items()},
            "requested_outputs": [{"item": o["item"], "rate": o["rate"]} for o in request.outputs],
            "total_power_kw": total_power
        }
        
        return result
    
    def _recipe_for(self, item: str, resolve_fracking: bool) -> Optional[str]:
        """Resolve the producing recipe for an item.

        If the item is itself a recipe key (e.g. an extractor recipe that is
        requested directly), use it. Otherwise, when fracking resolution is
        enabled, prefer the fracking alternative recipe for ore items; fall back
        to the standard "from environment" recipe.
        """
        if item in self.recipes:
            return item
        if resolve_fracking and item in self._fracking_recipes:
            return self._fracking_recipes[item]
        return self._output_to_recipe.get(item)

    def _get_tier_info(self, factory_type: str, tier_name: str) -> FactoryTier:
        """Get tier information for a factory type."""
        factory = self.factories.get(factory_type)
        if not factory:
            raise ValueError(f"Factory type '{factory_type}' not found")
        
        for tier in factory["tiers"]:
            if tier["name"] == tier_name:
                return FactoryTier(**tier)
        
        raise ValueError(f"Tier '{tier_name}' not found for factory '{factory_type}'")
    
    def _robot_for(self, request: CalculationRequest, factory_type: str,
                   recipe_name: str) -> Optional[str]:
        """Resolve the robot name for a factory, checking recipe overrides
        first, then global selections. Absent/explicit-null means no robot."""
        if recipe_name in request.recipe_overrides:
            return request.recipe_overrides[recipe_name].robot
        return request.global_robots.get(factory_type)
    
    def _default_robot(self, factory_type: str) -> Optional[str]:
        """Pick the default robot for a factory: highest efficiency, tiebreak speed."""
        candidates = [
            name for name in self.robots.get("robots", {})
            if self._robot_affects(name, factory_type)
        ]
        if not candidates:
            return None
        
        def score(name):
            robot = self.robots["robots"][name]
            buff = robot.get("buff_percentage", 0.0)
            efficiency = buff if robot.get("buff_type") == "efficiency" else -1.0
            speed = buff if robot.get("buff_type") == "speed" else -1.0
            return (efficiency, speed)
        
        return max(candidates, key=score)
    
    def _robot_affects(self, robot_name: str, factory_type: str) -> bool:
        """Check whether a robot's affected machine groups include the factory type."""
        if not self.robots:
            return False
        robot = self.robots.get("robots", {}).get(robot_name)
        if not robot:
            return False
        aliases = self.robots.get("machine_aliases", {})
        for group in robot.get("affected_machines", []):
            if factory_type in aliases.get(group, []):
                return True
        return False
    
    def _robot_effects(self, robot_name: Optional[str],
                       workstation_level: int) -> tuple[float, float, float]:
        """Return (speed_modifier, efficiency_modifier, power_multiplier) for a robot."""
        speed_modifier = 0.0
        efficiency_modifier = 0.0
        power_multiplier = 1.0
        if not robot_name or not self.robots:
            return speed_modifier, efficiency_modifier, power_multiplier
        robot = self.robots.get("robots", {}).get(robot_name)
        if not robot:
            return speed_modifier, efficiency_modifier, power_multiplier
        
        levels = self.robots.get("workstation_levels", {})
        multiplier = levels.get(str(workstation_level), 4.0)
        
        buff = robot.get("buff_percentage", 0.0) * multiplier
        if robot.get("buff_type") == "speed":
            speed_modifier = buff
        else:
            efficiency_modifier = buff
        power_multiplier = 1 + robot.get("power_increase_percentage", 0.0) * multiplier
        return speed_modifier, efficiency_modifier, power_multiplier
    
    def cache_calculation(self, calc_id: str, result: Dict[str, Any]):
        """Cache a calculation result."""
        self._calculation_cache[calc_id] = result
    
    def get_cached_calculation(self, calc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a cached calculation result."""
        return self._calculation_cache.get(calc_id)
    
    def delete_cached_calculation(self, calc_id: str):
        """Delete a cached calculation result."""
        if calc_id in self._calculation_cache:
            del self._calculation_cache[calc_id]
