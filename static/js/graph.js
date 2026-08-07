// Graph visualization using vis.js

let network = null;

function renderGraph() {
    if (!calculationResult) return;
    
    // Check if vis library is available
    if (typeof vis === 'undefined' || !vis.Network) {
        console.warn('Graph view not available - vis library not loaded');
        return;
    }
    
    try {
        const results = calculationResult.results;
        
        // Create nodes and edges
        const nodes = [];
        const edges = [];
        
        // Track which nodes we've seen
        const nodeIds = new Set();
        
        // Map each output item to the recipe node that produces it
        const producerMap = {};
        for (const node of results.production_chain) {
            const nodeId = `recipe_${node.recipe_name}`;
            for (const outputItem of Object.keys(node.outputs_produced || {})) {
                producerMap[outputItem] = nodeId;
            }
        }
        
        // Add factory/recipe nodes (one per recipe, lists factory count)
        for (const node of results.production_chain) {
            const nodeId = `recipe_${node.recipe_name}`;
            if (!nodeIds.has(nodeId)) {
                // Fracking ore-vein nodes run on olumite-derived fracking fluid;
                // color them like raw ore resources so the mined ore stays visible.
                const group = node.fracking ? 'miner' : 'product';
                const title = node.fracking
                    ? `${node.recipe_name} — ${formatNumber(node.factories.count)} factories at ${formatNumber(node.requested_rate)}/min (via fracking)`
                    : `${node.recipe_name} — ${formatNumber(node.factories.count)} factories at ${formatNumber(node.requested_rate)}/min`;
                nodes.push({
                    id: nodeId,
                    label: `${node.factories.type} (${node.factories.tier})\n${formatNumber(node.factories.count)}×`,
                    group: group,
                    title: title
                });
                nodeIds.add(nodeId);
            }
        }
        
        // Recipe-to-recipe edges (each labeled with the consumer's input ingredient + rate)
        for (const node of results.production_chain) {
            const targetId = `recipe_${node.recipe_name}`;
            for (const [inputItem, info] of Object.entries(node.inputs_required || {})) {
                if (info.source !== 'recipe') continue;
                const sourceId = producerMap[inputItem] || `resource_${inputItem}`;
                edges.push({
                    from: sourceId,
                    to: targetId,
                    label: `${inputItem}\n${formatNumber(info.rate)}/min`,
                    arrows: 'to',
                    smooth: { type: 'curved', roundness: 0.2 }
                });
            }
        }
        
        // Add raw resource (world input) nodes and edges
        for (const [resource, info] of Object.entries(results.raw_resources || {})) {
            const resourceId = `resource_${resource}`;
            if (!nodeIds.has(resourceId)) {
                const group = info.type === 'ore' ? 'ore' : (info.type === 'olumite' ? 'olumite' : (info.type === 'infinite' ? 'infinite' : 'basic'));
                nodes.push({
                    id: resourceId,
                    label: `${resource}\n${formatNumber(info.world_consumption || info.total_per_min)}/min`,
                    group: group,
                    title: `World consumption: ${formatNumber(info.world_consumption || info.total_per_min)} per minute`
                });
                nodeIds.add(resourceId);
            }
            
            // Find which recipe uses this resource and add edge
            for (const node of results.production_chain) {
                if (node.inputs_required && node.inputs_required[resource]) {
                    edges.push({
                        from: resourceId,
                        to: `recipe_${node.recipe_name}`,
                        label: `${resource}\n${formatNumber(node.inputs_required[resource].rate)}/min`,
                        arrows: 'to',
                        dashes: true
                    });
                }
            }
        }
        
        // Add requested-output endpoint nodes (only for items with a producing recipe)
        for (const output of (results.requested_outputs || [])) {
            const item = output.item;
            const sourceId = producerMap[item];
            // If the requested item has no producing recipe (basic resource), its world
            // node already serves as the endpoint; skip to avoid a dangling edge.
            if (!sourceId) continue;
            const outputId = `output_${item}`;
            if (!nodeIds.has(outputId)) {
                nodes.push({
                    id: outputId,
                    label: `${item}\n${formatNumber(output.rate)}/min`,
                    group: 'output',
                    title: `Requested output: ${formatNumber(output.rate)} per minute`
                });
                nodeIds.add(outputId);
            }
            edges.push({
                from: sourceId,
                to: outputId,
                label: `${item}\n${formatNumber(output.rate)}/min`,
                arrows: 'to'
            });
        }
        
        // Set up graph options
        const options = {
            nodes: {
                shape: 'box',
                widthConstraint: {
                    maximum: 160
                },
                font: {
                    size: 14,
                    multi: true
                },
                margin: 10
            },
            edges: {
                font: {
                    align: 'middle',
                    size: 12,
                    multi: true
                },
                arrows: {
                    to: {
                        enabled: true,
                        scaleFactor: 1
                    }
                }
            },
            groups: {
                ore: { color: { background: '#4CAF50', border: '#2E7D32' } },
                olumite: { color: { background: '#2196F3', border: '#1565C0' } },
                infinite: { color: { background: '#00BCD4', border: '#0097A7' } },
                basic: { color: { background: '#9E9E9E', border: '#616161' } },
                product: { color: { background: '#9C27B0', border: '#7B1FA2' } },
                miner: { color: { background: '#4CAF50', border: '#2E7D32' } },
                output: { color: { background: '#FF5722', border: '#BF360C' } }
            },
            layout: {
                hierarchical: {
                    direction: 'LR',
                    sortMethod: 'directed',
                    levelSeparation: 400,
                    nodeSpacing: 300,
                    treeSpacing: 250
                }
            },
            physics: {
                enabled: false
            },
            interaction: {
                freezeDuringDrag: true
            }
        };
        
        // Create network
        const container = document.getElementById('network');
        const data = {
            nodes: new vis.DataSet(nodes),
            edges: new vis.DataSet(edges)
        };
        
        if (network) {
            network.destroy();
        }
        
        network = new vis.Network(container, data, options);
    } catch (error) {
        console.error('Error rendering graph:', error);
    }
}
