/* Diagnostic component — identify what the user knows/doesn't know, with persistence */

async function renderDiagnostic(container) {
    container.innerHTML = '<div class="text-muted">Loading diagnostic targets...</div>';

    const targets = await API.getDiagnosticTargets();
    const progress = await API.getProgress();

    // Restore in-progress ratings from session
    const savedRatings = Session.get('diagnostic_ratings', {});
    const ratings = { ...savedRatings };

    let html = `
        <h2 class="mb-2">Diagnostic: What Do You Know?</h2>
        <p class="text-muted mb-4">Rate each theorem/result below. The system will propagate your ratings to identify all your knowledge gaps.</p>
        <div class="flex-between mb-4">
            <span class="text-sm text-muted">${targets.length} items to rate &mdash; ${Object.keys(ratings).length} rated so far</span>
            <button class="btn btn-primary" id="submitDiagnostic">Analyze My Gaps</button>
        </div>
        <div id="diagnosticList"></div>
        <div id="diagnosticResult" class="hidden mt-4"></div>
    `;

    container.innerHTML = html;

    const list = document.getElementById('diagnosticList');
    const counterEl = container.querySelector('.text-sm.text-muted');

    function updateCounter() {
        counterEl.textContent = `${targets.length} items to rate — ${Object.keys(ratings).length} rated so far`;
    }

    for (const target of targets) {
        // Use saved rating, then server progress, then null
        const savedStatus = ratings[target.id] || progress.nodes?.[target.id]?.status || null;
        if (savedStatus) {
            ratings[target.id] = savedStatus;
        }

        const card = createNodeCard(target, {
            showContent: true,
            showActions: true,
            currentStatus: savedStatus,
            onRate: (nodeId, action) => {
                ratings[nodeId] = action;
                // Save in-progress ratings
                Session.set('diagnostic_ratings', ratings);
                updateCounter();
            },
        });
        card.classList.add('diagnostic-item');
        if (savedStatus) {
            card.classList.add(`rated-${savedStatus}`);
        }
        list.appendChild(card);
    }

    document.getElementById('submitDiagnostic').addEventListener('click', async () => {
        if (Object.keys(ratings).length === 0) {
            alert('Rate at least one item first!');
            return;
        }

        const result = await API.rateDiagnostic(ratings);
        // Clear saved ratings after successful submit
        Session.remove('diagnostic_ratings');

        const resultDiv = document.getElementById('diagnosticResult');
        resultDiv.classList.remove('hidden');
        resultDiv.innerHTML = `
            <div class="card" style="border-left:3px solid #58a6ff">
                <h3>Diagnostic Results</h3>
                <p class="mt-2">
                    <span class="status-unknown">${result.total_unknown} unknown</span> &middot;
                    <span class="status-shaky">${result.total_shaky} shaky</span> concepts identified
                </p>
                <div class="btn-group">
                    <button class="btn btn-primary" onclick="navigateTo('learning')">Start Learning</button>
                    <button class="btn btn-blue" onclick="navigateTo('dashboard')">View Dashboard</button>
                </div>
            </div>
        `;
    });
}
