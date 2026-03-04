/* API client wrapper */
const API = {
    base: '',

    async get(path) {
        const res = await fetch(this.base + path);
        return res.json();
    },

    async post(path, data) {
        const res = await fetch(this.base + path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return res.json();
    },

    // Graph
    getGraph: () => API.get('/api/graph'),
    getNode: (id) => API.get(`/api/node/${encodeURIComponent(id)}`),
    getMacros: () => API.get('/api/macros'),

    // Progress
    getProgress: () => API.get('/api/progress'),
    updateProgress: (nodeId, status, source = 'manual') =>
        API.post(`/api/progress/${encodeURIComponent(nodeId)}`, { status, source }),
    resetProgress: () => API.post('/api/progress/reset', {}),

    // Diagnostic
    getDiagnosticTargets: () => API.get('/api/diagnostic/targets'),
    rateDiagnostic: (ratings) => API.post('/api/diagnostic/rate', { ratings }),
    getUnknowns: () => API.get('/api/diagnostic/unknowns'),

    // Learning
    getLearningPath: (targetId) => API.get(`/api/learning/path/${encodeURIComponent(targetId)}`),
    getAutoLearningPath: () => API.get('/api/learning/auto'),

    // Quiz
    getQuiz: (type, count = 5, scope = 'all') =>
        API.get(`/api/quiz/generate?type=${type}&count=${count}&scope=${scope}`),
    completeQuiz: (data) => API.post('/api/quiz/complete', data),

    // Dashboard
    getDashboard: () => API.get('/api/dashboard'),

    // Spaced Repetition
    getSRDue: (limit = 20) => API.get(`/api/sr/due?limit=${limit}`),
    getSRSummary: () => API.get('/api/sr/summary'),
    recordSRReview: (nodeId, rating) => API.post('/api/sr/review', { node_id: nodeId, rating }),
    getRLStats: () => API.get('/api/sr/rl-stats'),

    // Session persistence
    getSession: () => API.get('/api/session'),
    saveSession: (data) => API.post('/api/session', data),
    saveSessionKey: (key, value) => API.post(`/api/session/${key}`, { value }),

    // Courses
    getCourses: () => API.get('/api/courses'),
    getCurrentCourse: () => API.get('/api/courses/current'),
    createCourse: (formData) => fetch('/api/courses', { method: 'POST', body: formData }).then(r => r.json()),
    switchCourse: (courseId) => API.post(`/api/courses/${encodeURIComponent(courseId)}/switch`, {}),
    deleteCourse: (courseId) => fetch(`/api/courses/${encodeURIComponent(courseId)}`, { method: 'DELETE' }).then(r => r.json()),
    rebuildCourse: (courseId) => API.post(`/api/courses/${encodeURIComponent(courseId)}/rebuild`, {}),
};


/**
 * Session manager — persists all UI state to the server.
 * Debounces writes to avoid excessive requests.
 */
const Session = {
    _data: {},
    _loaded: false,
    _saveTimer: null,

    async load() {
        if (this._loaded) return this._data;
        try {
            this._data = await API.getSession();
        } catch {
            this._data = {};
        }
        this._loaded = true;
        return this._data;
    },

    get(key, fallback = null) {
        return this._data[key] !== undefined ? this._data[key] : fallback;
    },

    set(key, value) {
        this._data[key] = value;
        this._scheduleSave();
    },

    setMulti(obj) {
        Object.assign(this._data, obj);
        this._scheduleSave();
    },

    remove(key) {
        delete this._data[key];
        this._scheduleSave();
    },

    _scheduleSave() {
        if (this._saveTimer) clearTimeout(this._saveTimer);
        this._saveTimer = setTimeout(() => {
            API.saveSession(this._data).catch(() => {});
        }, 300);  // debounce 300ms
    },

    /** Clear all session data (use after progress reset) */
    clear() {
        this._data = {};
        this._loaded = false;
        if (this._saveTimer) {
            clearTimeout(this._saveTimer);
            this._saveTimer = null;
        }
    },

    /** Force immediate save (use before page unload) */
    flush() {
        if (this._saveTimer) {
            clearTimeout(this._saveTimer);
            this._saveTimer = null;
        }
        // Use sendBeacon for reliable unload saves
        const blob = new Blob([JSON.stringify(this._data)], { type: 'application/json' });
        navigator.sendBeacon('/api/session', blob);
    },
};
