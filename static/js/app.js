// Main frontend logic for the Foundry Calculator

let factoryData = {};
let recipeData = {};
let robotData = {};
let calculationResult = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', async function() {
    // Add output row immediately (before config loads)
    addOutputRow();
    
    // Load config in background
    await loadConfiguration();
});

// Load factory and recipe configurations from API (single attempt)
async function loadConfiguration() {
    const outputsContainer = document.getElementById('outputs-container');
    if (outputsContainer) {
        outputsContainer.innerHTML = '';
    }
    
    try {
        const [factoriesResponse, recipesResponse, robotsResponse] = await Promise.all([
            fetch('/api/factories'),
            fetch('/api/recipes'),
            fetch('/api/robots')
        ]);
        
        if (!factoriesResponse.ok || !recipesResponse.ok || !robotsResponse.ok) {
            throw new Error('API not ready');
        }
        
        factoryData = await factoriesResponse.json();
        recipeData = await recipesResponse.json();
        robotData = await robotsResponse.json();
        
        // Hide error messages on success
        const msg = document.getElementById('config-error-message');
        if (msg) {
            msg.classList.add('d-none');
        }
        
        // Populate settings and add output row
        populateGlobalSettings();
        populateRecipeOverrides();
        addOutputRow(); // Add first output row after config loads
        
    } catch (error) {
        console.error('Failed to load configuration:', error);
        const msg = document.getElementById('config-error-message');
        if (msg) {
            msg.classList.remove('d-none');
        }
    }
}

// Retry configuration loading (manual trigger)
async function retryConfiguration() {
    await loadConfiguration();
}

// Populate global settings dropdowns and inputs
function populateGlobalSettings() {
    const container = document.getElementById('global-settings-container');
    container.innerHTML = '';
    
    // Robot workstation level
    const wsRow = document.createElement('div');
    wsRow.className = 'row mb-3';
    wsRow.innerHTML = `
        <div class="col-md-3">
            <label class="form-label fw-bold">Robot Workstation Level</label>
            <select class="form-select workstation-level" value="3">
                <option value="1">Workstation I</option>
                <option value="2">Workstation II</option>
                <option value="3" selected>Workstation III</option>
            </select>
        </div>
    `;
    container.appendChild(wsRow);
    
    // Factory tier selections
    const tierRow = document.createElement('div');
    tierRow.className = 'row mb-3';
    tierRow.innerHTML = '<div class="col-12"><h6>Factory Tiers</h6></div>';
    container.appendChild(tierRow);
    
    for (const factoryName of Object.keys(factoryData)) {
        const factory = factoryData[factoryName];
        const row = document.createElement('div');
        row.className = 'row mb-2';
        
        let tierHtml;
        if (factory.tiers.length === 1) {
            // Single-tier factory: no dropdown, show tier as plain text
            tierHtml = `
                <div class="form-control-plaintext py-1">${factory.tiers[0].name}</div>
                <input type="hidden" class="tier-select" data-factory="${factoryName}" value="${factory.tiers[0].name}">
            `;
        } else {
            // Multi-tier factory: default to the highest tier
            let tierOptions = '';
            factory.tiers.forEach((tier, index) => {
                tierOptions += `<option value="${tier.name}" ${index === factory.tiers.length - 1 ? 'selected' : ''}>${tier.name}</option>`;
            });
            tierHtml = `
                <select class="form-select tier-select" data-factory="${factoryName}">
                    ${tierOptions}
                </select>
            `;
        }
        
        row.innerHTML = `
            <div class="col-md-4">
                <label class="form-label">${factoryName}</label>
                ${tierHtml}
            </div>
            <div class="col-md-8">
                <label class="form-label">Robot</label>
                ${robotSelectHtml(factoryName, 'robot-select')}
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

// Build a robot dropdown for a factory (used in global settings)
function robotSelectHtml(factoryName, className) {
    const info = (robotData.factories || {})[factoryName];
    const robots = (info && info.robots) ? info.robots : [];
    const defaultValue = (info && info.default) ? info.default : '';
    
    let options = `<option value="">None (no robot)</option>`;
    for (const robotName of robots) {
        const robot = (robotData.robots || {})[robotName];
        const label = robot
            ? `${robotName} (${robot.buff_type === 'speed' ? 'Speed' : 'Efficiency'} +${Math.round(robot.buff_percentage * 100)}%)`
            : robotName;
        const selected = robotName === defaultValue ? 'selected' : '';
        options += `<option value="${robotName}" ${selected}>${label}</option>`;
    }
    return `<select class="form-select ${className}" data-factory="${factoryName}">${options}</select>`;
}

// Populate recipe override dropdowns (defensive: skip recipes with missing factory)
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
        
        // Skip recipes whose factory isn't defined (graceful degradation)
        if (!factory) {
            console.warn(`Skipping recipe "${itemName}" - factory "${recipe.factory_type}" not defined in factories.json`);
            continue;
        }
        
        const row = document.createElement('div');
        row.className = 'row mb-3';
        
        let tierHtml;
        if (factory.tiers.length === 1) {
            // Single-tier factory: no dropdown, show tier as plain text
            // (hidden empty override-tier keeps "Use Global" semantics and modifier collection)
            tierHtml = `
                <div class="form-control-plaintext py-1">${factory.tiers[0].name}</div>
                <input type="hidden" class="override-tier" data-item="${itemName}" value="">
            `;
        } else {
            let tierOptions = '<option value="">Use Global</option>';
            factory.tiers.forEach(tier => {
                tierOptions += `<option value="${tier.name}">${tier.name}</option>`;
            });
            tierHtml = `
                <select class="form-select form-select-sm override-tier" data-item="${itemName}">
                    ${tierOptions}
                </select>
            `;
        }
        
        row.innerHTML = `
            <div class="col-md-12">
                <label class="form-label fw-bold">${itemName}</label>
                <div class="row">
                    <div class="col-md-3">
                        <label class="form-label small">Tier</label>
                        ${tierHtml}
                    </div>
                    <div class="col-md-5">
                        <label class="form-label small">Robot</label>
                        <select class="form-select form-select-sm override-robot" data-item="${itemName}" data-factory="${recipe.factory_type}">
                            <option value="">Use Global</option>
                            <option value="none">None (no robot)</option>
                            ${recipeRobotOptions(recipe.factory_type)}
                        </select>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(row);
    }
}

// Robot options for a recipe's factory (for per-recipe override dropdown)
function recipeRobotOptions(factoryName) {
    const info = (robotData.factories || {})[factoryName];
    const robots = (info && info.robots) ? info.robots : [];
    let options = '';
    for (const robotName of robots) {
        const robot = (robotData.robots || {})[robotName];
        const label = robot
            ? `${robotName} (${robot.buff_type === 'speed' ? 'Speed' : 'Efficiency'} +${Math.round(robot.buff_percentage * 100)}%)`
            : robotName;
        options += `<option value="${robotName}">${label}</option>`;
    }
    return options;
}

// Add a new output row
function addOutputRow() {
    const container = document.getElementById('outputs-container');
    if (!container) return;
    
    const row = document.createElement('div');
    row.className = 'row output-row align-items-end';
    
    let itemOptions = '<option value="">Select Item</option>';
    const productNames = new Set();
    for (const recipe of Object.values(recipeData)) {
        for (const outItem of Object.keys(recipe.outputs || {})) {
            productNames.add(outItem);
        }
    }
    for (const itemName of [...productNames].sort()) {
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
