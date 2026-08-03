"""
Data models for the Foundry Calculator.
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any

# ============================================================================
# Configuration Models
# ============================================================================

class FactoryTier(BaseModel):
    """Represents a factory tier with speed and power settings."""
    name: str
    speed_multiplier: float
    power_kw: float


class Factory(BaseModel):
    """Factory definition with multiple tiers."""
    tiers: list[FactoryTier]


# ============================================================================
# Request Models
# ============================================================================

class ModifierRequest(BaseModel):
    """Speed, efficiency, and energy modifiers."""
    speed: float = 0.0
    efficiency: float = 0.0
    energy: float = 1.0


class RecipeOverride(BaseModel):
    """Per-recipe overrides for tier and modifiers."""
    tier: Optional[str] = None
    modifiers: ModifierRequest = ModifierRequest()


class CalculationRequest(BaseModel):
    """Request to calculate production chain."""
    outputs: list[Dict[str, Any]]
    global_tiers: Dict[str, str] = {}
    recipe_overrides: Dict[str, RecipeOverride] = {}
    global_modifiers: Dict[str, ModifierRequest] = {}
    research_efficiency: Dict[str, float] = {"ore": 0.0, "olumite": 0.0}


# ============================================================================
# Response Models
# ============================================================================

class FactoryInfo(BaseModel):
    """Factory usage information."""
    type: str
    tier: str
    count: float


class InputOutputInfo(BaseModel):
    """Input or output flow information."""
    rate: float
    source: str


class ProductionNode(BaseModel):
    """A node in the production chain."""
    recipe_name: str
    item: str
    requested_rate: float
    factories: FactoryInfo
    inputs_required: Dict[str, InputOutputInfo]
    outputs_produced: Dict[str, float]
    power_kw: float


class RawResourceInfo(BaseModel):
    """Raw resource consumption information."""
    total_per_min: float
    type: str
    world_consumption: Optional[float] = None


class CalculationResult(BaseModel):
    """Complete calculation result."""
    id: str
    results: Dict[str, Any]
