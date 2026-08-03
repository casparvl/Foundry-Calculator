"""
Core calculation engine for the Foundry Calculator.
"""
from typing import Dict, List, Any, Optional
from src.models import (
    Factory, FactoryTier, ModifierRequest, CalculationRequest,
    ProductionNode, FactoryInfo, InputOutputInfo, RawResourceInfo
)
import math


class ProductionChainSolver:
    """
    Solves production chains and calculates resource requirements.
    
    All calculations are fractional (no rounding).
    Modifiers are applied independently.
    """
    
    def __init__(self, factories: Dict[str, Any], recipes: Dict[str, Any]):
        self.factories = factories
        self.recipes = recipes
        self._calculation_cache: Dict[str, Any] = {}
    
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
        
        # Process items (BFS to handle dependencies)
        processed_items = set()
        queue = list(items_needed.keys())
        
        while queue:
            item = queue.pop(0)
            if item in processed_items:
                continue
            
            if item not in self.recipes:
                # This is a basic resource without a recipe
                if item not in raw_resources:
                    raw_resources[item] = RawResourceInfo(
                        total_per_min=items_needed[item],
                        type="basic"
                    )
                processed_items.add(item)
                continue
            
            # Process this item's production
            recipe = self.recipes[item]
            factory_type = recipe["factory_type"]
            
            # Get tier (global or recipe override)
            global_tier = request.global_tiers.get(factory_type, "Tier 1")
            override_tier = None
            if item in request.recipe_overrides:
                override_tier = request.recipe_overrides[item].tier
            selected_tier = override_tier if override_tier else global_tier
            
            # Get modifiers (recipe override or global)
            if item in request.recipe_overrides and request.recipe_overrides[item].modifiers:
                factory_modifiers = request.recipe_overrides[item].modifiers
            else:
                factory_modifiers = request.global_modifiers.get(factory_type, ModifierRequest())
            
            # Calculate effective rate
            tier_info = self._get_tier_info(factory_type, selected_tier)
            speed_modifier = 1 + factory_modifiers.speed
            effective_rate = (
                recipe["base_rate_per_min"] 
                * tier_info.speed_multiplier 
                * speed_modifier
            )
            
            # Calculate factory count
            factory_count = items_needed[item] / effective_rate
            
            # Calculate inputs required
            inputs_required = {}
            for input_item, input_amount in recipe["inputs"].items():
                # Calculate input rate based on output ratio
                output_amount = list(recipe["outputs"].values())[0]
                input_rate = (items_needed[item] * input_amount / output_amount)
                
                # Apply efficiency modifier
                efficiency = 1 + factory_modifiers.efficiency
                input_rate /= efficiency
                
                inputs_required[input_item] = InputOutputInfo(
                    rate=input_rate,
                    source="recipe"
                )
                
                # Add to items needed for next iteration
                items_needed[input_item] = items_needed.get(input_item, 0) + input_rate
                if input_item not in processed_items and input_item not in queue:
                    queue.append(input_item)
            
            # Calculate power (proportional to factory count)
            power_kw = factory_count * tier_info.power_kw * factory_modifiers.energy
            total_power += power_kw
            
            # Create production node
            node = ProductionNode(
                item=item,
                requested_rate=items_needed[item],
                factories=FactoryInfo(
                    type=factory_type,
                    tier=selected_tier,
                    count=factory_count
                ),
                inputs_required=inputs_required,
                outputs_produced={"item": items_needed[item]},
                power_kw=power_kw
            )
            production_chain.append(node)
            
            # Check if this is a basic resource (mined from world)
            if "resource_type" in recipe:
                resource_type = recipe["resource_type"]
                if resource_type == "infinite":
                    raw_resources[resource_type] = RawResourceInfo(
                        total_per_min=items_needed[item],
                        type=resource_type,
                        world_consumption=items_needed[item]
                    )
                else:
                    research_eff = request.research_efficiency.get(resource_type, 0.0)
                    world_consumption = items_needed[item] / (1 + research_eff)
                    
                    raw_resources[resource_type] = RawResourceInfo(
                        total_per_min=items_needed[item],
                        type=resource_type,
                        world_consumption=world_consumption
                    )
            
            processed_items.add(item)
        
        # Build final result
        result = {
            "production_chain": [node.dict() for node in production_chain],
            "raw_resources": {k: v.dict() for k, v in raw_resources.items()},
            "total_power_kw": total_power
        }
        
        return result
    
    def _get_tier_info(self, factory_type: str, tier_name: str) -> FactoryTier:
        """Get tier information for a factory type."""
        factory = self.factories.get(factory_type)
        if not factory:
            raise ValueError(f"Factory type '{factory_type}' not found")
        
        for tier in factory["tiers"]:
            if tier["name"] == tier_name:
                return FactoryTier(**tier)
        
        raise ValueError(f"Tier '{tier_name}' not found for factory '{factory_type}'")
    
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
