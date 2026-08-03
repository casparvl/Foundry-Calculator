"""
FastAPI application for the Foundry Calculator.
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
import uuid
import json

from src.models import CalculationRequest
from src.calculator import ProductionChainSolver

app = FastAPI(title="Foundry Calculator API")

# Load configuration files
with open("config/factories.json", "r") as f:
    FACTORIES = json.load(f)

with open("config/recipes.json", "r") as f:
    RECIPES = json.load(f)

# Initialize solver
solver = ProductionChainSolver(FACTORIES, RECIPES)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main UI."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/factories")
async def get_factories():
    """Return all factory definitions with tiers."""
    return FACTORIES


@app.get("/api/recipes")
async def get_recipes():
    """Return all recipe definitions."""
    return RECIPES


@app.post("/api/calculate")
async def calculate(request: CalculationRequest):
    """
    Calculate production chain for the given request.
    
    Returns a calculation ID that can be used to retrieve the result.
    """
    try:
        result = solver.calculate(request)
        calc_id = f"calc_{uuid.uuid4().hex[:8]}"
        solver.cache_calculation(calc_id, result)
        
        return {
            "id": calc_id,
            "results": result
        }
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/calculate/{calc_id}")
async def get_calculation(calc_id: str):
    """Retrieve a cached calculation result."""
    result = solver.get_cached_calculation(calc_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Calculation not found")
    return {"id": calc_id, "results": result}


@app.delete("/api/calculate/{calc_id}")
async def delete_calculation(calc_id: str):
    """Delete a cached calculation result."""
    solver.delete_cached_calculation(calc_id)
    return {"message": "Calculation deleted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
