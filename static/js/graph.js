// Graph visualization using vis.js

let network = null;

function renderGraph() {
    if (!calculationResult) return;
    
    const results = calculationResult.results;
    
    // Create nodes and edges
    const nodes = [];
    const edges = [];
    
    // Track which nodes we've seen
    const nodeIds = new Set();
    
    // Add production chain nodes
    for (const node of results.production_chain) {
        const nodeId = `product_${node.item}`;
        if (!nodeIds.has(nodeId)) {
            nodes.push({
                id: nodeId,
                label: `${node.item}\n${formatNumber(node.requested_rate)}/min`,
                group: 'product',
                title: `Produced at ${formatNumber(node.requested_rate)} per minute`
            });
            nodeIds.add(nodeId);
        }
        
        // Add edges from inputs
        for (const [inputItem, info] of Object.entries(node.inputs_required)) {
            const sourceId = `product_${inputItem}`;
            
            // If input is a basic resource, create a separate node
            if (info.source === 'recipe') {
                if (!nodeIds.has(sourceId)) {
                    nodes.push({
                        id: sourceId,
                        label: `${inputItem}\n${formatNumber(info.rate)}/min`,
                        group: 'intermediate',
                        title: `Required: ${formatNumber(info.rate)} per minute`
                    });
                    nodeIds.add(sourceId);
                }
                
                edges.push({
                    from: sourceId,
                    to: nodeId,
                    label: formatNumber(info.rate),
                    arrows: 'to',
                    smooth: { type: 'curved', roundness: 0.2 }
                });
            }
        }
    }
    
    // Add raw resource nodes
    for (const [resource, info] of Object.entries(results.raw_resources)) {
        const resourceId = `resource_${resource}`;
        if (!nodeIds.has(resourceId)) {
            const group = info.type === 'ore' ? 'ore' : (info.type === 'olumite' ? 'olumite' : 'basic');
            nodes.push({
                id: resourceId,
                label: `${resource}\n${formatNumber(info.world_consumption || info.total_per_min)}/min`,
                group: group,
                title: `World consumption: ${formatNumber(info.world_consumption || info.total_per_min)} per minute`
            });
            nodeIds.add(resourceId);
        }
    }
    
    // Set up graph options
    const options = {
        nodes: {
            shape: 'box',
            font: {
                size: 14,
                multi: true
            },
            margin: 10
        },
        edges: {
            font: {
                align: 'middle',
                size: 12
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
            basic: { color: { background: '#9E9E9E', border: '#616161' } },
            intermediate: { color: { background: '#FF9800', border: '#F57C00' } },
            product: { color: { background: '#9C27B0', border: '#7B1FA2' } }
        },
        layout: {
            hierarchical: {
                direction: 'LR',
                sortMethod: 'directed',
                levelSeparation: 250,
                nodeSpacing: 150
            }
        },
        physics: {
            hierarchicalRepulsion: {
                nodeDistance: 150
            }
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
}
