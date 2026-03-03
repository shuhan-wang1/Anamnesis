/* Browse component — browse all concepts with filters, with persistence */

async function renderBrowse(container) {
    container.innerHTML = '<div class="text-muted">Loading...</div>';

    const [allNodes, progress] = await Promise.all([
        API.get('/api/nodes'),
        API.getProgress(),
    ]);
    const graphData = { nodes: allNodes };

    const files = [...new Set(graphData.nodes.map(n => n.file_source))];
    const types = [...new Set(graphData.nodes.map(n => n.type))].sort();

    // Restore saved filters
    const savedFilters = Session.get('browse_filters', {});

    let html = `
        <h2 class="mb-4">Browse All Concepts</h2>
        <div class="browse-filters">
            <select id="browseType">
                <option value="all">All types</option>
                ${types.map(t => `<option value="${t}" ${savedFilters.type === t ? 'selected' : ''}>${t.charAt(0).toUpperCase() + t.slice(1)}</option>`).join('')}
            </select>
            <select id="browseFile">
                <option value="all">All files</option>
                ${files.map(f => `<option value="${f}" ${savedFilters.file === f ? 'selected' : ''}>${f}</option>`).join('')}
            </select>
            <select id="browseStatus">
                <option value="all">All statuses</option>
                <option value="unknown" ${savedFilters.status === 'unknown' ? 'selected' : ''}>Unknown</option>
                <option value="shaky" ${savedFilters.status === 'shaky' ? 'selected' : ''}>Shaky</option>
                <option value="known" ${savedFilters.status === 'known' ? 'selected' : ''}>Known</option>
            </select>
            <input type="text" id="browseSearch" placeholder="Search..." style="flex:1;min-width:150px" value="${savedFilters.search || ''}">
        </div>
        <div class="text-sm text-muted mb-2" id="browseCount"></div>
        <div id="browseList" class="browse-list"></div>
    `;

    container.innerHTML = html;

    function saveFilters() {
        Session.set('browse_filters', {
            type: document.getElementById('browseType').value,
            file: document.getElementById('browseFile').value,
            status: document.getElementById('browseStatus').value,
            search: document.getElementById('browseSearch').value,
        });
    }

    function filterAndRender() {
        const typeFilter = document.getElementById('browseType').value;
        const fileFilter = document.getElementById('browseFile').value;
        const statusFilter = document.getElementById('browseStatus').value;
        const search = document.getElementById('browseSearch').value.toLowerCase();

        saveFilters();

        let nodes = graphData.nodes;

        if (typeFilter !== 'all') {
            nodes = nodes.filter(n => n.type === typeFilter);
        }
        if (fileFilter !== 'all') {
            nodes = nodes.filter(n => n.file_source === fileFilter);
        }
        if (statusFilter !== 'all') {
            nodes = nodes.filter(n => {
                const s = progress.nodes?.[n.id]?.status || 'unknown';
                return s === statusFilter;
            });
        }
        if (search) {
            nodes = nodes.filter(n =>
                (n.title || '').toLowerCase().includes(search) ||
                (n.type || '').toLowerCase().includes(search) ||
                (n.display_number || '').includes(search) ||
                (n.katex_content || '').toLowerCase().includes(search)
            );
        }

        document.getElementById('browseCount').textContent = `${nodes.length} concepts`;

        const list = document.getElementById('browseList');
        list.innerHTML = '';

        const displayed = nodes.slice(0, 50);
        for (const node of displayed) {
            const status = progress.nodes?.[node.id]?.status || 'unknown';
            const card = createNodeCard(node, {
                showContent: true,
                showActions: true,
                currentStatus: status,
                onRate: async (nodeId, action) => {
                    await API.updateProgress(nodeId, action, 'browse');
                    progress.nodes = progress.nodes || {};
                    progress.nodes[nodeId] = progress.nodes[nodeId] || {};
                    progress.nodes[nodeId].status = action;
                },
            });
            list.appendChild(card);
        }

        if (nodes.length > 50) {
            const more = document.createElement('p');
            more.className = 'text-muted text-sm mt-2';
            more.textContent = `Showing 50 of ${nodes.length} results. Use filters to narrow down.`;
            list.appendChild(more);
        }
    }

    document.getElementById('browseType').addEventListener('change', filterAndRender);
    document.getElementById('browseFile').addEventListener('change', filterAndRender);
    document.getElementById('browseStatus').addEventListener('change', filterAndRender);
    document.getElementById('browseSearch').addEventListener('input', filterAndRender);

    filterAndRender();
}
