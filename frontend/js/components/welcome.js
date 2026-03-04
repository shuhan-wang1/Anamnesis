/* Welcome / onboarding page — shown when no courses exist */

async function renderWelcome(container) {
    // Hide nav elements that don't apply yet
    document.getElementById('courseSelector').style.display = 'none';

    container.innerHTML = `
        <div class="welcome-page">
            <div class="welcome-hero">
                <img src="logo.svg" class="welcome-logo" alt="Anamnesis Logo">
                <h1 class="welcome-title">Anamnesis</h1>
                <p class="welcome-subtitle">
                    Transform your LaTeX lecture notes into an interactive knowledge graph
                    with spaced-repetition review
                </p>
            </div>

            <div class="welcome-main card">
                <h2>Get Started</h2>
                <p class="text-muted mb-4">Drop your .tex lecture notes to create your first course. The parser automatically extracts definitions, theorems, proofs, and builds a dependency graph.</p>

                <div class="welcome-drop-zone" id="welcomeDropZone">
                    <div class="welcome-drop-content">
                        <svg class="welcome-drop-icon" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M24 4L14 14h7v14h6V14h7L24 4z" fill="#58a6ff" opacity="0.8"/>
                            <rect x="8" y="30" width="32" height="14" rx="3" stroke="#58a6ff" stroke-width="2" fill="none" opacity="0.5"/>
                            <circle cx="36" cy="37" r="2" fill="#58a6ff" opacity="0.6"/>
                        </svg>
                        <h3>Drag & drop .tex files here</h3>
                        <p class="text-muted text-sm">Supports individual files or entire folders</p>
                    </div>
                </div>

                <div class="upload-buttons" style="justify-content: center;">
                    <button class="btn btn-secondary" id="welcomeSelectFiles">Select Files</button>
                    <button class="btn btn-secondary" id="welcomeSelectFolder">Select Folder</button>
                    <input type="file" id="welcomeFileInput" multiple accept=".tex" style="display:none">
                    <input type="file" id="welcomeFolderInput" webkitdirectory style="display:none">
                </div>

                <div id="welcomeFileList" class="file-list" style="display:none">
                    <h4>Selected Files (<span id="welcomeFileCount">0</span>)</h4>
                    <ul id="welcomeFileListItems"></ul>
                    <button class="btn btn-link text-sm" id="welcomeClearFiles">Clear all</button>
                </div>

                <div id="welcomeForm" style="display:none">
                    <div class="form-group">
                        <label for="welcomeCourseName">Course Name</label>
                        <input type="text" id="welcomeCourseName" class="form-input"
                               placeholder="e.g. Linear Algebra, Machine Learning..." autocomplete="off">
                    </div>
                    <button class="btn btn-primary btn-lg" id="welcomeCreateBtn">
                        Create Course & Start Learning
                    </button>
                </div>

                <div id="welcomeProgress" class="welcome-progress-container" style="display:none">
                    <div class="welcome-spinner"></div>
                    <div class="welcome-progress-text" id="welcomeProgressText">Uploading files...</div>
                    <div class="welcome-progress-bar">
                        <div class="welcome-progress-fill" id="welcomeProgressFill"></div>
                    </div>
                </div>

                <div id="welcomeError" class="status-msg status-error" style="display:none"></div>
            </div>

            <div class="welcome-features">
                <div class="feature-card">
                    <div class="feature-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="#58a6ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="3"/>
                            <circle cx="5" cy="6" r="2"/><circle cx="19" cy="6" r="2"/>
                            <circle cx="5" cy="18" r="2"/><circle cx="19" cy="18" r="2"/>
                            <line x1="12" y1="9" x2="5" y2="8"/><line x1="12" y1="9" x2="19" y2="8"/>
                            <line x1="12" y1="15" x2="5" y2="16"/><line x1="12" y1="15" x2="19" y2="16"/>
                        </svg>
                    </div>
                    <h4>Knowledge Graph</h4>
                    <p>Automatically extracts definitions, theorems, and proofs, then maps their dependencies</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="#3fb950" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/>
                        </svg>
                    </div>
                    <h4>Spaced Repetition</h4>
                    <p>FSRS-based scheduling ensures you review concepts just before you forget them</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="#d29922" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
                        </svg>
                    </div>
                    <h4>6 Quiz Modes</h4>
                    <p>Definition recall, theorem statement, proof reconstruction, reverse quiz, and more</p>
                </div>
            </div>
        </div>
    `;

    // --- File selection state ---
    let selectedFiles = [];

    function updateFileList() {
        const listEl = document.getElementById('welcomeFileList');
        const itemsEl = document.getElementById('welcomeFileListItems');
        const countEl = document.getElementById('welcomeFileCount');
        const formEl = document.getElementById('welcomeForm');

        if (selectedFiles.length === 0) {
            listEl.style.display = 'none';
            formEl.style.display = 'none';
            return;
        }

        listEl.style.display = 'block';
        formEl.style.display = 'block';
        countEl.textContent = selectedFiles.length;
        itemsEl.innerHTML = selectedFiles.map((f, i) =>
            `<li>
                <span class="file-name">${f.name}</span>
                <span class="file-size text-muted">${(f.size / 1024).toFixed(1)} KB</span>
                <button class="btn-remove" data-idx="${i}" title="Remove">&times;</button>
            </li>`
        ).join('');

        // Auto-suggest course name from filenames
        const nameInput = document.getElementById('welcomeCourseName');
        if (!nameInput.value.trim()) {
            nameInput.value = _suggestCourseName(selectedFiles);
        }

        // Remove buttons
        itemsEl.querySelectorAll('.btn-remove').forEach(btn => {
            btn.addEventListener('click', () => {
                selectedFiles.splice(parseInt(btn.dataset.idx), 1);
                updateFileList();
            });
        });
    }

    function addFiles(fileList) {
        const existing = new Set(selectedFiles.map(f => f.name));
        for (const file of fileList) {
            const name = file.name || file.webkitRelativePath?.split('/').pop() || 'unknown';
            if (name.endsWith('.tex') && !existing.has(name)) {
                selectedFiles.push(file);
                existing.add(name);
            }
        }
        updateFileList();
    }

    // --- File input handlers ---
    document.getElementById('welcomeSelectFiles').addEventListener('click', () => {
        document.getElementById('welcomeFileInput').click();
    });
    document.getElementById('welcomeSelectFolder').addEventListener('click', () => {
        document.getElementById('welcomeFolderInput').click();
    });
    document.getElementById('welcomeFileInput').addEventListener('change', (e) => {
        addFiles(e.target.files);
    });
    document.getElementById('welcomeFolderInput').addEventListener('change', (e) => {
        addFiles(e.target.files);
    });
    document.getElementById('welcomeClearFiles').addEventListener('click', () => {
        selectedFiles = [];
        document.getElementById('welcomeCourseName').value = '';
        updateFileList();
    });

    // --- Drag & drop ---
    const dropZone = document.getElementById('welcomeDropZone');

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drop-zone-active');
    });
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drop-zone-active');
    });
    dropZone.addEventListener('drop', async (e) => {
        e.preventDefault();
        dropZone.classList.remove('drop-zone-active');

        const items = e.dataTransfer.items;
        if (items) {
            const filePromises = [];
            for (const item of items) {
                const entry = item.webkitGetAsEntry?.();
                if (entry) {
                    filePromises.push(_readEntryRecursive(entry));
                } else if (item.kind === 'file') {
                    const file = item.getAsFile();
                    if (file) filePromises.push(Promise.resolve([file]));
                }
            }
            const fileArrays = await Promise.all(filePromises);
            addFiles(fileArrays.flat());
        } else {
            addFiles(e.dataTransfer.files);
        }
    });

    // Also support full-page drop
    document.body.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drop-zone-active');
    });
    document.body.addEventListener('dragleave', (e) => {
        if (!e.relatedTarget || e.relatedTarget === document.documentElement) {
            dropZone.classList.remove('drop-zone-active');
        }
    });
    document.body.addEventListener('drop', async (e) => {
        // Only handle if not already handled by the drop zone
        if (e.target !== dropZone && !dropZone.contains(e.target)) {
            e.preventDefault();
            dropZone.classList.remove('drop-zone-active');
            const items = e.dataTransfer.items;
            if (items) {
                const filePromises = [];
                for (const item of items) {
                    const entry = item.webkitGetAsEntry?.();
                    if (entry) {
                        filePromises.push(_readEntryRecursive(entry));
                    } else if (item.kind === 'file') {
                        const file = item.getAsFile();
                        if (file) filePromises.push(Promise.resolve([file]));
                    }
                }
                const fileArrays = await Promise.all(filePromises);
                addFiles(fileArrays.flat());
            } else {
                addFiles(e.dataTransfer.files);
            }
        }
    });

    // --- Create course ---
    document.getElementById('welcomeCreateBtn').addEventListener('click', async () => {
        const name = document.getElementById('welcomeCourseName').value.trim();
        if (!name || selectedFiles.length === 0) return;

        const progressEl = document.getElementById('welcomeProgress');
        const formEl = document.getElementById('welcomeForm');
        const errorEl = document.getElementById('welcomeError');
        const progressText = document.getElementById('welcomeProgressText');
        const progressFill = document.getElementById('welcomeProgressFill');

        errorEl.style.display = 'none';
        formEl.style.display = 'none';
        progressEl.style.display = 'flex';

        // Animate progress steps
        progressText.textContent = 'Uploading files...';
        progressFill.style.width = '15%';

        const formData = new FormData();
        formData.append('name', name);
        for (const file of selectedFiles) {
            formData.append('files', file);
        }

        // Simulate progress during the server-side pipeline
        const progressSteps = [
            { text: 'Parsing LaTeX environments...', pct: '35%', delay: 800 },
            { text: 'Extracting macros & references...', pct: '55%', delay: 1500 },
            { text: 'Building knowledge graph...', pct: '75%', delay: 2500 },
            { text: 'Computing importance scores...', pct: '90%', delay: 3500 },
        ];

        const stepTimers = progressSteps.map(step =>
            setTimeout(() => {
                progressText.textContent = step.text;
                progressFill.style.width = step.pct;
            }, step.delay)
        );

        try {
            const result = await API.createCourse(formData);

            // Clear timers
            stepTimers.forEach(t => clearTimeout(t));

            if (result.error) {
                progressEl.style.display = 'none';
                formEl.style.display = 'block';
                errorEl.style.display = 'block';
                errorEl.textContent = result.error;
                return;
            }

            progressText.textContent = 'Done! Loading your course...';
            progressFill.style.width = '100%';

            // Reload KaTeX macros and course selector
            await initKaTeX();
            await initCourseSelector();

            // Navigate to dashboard
            setTimeout(() => navigateTo('dashboard'), 600);
        } catch (err) {
            stepTimers.forEach(t => clearTimeout(t));
            progressEl.style.display = 'none';
            formEl.style.display = 'block';
            errorEl.style.display = 'block';
            errorEl.textContent = 'Failed to create course: ' + (err.message || 'Unknown error');
        }
    });
}


function _suggestCourseName(files) {
    if (files.length === 0) return '';
    // Try to extract a common prefix from filenames
    const names = files.map(f => f.name.replace(/\.tex$/, ''));
    if (names.length === 1) return names[0].replace(/[_-]/g, ' ').trim();

    // Find common prefix
    let prefix = names[0];
    for (let i = 1; i < names.length; i++) {
        while (!names[i].startsWith(prefix) && prefix.length > 0) {
            prefix = prefix.slice(0, -1);
        }
    }
    prefix = prefix.replace(/[_\-\s.()]+$/, '').replace(/[_-]/g, ' ').trim();
    return prefix.length >= 3 ? prefix : 'My Course';
}


async function _readEntryRecursive(entry) {
    if (entry.isFile) {
        return new Promise(resolve => {
            entry.file(file => resolve([file]));
        });
    } else if (entry.isDirectory) {
        const reader = entry.createReader();
        return new Promise(resolve => {
            reader.readEntries(async entries => {
                const fileArrays = await Promise.all(entries.map(e => _readEntryRecursive(e)));
                resolve(fileArrays.flat());
            });
        });
    }
    return [];
}
