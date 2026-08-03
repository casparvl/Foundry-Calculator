// Calculator API calls and data processing

async function calculate() {
    try {
        // Gather outputs
        const outputs = [];
        document.querySelectorAll('.output-row').forEach(row => {
            const item = row.querySelector('.item-select').value;
            const rate = parseFloat(row.querySelector('.rate-input').value);
            if (item && rate > 0) {
                outputs.push({ item, rate });
            }
        });
        
        if (outputs.length === 0) {
            alert('Please add at least one output item with a rate.');
            return;
        }
        
        // Gather global tiers
        const globalTiers = {};
        document.querySelectorAll('.tier-select').forEach(select => {
            const factory = select.dataset.factory;
            const tier = select.value;
            if (tier) {
                globalTiers[factory] = tier;
            }
        });
        
        // Gather global modifiers
        const globalModifiers = {};
        document.querySelectorAll('.tier-select').forEach(select => {
            const factory = select.dataset.factory;
            globalModifiers[factory] = {
                speed: parseFloat(select.closest('.row').querySelector('.speed-input').value) || 0,
                efficiency: parseFloat(select.closest('.row').querySelector('.efficiency-input').value) || 0,
                energy: parseFloat(select.closest('.row').querySelector('.energy-input').value) || 1
            };
        });
        
        // Gather research efficiency
        const oreResearch = parseFloat(document.querySelector('.ore-research-input').value) || 0;
        const olumiteResearch = parseFloat(document.querySelector('.olumite-research-input').value) || 0;
        
        // Gather recipe overrides
        const recipeOverrides = {};
        document.querySelectorAll('.override-tier').forEach(select => {
            const item = select.dataset.item;
            const tier = select.value;
            const speedEl = document.querySelector(`.override-speed[data-item="${item}"]`);
            const efficiencyEl = document.querySelector(`.override-efficiency[data-item="${item}"]`);
            const energyEl = document.querySelector(`.override-energy[data-item="${item}"]`);
            
            const hasOverride = tier || 
                (speedEl && speedEl.value !== '') || 
                (efficiencyEl && efficiencyEl.value !== '') || 
                (energyEl && energyEl.value !== '');
            
            if (hasOverride) {
                recipeOverrides[item] = {
                    tier: tier || null,
                    modifiers: {
                        speed: speedEl && speedEl.value !== '' ? parseFloat(speedEl.value) : 0,
                        efficiency: efficiencyEl && efficiencyEl.value !== '' ? parseFloat(efficiencyEl.value) : 0,
                        energy: energyEl && energyEl.value !== '' ? parseFloat(energyEl.value) : 1
                    }
                };
            }
        });
        
        // Build request
        const request = {
            outputs: outputs,
            global_tiers: globalTiers,
            global_modifiers: globalModifiers,
            recipe_overrides: recipeOverrides,
            research_efficiency: {
                ore: oreResearch,
                olumite: olumiteResearch
            }
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
}

function displayTableView(results) {
    const container = document.getElementById('table-view');
    
    let html = '<div class="table-responsive"><table class="table table-bordered table-hover">';
    html += '<thead class="table-light"><tr>';
    html += '<th>Item</th>';
    html += '<th>Factory</th>';
    html += '<th>Tier</th>';
    html += '<th>Count</th>';
    html += '<th>Inputs Required (/min)</th>';
    html += '<th>Power (kW)</th>';
    html += '</tr></thead><tbody>';
    
    for (const node of results.production_chain) {
        // Format inputs
        let inputsHtml = '';
        for (const [inputItem, info] of Object.entries(node.inputs_required)) {
            inputsHtml += `${formatNumber(info.rate)} ${inputItem}<br>`;
        }
        if (!inputsHtml) {
            inputsHtml = '<em>Basic resource</em>';
        }
        
        html += '<tr>';
        html += `<td><strong>${node.item}</strong></td>`;
        html += `<td>${node.factories.type}</td>`;
        html += `<td>${node.factories.tier}</td>`;
        html += `<td>${formatNumber(node.factories.count)}</td>`;
        html += `<td>${inputsHtml}</td>`;
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
    html += `${formatNumber(results.total_power_kw)} kW</div>`;
    
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
    if (value >= 1000) return Math.round(value).toLocaleString();
    return value.toFixed(2);
}
