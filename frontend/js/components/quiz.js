/* Quiz component — 6 quiz modes (including Smart Review) with full session persistence */

const QUIZ_TYPES = [
    { id: 'smart_review', name: 'Smart Review', desc: 'Spaced repetition — review items you\'re about to forget' },
    { id: 'definition_recall', name: 'Definition Recall', desc: 'Show name, recall definition' },
    { id: 'theorem_statement', name: 'Theorem Statement', desc: 'Show name, recall statement' },
    { id: 'proof_reconstruction', name: 'Proof Reconstruction', desc: 'Show statement, recall proof' },
    { id: 'reverse_quiz', name: 'Reverse Quiz', desc: 'Show result, name the theorem' },
    { id: 'fill_blank', name: 'Fill in the Blank', desc: 'Complete the missing parts' },
];

let currentQuizType = null;
let quizItems = [];
let quizIndex = 0;
let quizScope = 'all';
let quizCount = 5;
let quizResults = [];  // track ratings for each item

async function renderQuiz(container) {
    // Restore saved quiz session
    const saved = Session.get('quiz');

    // If there's an in-progress quiz session, resume it
    if (saved && saved.items && saved.items.length > 0 && saved.index < saved.items.length) {
        currentQuizType = saved.type;
        quizItems = saved.items;
        quizIndex = saved.index;
        quizScope = saved.scope || 'all';
        quizCount = saved.count || 5;
        quizResults = saved.results || [];
        _renderQuizShell(container, true);
        return;
    }

    currentQuizType = saved?.type || null;
    quizScope = saved?.scope || 'all';
    quizCount = saved?.count || 5;
    quizItems = [];
    quizIndex = 0;
    quizResults = [];

    _renderQuizShell(container, false);
}

function _renderQuizShell(container, resuming) {
    let html = `
        <h2 class="mb-4">Quiz</h2>
        <div class="quiz-selector" id="quizSelector">
    `;
    for (const t of QUIZ_TYPES) {
        html += `
            <div class="quiz-type-card ${currentQuizType === t.id ? 'active' : ''}" data-type="${t.id}">
                <div class="quiz-type-name">${t.name}</div>
                <div class="quiz-type-desc">${t.desc}</div>
            </div>
        `;
    }
    html += `</div>
        <div class="flex gap-2 mb-4">
            <select id="quizScope">
                <option value="all" ${quizScope === 'all' ? 'selected' : ''}>All concepts</option>
                <option value="unknown" ${quizScope === 'unknown' ? 'selected' : ''}>Unknown only</option>
                <option value="shaky" ${quizScope === 'shaky' ? 'selected' : ''}>Shaky only</option>
            </select>
            <select id="quizCount">
                <option value="5" ${quizCount == 5 ? 'selected' : ''}>5 questions</option>
                <option value="10" ${quizCount == 10 ? 'selected' : ''}>10 questions</option>
                <option value="20" ${quizCount == 20 ? 'selected' : ''}>20 questions</option>
            </select>
            <button class="btn btn-primary" id="startQuiz" ${!currentQuizType ? 'disabled' : ''}>Start Quiz</button>
        </div>
        <div id="quizArea"></div>
    `;

    container.innerHTML = html;

    // Type selection
    document.querySelectorAll('.quiz-type-card').forEach(card => {
        card.addEventListener('click', () => {
            document.querySelectorAll('.quiz-type-card').forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            currentQuizType = card.dataset.type;
            document.getElementById('startQuiz').disabled = false;
            Session.set('quiz', { type: currentQuizType, scope: quizScope, count: quizCount, items: [], index: 0, results: [] });
        });
    });

    // Save scope/count changes
    document.getElementById('quizScope').addEventListener('change', (e) => {
        quizScope = e.target.value;
        Session.set('quiz', { ...Session.get('quiz', {}), scope: quizScope });
    });
    document.getElementById('quizCount').addEventListener('change', (e) => {
        quizCount = parseInt(e.target.value);
        Session.set('quiz', { ...Session.get('quiz', {}), count: quizCount });
    });

    document.getElementById('startQuiz').addEventListener('click', async () => {
        const scope = document.getElementById('quizScope').value;
        const count = parseInt(document.getElementById('quizCount').value);

        if (currentQuizType === 'smart_review') {
            // Smart Review: fetch due items from SR engine
            await _startSmartReview(count);
        } else {
            // Standard quiz types
            quizItems = await API.getQuiz(currentQuizType, count, scope);
            quizIndex = 0;
            quizResults = [];

            if (quizItems.length === 0) {
                document.getElementById('quizArea').innerHTML =
                    '<div class="card"><p>No quiz items available for this combination. Try a different type or scope.</p></div>';
                return;
            }

            Session.set('quiz', {
                type: currentQuizType, scope, count,
                items: quizItems, index: 0, results: [],
            });

            renderQuizItem(document.getElementById('quizArea'));
        }
    });

    // If resuming, render current item
    if (resuming) {
        renderQuizItem(document.getElementById('quizArea'));
    }
}

async function _startSmartReview(count) {
    const area = document.getElementById('quizArea');
    area.innerHTML = '<div class="text-muted">Loading smart review items...</div>';

    const dueItems = await API.getSRDue(count);

    if (dueItems.length === 0) {
        area.innerHTML = `
            <div class="card" style="border-left:3px solid #238636">
                <h3>All caught up!</h3>
                <p class="mt-2 text-muted">No items due for review right now. Come back later or try a regular quiz.</p>
                <div class="btn-group">
                    <button class="btn btn-blue" onclick="navigateTo('dashboard')">Dashboard</button>
                </div>
            </div>
        `;
        return;
    }

    // Fetch full node data for each due item
    const nodePromises = dueItems.map(item => API.getNode(item.node_id));
    const nodes = await Promise.all(nodePromises);

    quizItems = [];
    for (let i = 0; i < nodes.length; i++) {
        const node = nodes[i];
        const due = dueItems[i];
        if (!node || !node.id) continue;

        const typeName = (node.type || '').charAt(0).toUpperCase() + (node.type || '').slice(1);
        const retPct = Math.round((due.retrievability || 0) * 100);

        quizItems.push({
            node_id: node.id,
            quiz_type: 'smart_review',
            prompt: `Review: ${typeName} ${node.display_number || ''}${node.title ? ': ' + node.title : ''}`,
            prompt_subtitle: `Estimated recall: ${retPct}% | Difficulty: ${Math.round((due.difficulty || 0.3) * 100)}%`,
            prompt_content: node.katex_content || '',
            answer: node.katex_content || node.latex_content || '',
            is_smart_review: true,
        });
    }

    quizIndex = 0;
    quizResults = [];

    Session.set('quiz', {
        type: 'smart_review', scope: 'all', count,
        items: quizItems, index: 0, results: [],
    });

    renderQuizItem(area);
}

function renderQuizItem(area) {
    if (quizIndex >= quizItems.length) {
        // Quiz complete — record session
        const correct = quizResults.filter(r => r.rating === 'known').length;
        API.completeQuiz({
            type: currentQuizType,
            scope: quizScope,
            total: quizItems.length,
            correct,
            items: quizResults,
        });
        // Clear saved quiz session
        Session.set('quiz', { type: currentQuizType, scope: quizScope, count: quizCount, items: [], index: 0, results: [] });

        area.innerHTML = `
            <div class="card" style="border-left:3px solid #238636">
                <h3>Quiz complete!</h3>
                <p class="mt-2 text-muted">
                    Score: ${correct} / ${quizItems.length}
                    (${Math.round(correct / quizItems.length * 100)}%)
                </p>
                <div class="btn-group">
                    <button class="btn btn-blue" onclick="navigateTo('dashboard')">Dashboard</button>
                    <button class="btn btn-primary" onclick="navigateTo('quiz')">Another Quiz</button>
                </div>
            </div>
        `;
        return;
    }

    const item = quizItems[quizIndex];
    const progressPct = ((quizIndex) / quizItems.length * 100).toFixed(0);

    const isSmartReview = item.is_smart_review || currentQuizType === 'smart_review';
    const badgeClass = isSmartReview ? 'algorithm' : (currentQuizType === 'definition_recall' ? 'definition' : 'theorem');
    const badgeText = isSmartReview ? 'smart review' : item.quiz_type.replace('_', ' ');

    let html = `
        <div class="learning-progress mb-4">
            <div class="learning-progress-bar">
                <div class="learning-progress-fill" style="width:${progressPct}%"></div>
            </div>
            <span class="learning-step-counter">${quizIndex + 1} / ${quizItems.length}</span>
        </div>
        <div class="card">
            <div class="card-header">
                <span class="badge badge-${badgeClass}">${badgeText}</span>
            </div>
            <h3>${item.prompt}</h3>
            ${item.prompt_subtitle ? `<p class="text-muted text-sm">${item.prompt_subtitle}</p>` : ''}
    `;

    if (isSmartReview) {
        // Smart review: hide content first, reveal on click
        html += `
                <div class="btn-group">
                    <button class="btn btn-blue" id="revealAnswer">Show Content & Self-Rate</button>
                </div>
                <div class="quiz-answer-area" id="quizAnswer">
                    <div class="math-content mt-2" id="quizAnswerContent"></div>
                </div>
                <div class="btn-group hidden" id="quizRate">
                    <button class="btn btn-primary" data-rate="known">I remember</button>
                    <button class="btn btn-warning" data-rate="shaky">Partially</button>
                    <button class="btn btn-danger" data-rate="unknown">Forgot</button>
                </div>
            </div>
        `;
    } else {
        if (item.prompt_content) {
            html += `<div class="math-content" id="quizPromptContent"></div>`;
        }
        html += `
                <div class="btn-group">
                    <button class="btn btn-blue" id="revealAnswer">Reveal Answer</button>
                </div>
                <div class="quiz-answer-area" id="quizAnswer">
                    <strong>Answer:</strong>
                    <div class="math-content mt-2" id="quizAnswerContent"></div>
                </div>
                <div class="btn-group hidden" id="quizRate">
                    <button class="btn btn-primary" data-rate="known">Got it right</button>
                    <button class="btn btn-warning" data-rate="shaky">Partially</button>
                    <button class="btn btn-danger" data-rate="unknown">Didn't know</button>
                </div>
            </div>
        `;
    }

    area.innerHTML = html;

    if (!isSmartReview && item.prompt_content) {
        const promptEl = document.getElementById('quizPromptContent');
        promptEl.innerHTML = item.prompt_content;
        renderMath(promptEl);
    }

    document.getElementById('revealAnswer').addEventListener('click', () => {
        const answerArea = document.getElementById('quizAnswer');
        answerArea.classList.add('revealed');
        const answerContent = document.getElementById('quizAnswerContent');
        answerContent.innerHTML = item.answer;
        renderMath(answerContent);
        document.getElementById('quizRate').classList.remove('hidden');
        document.getElementById('revealAnswer').classList.add('hidden');
    });

    document.querySelectorAll('#quizRate [data-rate]').forEach(btn => {
        btn.addEventListener('click', async () => {
            const rate = btn.dataset.rate;
            await API.updateProgress(item.node_id, rate, 'quiz');

            quizResults.push({ node_id: item.node_id, rating: rate });
            quizIndex++;

            // Save progress through quiz
            Session.set('quiz', {
                type: currentQuizType, scope: quizScope, count: quizCount,
                items: quizItems, index: quizIndex, results: quizResults,
            });

            renderQuizItem(area);
        });
    });
}
