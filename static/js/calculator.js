// Calculator API calls and data processing

async function calculate() {
    try {
        // Gather outputs
        const outputs = [];
        document.querySelectorAll('.output-row').forEach(row => {
            const itemEl = row.querySelector('.item-select');
            const rateEl = row.querySelector('.rate-input');
            const item = itemEl ? itemEl.value : '';
            const rate = rateEl ? parseFloat(rateEl.value) : 0;
            if (item && rate > 0) {
                outputs.push({ item, rate });
            }
        });
        
        if (outputs.length === 0) {
            alert('Please add at least one output item with a rate.');
            return;
        }
        
        // Gather global tiers and robots
        const globalTiers = {};
        const globalRobots = {};
        document.querySelectorAll('.tier-select').forEach(select => {
            const factory = select.dataset.factory;
            const tier = select.value;
            if (tier) {
                globalTiers[factory] = tier;
            }
            // Get robot from the same row (empty selection → explicit no robot)
            const row = select.closest('.row');
            if (row) {
                const robotEl = row.querySelector('.robot-select');
                if (robotEl) {
                    globalRobots[factory] = robotEl.value || null;
                }
            }
        });
        
        // Gather workstation level
        const workstationLevelEl = document.querySelector('.workstation-level');
        const workstationLevel = workstationLevelEl ? (parseInt(workstationLevelEl.value, 10) || 3) : 3;
        
        // Gather research efficiency
        const oreResearchEl = document.querySelector('.ore-research-input');
        const olumiteResearchEl = document.querySelector('.olumite-research-input');
        const oreResearch = oreResearchEl ? (parseFloat(oreResearchEl.value) || 0) : 0;
        const olumiteResearch = olumiteResearchEl ? (parseFloat(olumiteResearchEl.value) || 0) : 0;
        
        // Gather fracking resolution toggle
        const frackingToggleEl = document.querySelector('.fracking-toggle');
        const resolveFracking = frackingToggleEl ? frackingToggleEl.checked : true;
        
        // Gather recipe overrides
        const recipeOverrides = {};
        document.querySelectorAll('.override-tier').forEach(select => {
            const item = select.dataset.item;
            const tier = select.value;
            const robotEl = document.querySelector(`.override-robot[data-item="${item}"]`);
            const robotVal = robotEl ? robotEl.value : '';
            
            // 'none' means explicitly no robot; '' means use global; else a robot name
            let robot;
            if (robotVal === 'none') {
                robot = null;
            } else if (robotVal === '') {
                robot = undefined;
            } else {
                robot = robotVal;
            }
            const hasOverride = tier || robot !== undefined;
            
            if (hasOverride) {
                recipeOverrides[item] = {
                    tier: tier || null,
                    robot: robot
                };
            }
        });
        
        // Build request
        const request = {
            outputs: outputs,
            global_tiers: globalTiers,
            global_robots: globalRobots,
            workstation_level: workstationLevel,
            recipe_overrides: recipeOverrides,
            research_efficiency: {
                ore: oreResearch,
                olumite: olumiteResearch
            },
            resolve_fracking: resolveFracking
        };
        
        // Call API
        const response = await fetch('/api/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Calculation failed');
        }
        
        const result = await response.json();
        calculationResult = result;
        
        // Display results
        displayResults(result);
        document.getElementById('results-section').style.display = 'block';
        
    } catch (error) {
        console.error('Calculation error:', error);
        alert('Calculation failed: ' + error.message);
    }
}

function displayResults(result) {
    displayTableView(result.results);
    displaySummary(result.results);
    // Try to render graph, but don't fail if vis isn't available yet
    try {
        renderGraph();
    } catch (error) {
        console.warn('Graph rendering failed:', error.message);
    }
}

function displayTableView(results) {
    const container = document.getElementById('table-view');
    
    let html = '<div class="table-responsive"><table class="table table-bordered table-hover">';
    html += '<thead class="table-light"><tr>';
    html += '<th>Recipe</th>';
    html += '<th>Factory</th>';
    html += '<th>Tier</th>';
    html += '<th>Count</th>';
    html += '<th>Inputs Required (/min)</th>';
    html += '<th>Outputs (/min)</th>';
    html += '<th>Power (kW)</th>';
    html += '</tr></thead><tbody>';
    
    for (const node of results.production_chain) {
        // Format inputs
        let inputsHtml = '';
        for (const [inputItem, info] of Object.entries(node.inputs_required)) {
            if (info.source === "world") {
                inputsHtml += `${formatNumber(info.rate)} ${inputItem}<br>`;
            } else {
                inputsHtml += `${formatNumber(info.rate)} ${inputItem}<br>`;
            }
        }
        if (!inputsHtml) {
            inputsHtml = '<em>Basic resource</em>';
        }
        
        // Format outputs
        let outputsHtml = '';
        for (const [outputItem, rate] of Object.entries(node.outputs_produced)) {
            outputsHtml += `${formatNumber(rate)} ${outputItem}<br>`;
        }
        
        html += '<tr>';
        html += `<td><strong>${node.recipe_name}</strong></td>`;
        html += `<td>${node.factories.type}</td>`;
        html += `<td>${node.factories.tier}</td>`;
        html += `<td>${formatNumber(node.factories.count)}</td>`;
        html += `<td>${inputsHtml}</td>`;
        html += `<td>${outputsHtml}</td>`;
        html += `<td>${formatNumber(node.power_kw)}</td>`;
        html += '</tr>';
    }
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

function displaySummary(results) {
    const container = document.getElementById('summary-content');
    
    let html = '<div class="row">';
    
    // Total power
    html += '<div class="col-md-4"><strong>Total Power:</strong><br>';
    html += `${formatNumber(results.total_power_kw)} kW`;

    // Fracking ore vein miners (only present when fracking resolution is on)
    const minerNodes = results.production_chain.filter(n => n.fracking);
    if (minerNodes.length > 0) {
        html += '<br><br><strong>Ore Miners (via fracking):</strong><br>';
        for (const n of minerNodes) {
            html += `${n.item}: ${formatNumber(n.factories.count)}×<br>`;
        }
    }
    html += '</div>';
    
    // Factory counts
    const factoryCounts = {};
    for (const node of results.production_chain) {
        const key = `${node.factories.type} (${node.factories.tier})`;
        factoryCounts[key] = (factoryCounts[key] || 0) + node.factories.count;
    }
    
    html += '<div class="col-md-4"><strong>Factories:</strong><br>';
    for (const [factory, count] of Object.entries(factoryCounts)) {
        html += `${factory}: ${formatNumber(count)}<br>`;
    }
    html += '</div>';
    
    // Raw resources
    html += '<div class="col-md-4"><strong>Raw Resources:</strong><br>';
    for (const [resource, info] of Object.entries(results.raw_resources)) {
        html += `${resource}: ${formatNumber(info.total_per_min)}/min`;
        if (info.world_consumption !== undefined) {
            html += ` (World: ${formatNumber(info.world_consumption)}/min)`;
        }
        html += '<br>';
    }
    html += '</div>';
    
    html += '</div>';
    container.innerHTML = html;
}

function formatNumber(value) {
    if (value === undefined || value === null) return '-';
    // Always use comma for thousands, period for decimals
    if (value >= 1000) {
        return Math.round(value).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }
    return value.toFixed(2);
}
