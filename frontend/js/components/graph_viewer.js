/* D3.js dependency graph viewer */

const TYPE_COLORS = {
    definition: '#58a6ff',
    theorem: '#3fb950',
    lemma: '#d29922',
    corollary: '#bc8cff',
    proposition: '#bc8cff',
    proof: '#8b949e',
    'proof-sketch': '#8b949e',
    example: '#56d4dd',
    remark: '#8b949e',
    algorithm: '#f85149',
    exercise: '#d29922',
    problem: '#d29922',
    note: '#8b949e',
    warning: '#f85149',
    question: '#d29922',
    claim: '#3fb950',
};

const TYPE_SIZES = {
    definition: 8,
    theorem: 12,
    lemma: 10,
    corollary: 9,
    proposition: 10,
    proof: 6,
    'proof-sketch': 6,
    example: 7,
    remark: 6,
    algorithm: 9,
};

async function renderGraphViewer(container) {
    container.innerHTML = '<div class="text-muted">Loading graph...</div>';

    const graphData = await API.getGraph();
    const progress = await API.getProgress();

    // Filter controls
    let html = `
        <h2 class="mb-2">Dependency Graph</h2>
        <div class="browse-filters mb-2">
            <select id="graphFilterType">
                <option value="all">All types</option>
                <option value="core" selected>Core (def/thm/lem)</option>
                <option value="definition">Definitions</option>
                <option value="theorem">Theorems</option>
                <option value="lemma">Lemmas</option>
            </select>
            <select id="graphFilterFile">
                <option value="all">All files</option>
            </select>
            <button class="btn btn-sm" id="graphRefresh">Refresh</button>
        </div>
        <div class="graph-container" id="graphContainer" style="height:600px">
            <div class="graph-legend">
                <div class="legend-item"><div class="legend-dot" style="background:#58a6ff"></div> Definition</div>
                <div class="legend-item"><div class="legend-dot" style="background:#3fb950"></div> Theorem</div>
                <div class="legend-item"><div class="legend-dot" style="background:#d29922"></div> Lemma</div>
                <div class="legend-item"><div class="legend-dot" style="background:#bc8cff"></div> Corollary/Prop</div>
                <div class="legend-item"><div class="legend-dot" style="background:#56d4dd"></div> Example</div>
            </div>
            <div class="graph-tooltip" id="graphTooltip"></div>
        </div>
    `;

    container.innerHTML = html;

    // Populate file filter
    const files = [...new Set(graphData.nodes.map(n => n.file_source))];
    const fileSelect = document.getElementById('graphFilterFile');
    files.forEach(f => {
        const opt = document.createElement('option');
        opt.value = f;
        opt.textContent = f;
        fileSelect.appendChild(opt);
    });

    function getFilteredData() {
        const typeFilter = document.getElementById('graphFilterType').value;
        const fileFilter = document.getElementById('graphFilterFile').value;

        let filteredNodes = graphData.nodes;

        if (typeFilter === 'core') {
            filteredNodes = filteredNodes.filter(n =>
                ['definition', 'theorem', 'lemma', 'corollary', 'proposition'].includes(n.type)
            );
        } else if (typeFilter !== 'all') {
            filteredNodes = filteredNodes.filter(n => n.type === typeFilter);
        }

        if (fileFilter !== 'all') {
            filteredNodes = filteredNodes.filter(n => n.file_source === fileFilter);
        }

        const nodeIds = new Set(filteredNodes.map(n => n.id));
        const filteredEdges = graphData.edges.filter(e =>
            nodeIds.has(e.source) && nodeIds.has(e.target)
        );

        return { nodes: filteredNodes, edges: filteredEdges };
    }

    function drawGraph() {
        const graphContainer = document.getElementById('graphContainer');
        // Remove old SVG
        graphContainer.querySelectorAll('svg').forEach(s => s.remove());

        const filtered = getFilteredData();
        if (filtered.nodes.length === 0) return;

        const width = graphContainer.clientWidth;
        const height = 600;

        const svg = d3.select('#graphContainer')
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        // Arrow marker
        svg.append('defs').append('marker')
            .attr('id', 'arrow')
            .attr('viewBox', '0 0 10 10')
            .attr('refX', 20)
            .attr('refY', 5)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M 0 0 L 10 5 L 0 10 z')
            .attr('fill', '#30363d');

        // Deep clone nodes/edges for D3 (it mutates them)
        const nodes = filtered.nodes.map(n => ({ ...n }));
        const edges = filtered.edges.map(e => ({ ...e }));

        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(edges).id(d => d.id).distance(80))
            .force('charge', d3.forceManyBody().strength(-150))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(20));

        const g = svg.append('g');

        // Zoom
        svg.call(d3.zoom().scaleExtent([0.2, 4]).on('zoom', (event) => {
            g.attr('transform', event.transform);
        }));

        const links = g.selectAll('.link')
            .data(edges)
            .join('line')
            .attr('class', 'link')
            .attr('stroke', '#30363d')
            .attr('stroke-width', 1)
            .attr('marker-end', 'url(#arrow)');

        const nodeGroups = g.selectAll('.node')
            .data(nodes)
            .join('g')
            .attr('class', 'node')
            .call(d3.drag()
                .on('start', (event, d) => {
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    d.fx = d.x; d.fy = d.y;
                })
                .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
                .on('end', (event, d) => {
                    if (!event.active) simulation.alphaTarget(0);
                    d.fx = null; d.fy = null;
                })
            );

        nodeGroups.append('circle')
            .attr('r', d => TYPE_SIZES[d.type] || 7)
            .attr('fill', d => {
                const status = progress.nodes?.[d.id]?.status;
                if (status === 'known') return TYPE_COLORS[d.type] || '#8b949e';
                if (status === 'shaky') return TYPE_COLORS[d.type] || '#8b949e';
                return TYPE_COLORS[d.type] || '#8b949e';
            })
            .attr('stroke', d => {
                const status = progress.nodes?.[d.id]?.status;
                if (status === 'known') return '#3fb950';
                if (status === 'shaky') return '#d29922';
                return '#30363d';
            })
            .attr('stroke-width', d => {
                const status = progress.nodes?.[d.id]?.status;
                return (status === 'known' || status === 'shaky') ? 2 : 1;
            })
            .attr('opacity', d => {
                const status = progress.nodes?.[d.id]?.status;
                if (status === 'known') return 1;
                if (status === 'shaky') return 0.7;
                return 0.5;
            });

        nodeGroups.append('text')
            .text(d => {
                const prefix = d.type[0].toUpperCase();
                return `${prefix}${d.display_number || ''}`;
            })
            .attr('dx', 14)
            .attr('dy', 4)
            .attr('font-size', 10)
            .attr('fill', '#8b949e');

        // Tooltip
        const tooltip = document.getElementById('graphTooltip');

        nodeGroups.on('mouseover', (event, d) => {
            const typeName = d.type.charAt(0).toUpperCase() + d.type.slice(1);
            tooltip.style.display = 'block';
            tooltip.innerHTML = `<strong>${typeName} ${d.display_number || ''}</strong>${d.title ? '<br>' + d.title : ''}<br><span class="text-muted">${d.file_source || ''}</span>`;
            tooltip.style.left = (event.offsetX + 15) + 'px';
            tooltip.style.top = (event.offsetY - 10) + 'px';
        });

        nodeGroups.on('mouseout', () => {
            tooltip.style.display = 'none';
        });

        nodeGroups.on('click', async (event, d) => {
            const fullNode = await API.getNode(d.id);
            showNodeModal(fullNode);
        });

        simulation.on('tick', () => {
            links
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            nodeGroups.attr('transform', d => `translate(${d.x},${d.y})`);
        });
    }

    drawGraph();

    document.getElementById('graphRefresh').addEventListener('click', drawGraph);
    document.getElementById('graphFilterType').addEventListener('change', drawGraph);
    document.getElementById('graphFilterFile').addEventListener('change', drawGraph);
}
