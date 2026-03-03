/* Main SPA router and initialization */

const PAGES = {
    dashboard: renderDashboard,
    diagnostic: renderDiagnostic,
    learning: renderLearning,
    quiz: renderQuiz,
    graph: renderGraphViewer,
    browse: renderBrowse,
    courses: renderCourses,
};

let currentPage = 'dashboard';

function navigateTo(page) {
    currentPage = page;
    Session.set('currentPage', page);

    // Update nav
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.toggle('active', link.dataset.page === page);
    });

    // Render page
    const app = document.getElementById('app');
    app.innerHTML = '';

    const renderer = PAGES[page];
    if (renderer) {
        renderer(app);
    } else {
        app.innerHTML = `<div class="card"><p>Page not found: ${page}</p></div>`;
    }
}

/** Initialize and populate the course selector dropdown */
async function initCourseSelector() {
    const select = document.getElementById('courseSelect');
    if (!select) return;

    try {
        const data = await API.getCourses();
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

        // Hide selector if no courses
        const selectorDiv = document.getElementById('courseSelector');
        if (data.courses.length === 0) {
            selectorDiv.style.display = 'none';
        } else {
            selectorDiv.style.display = '';
        }

        // Switch course on change
        select.addEventListener('change', async () => {
            const courseId = select.value;
            select.disabled = true;
            try {
                await API.switchCourse(courseId);
                Session.clear();
                await Session.load();
                await initKaTeX();
                // Re-render current page with new course data
                navigateTo(currentPage);
            } catch (err) {
                alert('Failed to switch course: ' + (err.message || 'Unknown error'));
            }
            select.disabled = false;
        });
    } catch {
        // Courses not available yet
        document.getElementById('courseSelector').style.display = 'none';
    }
}

// Init
document.addEventListener('DOMContentLoaded', async () => {
    // Load saved session first
    await Session.load();

    // Init KaTeX macros
    await initKaTeX();

    // Init course selector
    await initCourseSelector();

    // Nav click handlers
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            navigateTo(link.dataset.page);
        });
    });

    // Restore last page or default to dashboard
    const savedPage = Session.get('currentPage', 'dashboard');
    navigateTo(PAGES[savedPage] ? savedPage : 'dashboard');
});

// Save session on page unload
window.addEventListener('beforeunload', () => {
    Session.flush();
});
