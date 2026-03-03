"""Shared application state — course-aware global state management."""

import json
import os

graph = None
progress = None
session = {}
current_course_id = None

DATA_DIR = None
PROGRESS_PATH = None
SESSION_PATH = None

# Course manager (lazy import to avoid circular deps)
_course_manager = None


def _get_cm():
    global _course_manager
    if _course_manager is None:
        from server import course_manager as cm
        _course_manager = cm
    return _course_manager


def init(data_dir: str):
    """Initialize state: load courses registry, switch to last-used course."""
    global DATA_DIR
    DATA_DIR = data_dir

    # Initialize course manager
    cm = _get_cm()
    cm.init(data_dir)

    # Load courses
    courses = cm.load_courses()
    if not courses:
        print("No courses found. Waiting for course creation or migration.")
        # Set empty state so the server can start
        _set_empty_state()
        return

    # Load last-used course from global session, or use first course
    global_session_path = os.path.join(data_dir, 'global_session.json')
    last_course_id = None
    if os.path.exists(global_session_path):
        with open(global_session_path, 'r') as f:
            global_session = json.load(f)
            last_course_id = global_session.get('last_course_id')

    # Verify the last course still exists
    course_ids = {c['id'] for c in courses}
    if last_course_id not in course_ids:
        last_course_id = courses[0]['id']

    switch_course(last_course_id)


def _set_empty_state():
    """Set empty state when no courses exist."""
    global graph, progress, session, current_course_id, PROGRESS_PATH, SESSION_PATH
    graph = {
        'metadata': {'total_nodes': 0, 'total_edges': 0, 'source_files': [], 'top_important': []},
        'macros': {},
        'nodes': [],
        'edges': [],
    }
    progress = {'nodes': {}, 'quiz_sessions': [], 'study_time': {}}
    session = {}
    current_course_id = None
    PROGRESS_PATH = None
    SESSION_PATH = None


def switch_course(course_id: str):
    """Switch to a different course, loading its graph, progress, and session."""
    global graph, progress, session, current_course_id, PROGRESS_PATH, SESSION_PATH

    cm = _get_cm()
    course = cm.get_course(course_id)
    if not course:
        print(f"Course '{course_id}' not found!")
        return False

    paths = cm.get_course_paths(course_id)

    # Load knowledge graph
    graph_path = paths['graph_path']
    if os.path.exists(graph_path):
        with open(graph_path, 'r', encoding='utf-8') as f:
            graph = json.load(f)
        print(f"Loaded graph for '{course['name']}': {graph['metadata']['total_nodes']} nodes, {graph['metadata']['total_edges']} edges")
    else:
        graph = {
            'metadata': {'total_nodes': 0, 'total_edges': 0, 'source_files': [], 'top_important': []},
            'macros': {},
            'nodes': [],
            'edges': [],
        }
        print(f"No graph found for '{course['name']}'")

    # Load progress
    PROGRESS_PATH = paths['progress_path']
    if os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH, 'r') as f:
            progress = json.load(f)
    else:
        progress = {'nodes': {}}

    # Ensure progress has all expected top-level keys
    progress.setdefault('nodes', {})
    progress.setdefault('quiz_sessions', [])
    progress.setdefault('study_time', {})

    # Load session
    SESSION_PATH = paths['session_path']
    if os.path.exists(SESSION_PATH):
        with open(SESSION_PATH, 'r') as f:
            session = json.load(f)
    else:
        session = {}

    current_course_id = course_id

    # Save last-used course to global session
    _save_global_session()

    return True


def _save_global_session():
    """Save which course was last active."""
    global_session_path = os.path.join(DATA_DIR, 'global_session.json')
    with open(global_session_path, 'w') as f:
        json.dump({'last_course_id': current_course_id}, f)


def save_progress():
    if PROGRESS_PATH:
        os.makedirs(os.path.dirname(PROGRESS_PATH), exist_ok=True)
        with open(PROGRESS_PATH, 'w') as f:
            json.dump(progress, f, indent=2)


def save_session():
    if SESSION_PATH:
        os.makedirs(os.path.dirname(SESSION_PATH), exist_ok=True)
        with open(SESSION_PATH, 'w') as f:
            json.dump(session, f, indent=2)
