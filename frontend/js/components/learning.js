/* Learning mode — curated study plan organized by topics, with persistence */

async function renderLearning(container) {
    container.innerHTML = '<div class="text-muted">Loading study plan...</div>';

    const data = await API.get('/api/learning/study-plan');

    if (!data.topics || data.topics.length === 0) {
        container.innerHTML = `
            <h2 class="mb-4">Study Plan</h2>
            <div class="card"><p>No concepts found. Make sure the knowledge graph is built.</p></div>
        `;
        return;
    }

    const totalNodes = data.total_nodes;
    const totalKnown = data.total_known;
    const pct = totalNodes > 0 ? Math.round(totalKnown / totalNodes * 100) : 0;

    // Restore saved view preference
    const savedView = Session.get('learning_view', 'topics');

    let html = `
        <h2 class="mb-2">Study Plan</h2>
        <p class="text-muted text-sm mb-4">
            ${totalKnown} / ${totalNodes} key concepts mastered (${pct}%)
            &mdash; Curated by exam importance
        </p>

        <div class="progress-bar-container mb-4" style="height:8px">
            <div class="progress-bar-known" style="width:${pct}%"></div>
        </div>

        <div class="study-view-toggle mb-4">
            <button class="btn btn-sm ${savedView === 'topics' ? 'active' : ''}" id="viewTopics">By Topic</button>
            <button class="btn btn-sm ${savedView === 'path' ? 'active' : ''}" id="viewPath">Focus Path</button>
        </div>

        <div id="studyContent"></div>
    `;

    container.innerHTML = html;

    const contentEl = document.getElementById('studyContent');

    // Render topic view
    function renderTopicView() {
        document.getElementById('viewTopics').classList.add('active');
        document.getElementById('viewPath').classList.remove('active');
        Session.set('learning_view', 'topics');

        // Restore which topics were expanded
        const expandedTopics = Session.get('learning_expanded', []);

        let topicHtml = '';
        data.topics.forEach((topic, idx) => {
            const topicPct = topic.total > 0 ? Math.round(topic.known / topic.total * 100) : 0;
            const unknownCount = topic.total - topic.known - topic.shaky;
            const isOpen = expandedTopics.includes(idx);

            topicHtml += `
                <div class="topic-section card ${isOpen ? 'topic-open' : ''}" data-section-idx="${idx}">
                    <div class="topic-header">
                        <span class="proof-arrow">&#9654;</span>
                        <span class="topic-title">${topic.section}</span>
                        <span class="topic-stats">
                            <span class="text-sm">${topic.known}/${topic.total} mastered</span>
                            ${unknownCount > 0 ? `<span class="text-sm status-unknown">${unknownCount} to learn</span>` : ''}
                        </span>
                        <div class="topic-bar">
                            <div class="topic-bar-fill" style="width:${topicPct}%"></div>
                        </div>
                    </div>
                    <div class="topic-body" data-topic-idx="${idx}"></div>
                </div>
            `;
        });
        contentEl.innerHTML = topicHtml;

        // Bind topic toggle with persistence
        contentEl.querySelectorAll('.topic-header').forEach(header => {
            header.addEventListener('click', () => {
                const section = header.closest('.topic-section');
                section.classList.toggle('topic-open');
                // Save expanded state
                const expanded = [];
                contentEl.querySelectorAll('.topic-section.topic-open').forEach(s => {
                    expanded.push(parseInt(s.dataset.sectionIdx));
                });
                Session.set('learning_expanded', expanded);
            });
        });

        // Render nodes into each topic body
        data.topics.forEach((topic, idx) => {
            const body = contentEl.querySelector(`[data-topic-idx="${idx}"]`);
            if (!body) return;

            for (const node of topic.nodes) {
                const card = createNodeCard(node, {
                    showContent: false,
                    compact: true,
                    currentStatus: node.status !== 'unknown' ? node.status : null,
                });
                card.style.cursor = 'pointer';
                card.addEventListener('click', () => showStudyNode(node));
                body.appendChild(card);
            }
        });

        // If nothing was expanded, auto-open first topic with unknowns
        if (expandedTopics.length === 0) {
            const firstIdx = data.topics.findIndex(t => t.known < t.total);
            if (firstIdx >= 0) {
                const el = contentEl.querySelector(`[data-section-idx="${firstIdx}"]`);
                if (el) {
                    el.classList.add('topic-open');
                    Session.set('learning_expanded', [firstIdx]);
                }
            }
        }
    }

    // Render focus path view
    async function renderFocusPath() {
        document.getElementById('viewPath').classList.add('active');
        document.getElementById('viewTopics').classList.remove('active');
        Session.set('learning_view', 'path');

        contentEl.innerHTML = '<div class="text-muted">Building focus path...</div>';

        const autoData = await API.getAutoLearningPath();

        if (!autoData.path || autoData.path.length === 0) {
            Session.remove('learning_path');
            contentEl.innerHTML = `
                <div class="card" style="border-left:3px solid #238636">
                    <h3>All caught up!</h3>
                    <p class="mt-2 text-muted">All key theorems are marked as known. Try the quiz to test yourself.</p>
                    <div class="btn-group">
                        <button class="btn btn-warning" onclick="navigateTo('quiz')">Take a Quiz</button>
                    </div>
                </div>
            `;
            return;
        }

        // Restore step position if same target
        const savedPath = Session.get('learning_path');
        let currentStep = 0;
        if (savedPath && savedPath.target_id === autoData.target_id && savedPath.step < autoData.path.length) {
            currentStep = savedPath.step;
        }

        const path = autoData.path;

        function renderStep() {
            // Save current step
            Session.set('learning_path', { target_id: autoData.target_id, step: currentStep });

            const node = path[currentStep];
            const progress = ((currentStep) / path.length * 100).toFixed(0);

            let stepHtml = `
                <div class="mb-4">
                    <p class="text-muted text-sm">
                        Working toward: <strong>${autoData.target?.title || autoData.target?.display_number || autoData.target_id}</strong>
                    </p>
                    <div class="learning-progress">
                        <div class="learning-progress-bar">
                            <div class="learning-progress-fill" style="width:${progress}%"></div>
                        </div>
                        <span class="learning-step-counter">Step ${currentStep + 1} / ${path.length}</span>
                    </div>
                </div>
            `;

            contentEl.innerHTML = stepHtml;

            const card = createNodeCard(node, { showContent: true });
            contentEl.appendChild(card);

            const btnGroup = document.createElement('div');
            btnGroup.className = 'btn-group';
            btnGroup.innerHTML = `
                <button class="btn" id="prevStep" ${currentStep === 0 ? 'disabled' : ''}>Back</button>
                <button class="btn btn-primary" id="understood">I understand &rarr;</button>
                <button class="btn btn-warning" id="shaky">Shaky</button>
            `;
            contentEl.appendChild(btnGroup);

            document.getElementById('prevStep').addEventListener('click', () => {
                if (currentStep > 0) { currentStep--; renderStep(); }
            });

            const advance = async (status) => {
                await API.updateProgress(node.id, status, 'learning');
                if (currentStep < path.length - 1) {
                    currentStep++;
                    renderStep();
                } else {
                    Session.remove('learning_path');
                    contentEl.innerHTML = `
                        <div class="card" style="border-left:3px solid #238636">
                            <h3>Path complete!</h3>
                            <p class="mt-2 text-muted">Reviewed ${path.length} concepts.</p>
                            <div class="btn-group">
                                <button class="btn btn-blue" onclick="navigateTo('dashboard')">Dashboard</button>
                                <button class="btn btn-primary" onclick="renderLearning(document.getElementById('app'))">Next Path</button>
                                <button class="btn btn-warning" onclick="navigateTo('quiz')">Quiz</button>
                            </div>
                        </div>
                    `;
                }
            };

            document.getElementById('understood').addEventListener('click', () => advance('known'));
            document.getElementById('shaky').addEventListener('click', () => advance('shaky'));
        }

        renderStep();
    }

    // View toggle handlers
    document.getElementById('viewTopics').addEventListener('click', renderTopicView);
    document.getElementById('viewPath').addEventListener('click', renderFocusPath);

    // Restore saved view
    if (savedView === 'path') {
        renderFocusPath();
    } else {
        renderTopicView();
    }
}


function showStudyNode(node) {
    document.querySelectorAll('.modal-overlay').forEach(m => m.remove());

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.remove();
    });

    const modal = document.createElement('div');
    modal.className = 'modal-content';

    modal.innerHTML = '<button class="modal-close">&times;</button>';
    modal.querySelector('.modal-close').addEventListener('click', () => overlay.remove());

    const card = createNodeCard(node, { showContent: true });
    modal.appendChild(card);

    const actions = document.createElement('div');
    actions.className = 'btn-group';
    actions.innerHTML = `
        <button class="btn btn-primary" data-rate="known">I know this</button>
        <button class="btn btn-warning" data-rate="shaky">Shaky</button>
        <button class="btn btn-danger" data-rate="unknown">Don't know</button>
    `;
    actions.querySelectorAll('[data-rate]').forEach(btn => {
        btn.addEventListener('click', async () => {
            await API.updateProgress(node.id, btn.dataset.rate, 'learning');
            overlay.remove();
            renderLearning(document.getElementById('app'));
        });
    });
    modal.appendChild(actions);

    overlay.appendChild(modal);
    document.body.appendChild(overlay);
}
