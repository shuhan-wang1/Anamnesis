/* Renders a single knowledge node with KaTeX */

function createNodeCard(node, options = {}) {
    const {
        showContent = true,
        showActions = false,
        compact = false,
        onRate = null,
        currentStatus = null,
    } = options;

    const div = document.createElement('div');
    div.className = 'card';
    if (currentStatus) {
        div.classList.add(`rated-${currentStatus}`);
    }

    const typeName = node.type.charAt(0).toUpperCase() + node.type.slice(1);
    const badgeClass = `badge badge-${node.type}`;
    const number = node.display_number ? ` ${node.display_number}` : '';
    const title = node.title ? `: ${node.title}` : '';

    // Importance indicator
    const importance = node.importance || 0;
    let impLabel = '';
    if (importance >= 30) impLabel = '<span class="imp-badge imp-high" title="High exam importance">&#9733;&#9733;&#9733;</span>';
    else if (importance >= 20) impLabel = '<span class="imp-badge imp-med" title="Medium importance">&#9733;&#9733;</span>';
    else if (importance >= 12) impLabel = '<span class="imp-badge imp-low" title="Low importance">&#9733;</span>';

    let html = `
        <div class="card-header">
            <span class="${badgeClass}">${typeName}</span>
            <span class="card-title">${typeName}${number}${title}</span>
            ${impLabel}
            ${currentStatus ? `<span class="status-${currentStatus}" style="margin-left:auto;font-size:12px">${currentStatus}</span>` : ''}
        </div>
    `;

    if (node.section_path && node.section_path.length > 0) {
        html += `<div class="section-path"><span>${node.section_path.join(' > ')}</span> &middot; ${node.file_source || ''}</div>`;
    }

    if (showContent) {
        html += `<div class="math-content" data-math-render="true"></div>`;
    }

    // Proof section (folded under theorem/lemma/etc.)
    if (showContent && node.proof_katex) {
        html += `
            <div class="proof-section">
                <button class="proof-toggle" onclick="this.parentElement.classList.toggle('proof-open')">
                    <span class="proof-arrow">&#9654;</span> Proof
                </button>
                <div class="proof-body" data-proof-render="true"></div>
            </div>
        `;
    }

    if (showActions && onRate) {
        html += `
            <div class="btn-group">
                <button class="btn btn-primary btn-sm" data-action="known">I know this</button>
                <button class="btn btn-warning btn-sm" data-action="shaky">Shaky</button>
                <button class="btn btn-danger btn-sm" data-action="unknown">No idea</button>
            </div>
        `;
    }

    div.innerHTML = html;

    // Render main math content — content now contains HTML + math delimiters
    const mathEl = div.querySelector('[data-math-render]');
    if (mathEl) {
        mathEl.innerHTML = node.katex_content || node.latex_content || '';
        renderMath(mathEl);
    }

    // Render proof content
    const proofEl = div.querySelector('[data-proof-render]');
    if (proofEl) {
        proofEl.innerHTML = node.proof_katex || '';
        renderMath(proofEl);
    }

    // Bind actions
    if (showActions && onRate) {
        div.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                onRate(node.id, action);
                div.className = `card diagnostic-item rated-${action}`;
            });
        });
    }

    return div;
}

function showNodeModal(node) {
    // Remove existing modal
    document.querySelectorAll('.modal-overlay').forEach(m => m.remove());

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.remove();
    });

    const modal = document.createElement('div');
    modal.className = 'modal-content';

    const card = createNodeCard(node, { showContent: true });
    modal.innerHTML = '<button class="modal-close">&times;</button>';
    modal.querySelector('.modal-close').addEventListener('click', () => overlay.remove());
    modal.appendChild(card);

    overlay.appendChild(modal);
    document.body.appendChild(overlay);
}
