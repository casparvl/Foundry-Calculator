// Main frontend logic for the Foundry Calculator

let factoryData = {};
let recipeData = {};
let calculationResult = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', async function() {
    await loadConfiguration();
    addOutputRow(); // Add first output row by default
});

// Load factory and recipe configurations from API
async function loadConfiguration() {
    try {
        const [factoriesResponse, recipesResponse] = await Promise.all([
            fetch('/api/factories'),
            fetch('/api/recipes')
        ]);
        
        factoryData = await factoriesResponse.json();
        recipeData = await recipesResponse.json();
        
        // Populate global settings
        populateGlobalSettings();
        populateRecipeOverrides();
    } catch (error) {
        console.error('Error loading configuration:', error);
        alert('Failed to load configuration. Please check if the server is running.');
    }
}

// Populate global settings dropdowns and inputs
function populateGlobalSettings() {
    const container = document.getElementById('global-settings-container');
    container.innerHTML = '';
    
    // Factory tier selections
    const tierRow = document.createElement('div');
    tierRow.className = 'row mb-3';
    tierRow.innerHTML = '<div class="col-12"><h6>Factory Tiers</h6></div>';
    container.appendChild(tierRow);
    
    for (const factoryName of Object.keys(factoryData)) {
        const factory = factoryData[factoryName];
        const row = document.createElement('div');
        row.className = 'row mb-2';
        
        let tierOptions = '<option value="">Select Tier</option>';
        factory.tiers.forEach((tier, index) => {
            tierOptions += `<option value="${tier.name}" ${index === 0 ? 'selected' : ''}>${tier.name}</option>`;
        });
        
        row.innerHTML = `
            <div class="col-md-4">
                <label class="form-label">${factoryName}</label>
                <select class="form-select tier-select" data-factory="${factoryName}">
                    ${tierOptions}
                </select>
            </div>
            <div class="col-md-8">
                <div class="input-group input-group-sm">
                    <span class="input-group-text">Speed</span>
                    <input type="number" class="form-control speed-input" data-factory="${factoryName}" value="0" step="0.1" min="-1">
                    <span class="input-group-text">Eff.</span>
                    <input type="number" class="form-control efficiency-input" data-factory="${factoryName}" value="0" step="0.1" min="-1">
                    <span class="input-group-text">Ene.</span>
                    <input type="number" class="form-control energy-input" data-factory="${factoryName}" value="1" step="0.1">
                </div>
            </div>
        `;
        container.appendChild(row);
    }
    
    // Global modifier inputs
    const modifierRow = document.createElement('div');
    modifierRow.className = 'row mb-2';
    modifierRow.innerHTML = `
        <div class="col-12"><h6 class="mt-3">Global Modifiers</h6></div>
    `;
    container.appendChild(modifierRow);
    
    for (const factoryName of Object.keys(factoryData)) {
        const row = document.createElement('div');
        row.className = 'row mb-2';
        row.innerHTML = `
            <div class="col-md-3">
                <label class="form-label">${factoryName}</label>
                <div class="input-group input-group-sm">
                    <span class="input-group-text">Speed</span>
                    <input type="number" class="form-select speed-input" data-factory="${factoryName}" value="0" step="0.1" min="-1">
                    <span class="input-group-text">Eff.</span>
                    <input type="number" class="form-select efficiency-input" data-factory="${factoryName}" value="0" step="0.1" min="-1">
                    <span class="input-group-text">Ene.</span>
                    <input type="number" class="form-select energy-input" data-factory="${factoryName}" value="1" step="0.1">
                </div>
            </div>
        `;
        container.appendChild(row);
    }
    
    // Research efficiency
    const researchRow = document.createElement('div');
    researchRow.className = 'row mb-2';
    researchRow.innerHTML = `
        <div class="col-md-6">
            <h6 class="mt-3">Research Efficiency</h6>
            <div class="row">
                <div class="col">
                    <label class="form-label">Ore</label>
                    <input type="number" class="form-select ore-research-input" value="0" step="0.1" min="0">
                </div>
                <div class="col">
                    <label class="form-label">Olumite</label>
                    <input type="number" class="form-select olumite-research-input" value="0" step="0.1" min="0">
                </div>
            </div>
        </div>
    `;
    container.appendChild(researchRow);
}

// Populate recipe override dropdowns
function populateRecipeOverrides() {
    const container = document.getElementById('recipe-overrides-container');
    container.innerHTML = '';
    
    const intro = document.createElement('div');
    intro.className = 'alert alert-info mb-3';
    intro.textContent = 'Override settings for individual recipes. Leave blank to use global settings.';
    container.appendChild(intro);
    
    for (const itemName of Object.keys(recipeData)) {
        const recipe = recipeData[itemName];
        const factory = factoryData[recipe.factory_type];
        
        const row = document.createElement('div');
        row.className = 'row mb-3';
        
        let tierOptions = '<option value="">Use Global</option>';
        factory.tiers.forEach(tier => {
            tierOptions += `<option value="${tier.name}">${tier.name}</option>`;
        });
        
        row.innerHTML = `
            <div class="col-md-12">
                <label class="form-label fw-bold">${itemName}</label>
                <div class="row">
                    <div class="col-md-3">
                        <label class="form-label small">Tier</label>
                        <select class="form-select form-select-sm override-tier" data-item="${itemName}">
                            ${tierOptions}
                        </select>
                    </div>
                    <div class="col-md-9">
                        <label class="form-label small">Modifiers</label>
                        <div class="row">
                            <div class="col">
                                <input type="number" class="form-select form-select-sm override-speed" data-item="${itemName}" placeholder="Speed" step="0.1" min="-1">
                            </div>
                            <div class="col">
                                <input type="number" class="form-select form-select-sm override-efficiency" data-item="${itemName}" placeholder="Eff." step="0.1" min="-1">
                            </div>
                            <div class="col">
                                <input type="number" class="form-select form-select-sm override-energy" data-item="${itemName}" placeholder="Ene." step="0.1">
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(row);
    }
}

// Add a new output row
function addOutputRow() {
    const container = document.getElementById('outputs-container');
    const row = document.createElement('div');
    row.className = 'row output-row align-items-end';
    
    let itemOptions = '<option value="">Select Item</option>';
    for (const itemName of Object.keys(recipeData)) {
        itemOptions += `<option value="${itemName}">${itemName}</option>`;
    }
    
    row.innerHTML = `
        <div class="col-md-4">
            <label class="form-label">Item</label>
            <select class="form-select item-select">
                ${itemOptions}
            </select>
        </div>
        <div class="col-md-5">
            <label class="form-label">Rate (/min)</label>
            <input type="number" class="form-control rate-input" value="10" step="1" min="0">
        </div>
        <div class="col-md-2">
            <button class="btn btn-outline-danger btn-sm" onclick="this.parentElement.parentElement.remove()">
                Remove
            </button>
        </div>
    `;
    container.appendChild(row);
}

// Show table view
function showTableView() {
    document.getElementById('table-view').style.display = 'block';
    document.getElementById('graph-view').style.display = 'none';
}

// Show graph view
function showGraphView() {
    document.getElementById('table-view').style.display = 'none';
    document.getElementById('graph-view').style.display = 'block';
    if (calculationResult) {
        renderGraph();
    }
}
