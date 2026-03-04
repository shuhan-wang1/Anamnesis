/* Dashboard component — exam readiness overview */

async function renderDashboard(container) {
    container.innerHTML = '<div class="text-muted">Loading dashboard...</div>';

    const [data, srData, rlData] = await Promise.all([
        API.getDashboard(),
        API.getSRSummary(),
        API.getRLStats(),
    ]);

    const readiness = data.readiness_percent;
    const knownPct = data.total > 0 ? (data.known / data.total * 100) : 0;
    const shakyPct = data.total > 0 ? (data.shaky / data.total * 100) : 0;
    const unknownPct = data.total > 0 ? (data.unknown / data.total * 100) : 0;

    let html = `
        <h2 class="mb-4">Exam Readiness</h2>

        <div class="progress-bar-container">
            <div class="progress-bar-known" style="width:${knownPct}%"></div>
            <div class="progress-bar-shaky" style="width:${shakyPct}%"></div>
            <div class="progress-bar-unknown" style="width:${unknownPct}%"></div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" style="color:#3fb950">${readiness}%</div>
                <div class="stat-label">Readiness</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color:#3fb950">${data.known}</div>
                <div class="stat-label">Known</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color:#d29922">${data.shaky}</div>
                <div class="stat-label">Shaky</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color:#f85149">${data.unknown}</div>
                <div class="stat-label">Unknown</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.total}</div>
                <div class="stat-label">Total Concepts</div>
            </div>
        </div>
    `;

    // Type breakdown
    html += '<h3 class="mb-2">By Type</h3><div class="card mb-4"><table style="width:100%;font-size:14px">';
    html += '<tr style="color:#8b949e"><td>Type</td><td>Total</td><td>Known</td><td>Shaky</td><td>Unknown</td></tr>';
    for (const [type, stats] of Object.entries(data.type_stats).sort((a, b) => b[1].total - a[1].total)) {
        html += `<tr>
            <td><span class="badge badge-${type}">${type}</span></td>
            <td>${stats.total}</td>
            <td class="status-known">${stats.known}</td>
            <td class="status-shaky">${stats.shaky}</td>
            <td class="status-unknown">${stats.unknown}</td>
        </tr>`;
    }
    html += '</table></div>';

    // File breakdown
    html += '<h3 class="mb-2">By File</h3><div class="card mb-4"><table style="width:100%;font-size:14px">';
    html += '<tr style="color:#8b949e"><td>File</td><td>Total</td><td>Known</td><td>Shaky</td><td>Unknown</td><td>Progress</td></tr>';
    for (const [file, stats] of Object.entries(data.file_stats)) {
        const pct = stats.total > 0 ? Math.round(stats.known / stats.total * 100) : 0;
        html += `<tr>
            <td style="font-size:12px">${file}</td>
            <td>${stats.total}</td>
            <td class="status-known">${stats.known}</td>
            <td class="status-shaky">${stats.shaky}</td>
            <td class="status-unknown">${stats.unknown}</td>
            <td>
                <div style="background:#21262d;border-radius:3px;height:8px;width:80px;display:inline-block">
                    <div style="background:#238636;height:100%;width:${pct}%;border-radius:3px"></div>
                </div>
                <span style="font-size:12px;color:#8b949e">${pct}%</span>
            </td>
        </tr>`;
    }
    html += '</table></div>';

    // Spaced Repetition summary
    if (srData) {
        if (srData.total_in_sr > 0) {
            const retPct = Math.round(srData.avg_retrievability * 100);
            html += `
                <div class="card mb-4" style="border-left:3px solid #58a6ff">
                    <h3>Spaced Repetition</h3>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value" style="color:#f0883e">${srData.due_for_review}</div>
                            <div class="stat-label">Due for Review</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${retPct}%</div>
                            <div class="stat-label">Avg Retention</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${srData.total_in_sr}</div>
                            <div class="stat-label">Items Tracked</div>
                        </div>
                    </div>
                    ${srData.due_for_review > 0
                        ? '<button class="btn btn-blue mt-2" onclick="navigateTo(\'quiz\')">Start Smart Review</button>'
                        : '<p class="text-muted mt-2">All caught up! No items due for review.</p>'}
                </div>
            `;
        } else {
            html += `
                <div class="card mb-4" style="border-left:3px solid #58a6ff">
                    <h3>Spaced Repetition</h3>
                    <p class="text-muted">Start reviewing items in <strong>Browse</strong> to enable Smart Review scheduling.
                    The system will track your memory and schedule optimal review times.</p>
                </div>
            `;
        }
    }

    // RL Learning stats
    if (rlData && rlData.total_interactions > 0) {
        const rlPct = Math.round(rlData.current_rl_weight * 100);
        html += `
            <div class="card mb-4" style="border-left:3px solid #a371f7">
                <h3>Adaptive Learning (RL)</h3>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value" style="color:#a371f7">${rlPct}%</div>
                        <div class="stat-label">RL Influence</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${rlData.total_interactions}</div>
                        <div class="stat-label">Total Reviews</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${rlData.nodes_with_rl_state}</div>
                        <div class="stat-label">Nodes Tracked</div>
                    </div>
                </div>
                <p class="text-muted text-sm mt-2">The system learns your knowledge gaps from each review.
                As you review more, it gets better at selecting questions you're likely to find challenging.</p>
            </div>
        `;
    }

    // Critical gaps
    if (data.critical_gaps.length > 0) {
        html += '<h3 class="mb-2">Critical Gaps (most depended on)</h3>';
        for (const gap of data.critical_gaps) {
            const typeName = gap.type.charAt(0).toUpperCase() + gap.type.slice(1);
            html += `<div class="card" style="border-left:3px solid #f85149;padding:12px">
                <span class="badge badge-${gap.type}">${typeName}</span>
                <strong>${typeName} ${gap.display_number || ''}</strong>${gap.title ? ': ' + gap.title : ''}
                <span class="text-muted text-sm"> &middot; ${gap.dependency_count} nodes depend on this</span>
            </div>`;
        }
    }

    // Quick actions
    html += `
        <div class="mt-4 btn-group">
            <button class="btn btn-blue" onclick="navigateTo('diagnostic')">Start Diagnostic</button>
            <button class="btn btn-primary" onclick="navigateTo('learning')">Start Learning</button>
            <button class="btn btn-warning" onclick="navigateTo('quiz')">Take a Quiz</button>
            <button class="btn btn-danger btn-sm" id="resetProgressBtn">Reset All Progress</button>
        </div>
    `;

    container.innerHTML = html;

    document.getElementById('resetProgressBtn')?.addEventListener('click', async () => {
        if (confirm('Reset all progress? This cannot be undone.')) {
            try {
                await API.resetProgress();
                Session.clear();
                renderDashboard(container);
            } catch (err) {
                alert('Failed to reset progress: ' + (err.message || 'Unknown error'));
            }
        }
    });
}
