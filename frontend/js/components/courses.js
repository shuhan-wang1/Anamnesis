/* Course management page — create, switch, delete courses */

async function renderCourses(container) {
    container.innerHTML = '<div class="card"><p>Loading courses...</p></div>';

    let data;
    try {
        data = await API.getCourses();
    } catch (err) {
        container.innerHTML = '<div class="card"><p>Failed to load courses.</p></div>';
        return;
    }

    const courses = data.courses || [];
    const activeCourseId = data.active_course_id;

    container.innerHTML = `
        <div class="card">
            <h2>Courses</h2>
            <p class="text-muted">Manage your course materials. Each course has its own knowledge graph, progress, and review schedule.</p>
        </div>

        <!-- Create New Course -->
        <div class="card">
            <h3>Create New Course</h3>
            <div class="create-course-form">
                <div class="form-group">
                    <label for="courseName">Course Name</label>
                    <input type="text" id="courseName" placeholder="e.g. Linear Algebra, Machine Learning..."
                           class="form-input" autocomplete="off">
                </div>

                <div class="form-group">
                    <label>Upload .tex Files</label>
                    <div class="upload-methods">
                        <div class="drop-zone" id="dropZone">
                            <div class="drop-zone-content">
                                <div class="drop-zone-icon">&#128196;</div>
                                <p>Drag & drop .tex files here</p>
                                <p class="text-muted text-sm">or use the buttons below</p>
                            </div>
                        </div>
                        <div class="upload-buttons">
                            <button class="btn btn-secondary" id="selectFilesBtn">Select Files</button>
                            <button class="btn btn-secondary" id="selectFolderBtn">Select Folder</button>
                            <input type="file" id="fileInput" multiple accept=".tex" style="display:none">
                            <input type="file" id="folderInput" webkitdirectory style="display:none">
                        </div>
                    </div>
                </div>

                <div id="fileList" class="file-list" style="display:none">
                    <h4>Selected Files (<span id="fileCount">0</span>)</h4>
                    <ul id="fileListItems"></ul>
                    <button class="btn btn-link text-sm" id="clearFilesBtn">Clear all</button>
                </div>

                <button class="btn btn-primary" id="createCourseBtn" disabled>Create Course</button>
                <div id="createStatus" style="display:none" class="status-msg"></div>
            </div>
        </div>

        <!-- Course List -->
        <div class="card">
            <h3>Your Courses</h3>
            <div id="courseList">
                ${courses.length === 0
                    ? '<p class="text-muted">No courses yet. Create one above!</p>'
                    : courses.map(c => _renderCourseCard(c, activeCourseId)).join('')}
            </div>
        </div>
    `;

    // --- File selection state ---
    let selectedFiles = [];

    function updateFileList() {
        const listEl = document.getElementById('fileList');
        const itemsEl = document.getElementById('fileListItems');
        const countEl = document.getElementById('fileCount');
        const createBtn = document.getElementById('createCourseBtn');

        if (selectedFiles.length === 0) {
            listEl.style.display = 'none';
            createBtn.disabled = true;
            return;
        }

        listEl.style.display = 'block';
        countEl.textContent = selectedFiles.length;
        itemsEl.innerHTML = selectedFiles.map((f, i) =>
            `<li>
                <span class="file-name">${f.name}</span>
                <span class="file-size text-muted">${(f.size / 1024).toFixed(1)} KB</span>
                <button class="btn-remove" data-idx="${i}" title="Remove">&times;</button>
            </li>`
        ).join('');

        createBtn.disabled = !document.getElementById('courseName').value.trim();

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
    document.getElementById('selectFilesBtn').addEventListener('click', () => {
        document.getElementById('fileInput').click();
    });

    document.getElementById('selectFolderBtn').addEventListener('click', () => {
        document.getElementById('folderInput').click();
    });

    document.getElementById('fileInput').addEventListener('change', (e) => {
        addFiles(e.target.files);
    });

    document.getElementById('folderInput').addEventListener('change', (e) => {
        addFiles(e.target.files);
    });

    document.getElementById('clearFilesBtn')?.addEventListener('click', () => {
        selectedFiles = [];
        updateFileList();
    });

    // --- Drag & drop ---
    const dropZone = document.getElementById('dropZone');

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
            // Handle directory drops (modern browsers)
            const filePromises = [];
            for (const item of items) {
                const entry = item.webkitGetAsEntry?.();
                if (entry) {
                    filePromises.push(_readEntry(entry));
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

    // --- Course name enables create button ---
    document.getElementById('courseName').addEventListener('input', () => {
        const createBtn = document.getElementById('createCourseBtn');
        createBtn.disabled = !document.getElementById('courseName').value.trim() || selectedFiles.length === 0;
    });

    // --- Create course ---
    document.getElementById('createCourseBtn').addEventListener('click', async () => {
        const name = document.getElementById('courseName').value.trim();
        if (!name || selectedFiles.length === 0) return;

        const statusEl = document.getElementById('createStatus');
        const createBtn = document.getElementById('createCourseBtn');
        createBtn.disabled = true;
        statusEl.style.display = 'block';
        statusEl.className = 'status-msg status-info';
        statusEl.textContent = `Creating course "${name}" and parsing ${selectedFiles.length} files... This may take a moment.`;

        const formData = new FormData();
        formData.append('name', name);
        for (const file of selectedFiles) {
            formData.append('files', file);
        }

        try {
            const result = await API.createCourse(formData);
            if (result.error) {
                statusEl.className = 'status-msg status-error';
                statusEl.textContent = result.error;
                createBtn.disabled = false;
                return;
            }

            statusEl.className = 'status-msg status-success';
            statusEl.textContent = `Course "${result.course.name}" created with ${result.course.node_count} concepts! Switching...`;

            // Reload KaTeX macros for new course
            await initKaTeX();

            // Refresh course selector and page
            await _refreshCourseSelector();

            // Clear form
            selectedFiles = [];
            document.getElementById('courseName').value = '';
            updateFileList();

            // Navigate to dashboard for the new course
            setTimeout(() => navigateTo('dashboard'), 500);
        } catch (err) {
            statusEl.className = 'status-msg status-error';
            statusEl.textContent = 'Failed to create course: ' + (err.message || 'Unknown error');
            createBtn.disabled = false;
        }
    });

    // --- Course card actions ---
    container.querySelectorAll('.course-switch-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const courseId = btn.dataset.courseId;
            btn.textContent = 'Switching...';
            btn.disabled = true;
            try {
                await API.switchCourse(courseId);
                Session.clear();
                await Session.load();
                await initKaTeX();
                await _refreshCourseSelector();
                navigateTo('dashboard');
            } catch (err) {
                alert('Failed to switch: ' + (err.message || 'Unknown error'));
                btn.textContent = 'Switch';
                btn.disabled = false;
            }
        });
    });

    container.querySelectorAll('.course-delete-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const courseId = btn.dataset.courseId;
            const courseName = btn.dataset.courseName;
            if (!confirm(`Delete "${courseName}" and all its data? This cannot be undone.`)) return;

            try {
                const result = await API.deleteCourse(courseId);
                if (result.error) {
                    alert(result.error);
                    return;
                }
                await _refreshCourseSelector();
                renderCourses(container);
            } catch (err) {
                alert('Failed to delete: ' + (err.message || 'Unknown error'));
            }
        });
    });
}


function _renderCourseCard(course, activeCourseId) {
    const isActive = course.id === activeCourseId;
    const date = new Date(course.created_at).toLocaleDateString();
    return `
        <div class="course-card ${isActive ? 'course-card-active' : ''}">
            <div class="course-card-header">
                <h4>${course.name}</h4>
                ${isActive ? '<span class="badge badge-active">Active</span>' : ''}
            </div>
            <div class="course-card-stats">
                <span>${course.node_count || 0} concepts</span>
                <span>${course.file_count || 0} files</span>
                <span>Created ${date}</span>
            </div>
            <div class="course-card-actions">
                ${isActive
                    ? '<button class="btn btn-secondary btn-sm" disabled>Current</button>'
                    : `<button class="btn btn-primary btn-sm course-switch-btn" data-course-id="${course.id}">Switch</button>`}
                ${!isActive
                    ? `<button class="btn btn-danger btn-sm course-delete-btn" data-course-id="${course.id}" data-course-name="${course.name}">Delete</button>`
                    : ''}
            </div>
        </div>
    `;
}


async function _readEntry(entry) {
    /**Recursively read files from a dropped directory entry.*/
    if (entry.isFile) {
        return new Promise(resolve => {
            entry.file(file => resolve([file]));
        });
    } else if (entry.isDirectory) {
        const reader = entry.createReader();
        return new Promise(resolve => {
            reader.readEntries(async entries => {
                const fileArrays = await Promise.all(entries.map(e => _readEntry(e)));
                resolve(fileArrays.flat());
            });
        });
    }
    return [];
}


/** Refresh the course selector dropdown in the navbar */
async function _refreshCourseSelector() {
    try {
        const data = await API.getCourses();
        const select = document.getElementById('courseSelect');
        if (!select) return;

        select.innerHTML = '';
        for (const course of data.courses) {
            const opt = document.createElement('option');
            opt.value = course.id;
            opt.textContent = course.name;
            if (course.id === data.active_course_id) {
                opt.selected = true;
            }
            select.appendChild(opt);
        }
    } catch {}
}
