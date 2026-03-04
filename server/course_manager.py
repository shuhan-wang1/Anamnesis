"""Course management — CRUD operations and parse pipeline integration."""

import json
import os
import re
import shutil
from datetime import datetime


DATA_DIR = None  # Set by init()


def init(data_dir: str):
    global DATA_DIR
    DATA_DIR = data_dir
    os.makedirs(os.path.join(DATA_DIR, 'courses'), exist_ok=True)


def auto_migrate_legacy(data_dir: str, input_dir: str):
    """Auto-migrate legacy single-course data into courses/ structure on startup.

    Checks if courses.json exists. If not, looks for legacy data files
    (knowledge_graph.json, parsed_nodes.json, etc.) in data_dir root and
    .tex files in input_dir. If found, migrates them to a default course.
    """
    courses_file = os.path.join(data_dir, 'courses.json')
    if os.path.exists(courses_file):
        return  # Already migrated

    # Check if there's any legacy data to migrate
    legacy_files = [
        'knowledge_graph.json', 'parsed_nodes.json', 'explicit_edges.json',
        'inferred_edges.json', 'macro_registry.json', 'name_cache.json',
        'user_progress.json', 'session.json',
    ]
    has_legacy_data = any(
        os.path.exists(os.path.join(data_dir, f)) for f in legacy_files
    )
    has_tex_files = (
        os.path.exists(input_dir) and
        any(f.endswith('.tex') for f in os.listdir(input_dir))
    )

    if not has_legacy_data and not has_tex_files:
        return  # Nothing to migrate

    print("Auto-migrating legacy data to course structure...")

    courses_dir = os.path.join(data_dir, 'courses')
    default_dir = os.path.join(courses_dir, 'default')
    default_input = os.path.join(default_dir, 'input')
    os.makedirs(default_input, exist_ok=True)

    # Copy data files
    copied = 0
    for fname in legacy_files:
        src = os.path.join(data_dir, fname)
        dst = os.path.join(default_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            copied += 1
            print(f"  Migrated {fname}")

    # Copy input .tex files
    tex_files = []
    if os.path.exists(input_dir):
        for fname in os.listdir(input_dir):
            if fname.endswith('.tex'):
                src = os.path.join(input_dir, fname)
                dst = os.path.join(default_input, fname)
                shutil.copy2(src, dst)
                tex_files.append(fname)

    # Count nodes from knowledge graph
    node_count = 0
    kg_path = os.path.join(default_dir, 'knowledge_graph.json')
    if os.path.exists(kg_path):
        with open(kg_path, 'r', encoding='utf-8') as f:
            graph = json.load(f)
            node_count = graph.get('metadata', {}).get('total_nodes', 0)

    # Create courses.json
    courses = [{
        'id': 'default',
        'name': 'Imported Course',
        'created_at': datetime.now().isoformat(),
        'file_count': len(tex_files),
        'node_count': node_count,
        'files': tex_files,
    }]

    with open(courses_file, 'w', encoding='utf-8') as f:
        json.dump(courses, f, indent=2, ensure_ascii=False)

    print(f"  Migration complete: {copied} data files, {len(tex_files)} .tex files, {node_count} nodes")


def _courses_file():
    return os.path.join(DATA_DIR, 'courses.json')


def load_courses() -> list[dict]:
    path = _courses_file()
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_courses(courses: list):
    with open(_courses_file(), 'w', encoding='utf-8') as f:
        json.dump(courses, f, indent=2, ensure_ascii=False)


def get_course(course_id: str) -> dict | None:
    for c in load_courses():
        if c['id'] == course_id:
            return c
    return None


def get_course_dir(course_id: str) -> str:
    return os.path.join(DATA_DIR, 'courses', course_id)


def get_course_paths(course_id: str) -> dict:
    """Return all file paths for a course."""
    d = get_course_dir(course_id)
    return {
        'course_dir': d,
        'input_dir': os.path.join(d, 'input'),
        'graph_path': os.path.join(d, 'knowledge_graph.json'),
        'progress_path': os.path.join(d, 'user_progress.json'),
        'session_path': os.path.join(d, 'session.json'),
        'parsed_nodes_path': os.path.join(d, 'parsed_nodes.json'),
        'explicit_edges_path': os.path.join(d, 'explicit_edges.json'),
        'inferred_edges_path': os.path.join(d, 'inferred_edges.json'),
        'macro_registry_path': os.path.join(d, 'macro_registry.json'),
        'name_cache_path': os.path.join(d, 'name_cache.json'),
    }


def _slugify(name: str) -> str:
    """Convert course name to a filesystem-safe ID."""
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'[\s_]+', '-', slug).strip('-')
    return slug[:50] if slug else 'course'


def create_course(name: str, tex_files: dict[str, bytes]) -> dict:
    """Create a new course from uploaded .tex files.

    Args:
        name: Course display name.
        tex_files: {filename: file_bytes} for each uploaded .tex file.

    Returns:
        Course metadata dict.
    """
    # Generate unique ID
    slug = _slugify(name)
    course_id = slug
    existing_ids = {c['id'] for c in load_courses()}
    counter = 1
    while course_id in existing_ids:
        course_id = f"{slug}-{counter}"
        counter += 1

    # Create directory structure
    paths = get_course_paths(course_id)
    os.makedirs(paths['input_dir'], exist_ok=True)

    # Save .tex files
    saved_files = []
    for filename, content in tex_files.items():
        filepath = os.path.join(paths['input_dir'], filename)
        with open(filepath, 'wb') as f:
            f.write(content)
        saved_files.append(filename)

    # Run parse pipeline
    run_parse_pipeline(course_id)

    # Count nodes from built graph
    node_count = 0
    if os.path.exists(paths['graph_path']):
        with open(paths['graph_path'], 'r', encoding='utf-8') as f:
            graph = json.load(f)
            node_count = graph.get('metadata', {}).get('total_nodes', 0)

    # Save course metadata
    course = {
        'id': course_id,
        'name': name,
        'created_at': datetime.now().isoformat(),
        'file_count': len(saved_files),
        'node_count': node_count,
        'files': saved_files,
    }
    courses = load_courses()
    courses.append(course)
    save_courses(courses)

    return course


def delete_course(course_id: str) -> bool:
    """Delete a course and all its data."""
    courses = load_courses()
    courses = [c for c in courses if c['id'] != course_id]
    save_courses(courses)

    course_dir = get_course_dir(course_id)
    if os.path.exists(course_dir):
        shutil.rmtree(course_dir)
        return True
    return False


def update_course_meta(course_id: str):
    """Refresh course metadata (node_count, file_count) from disk."""
    courses = load_courses()
    paths = get_course_paths(course_id)
    for c in courses:
        if c['id'] == course_id:
            # Count files
            input_dir = paths['input_dir']
            if os.path.exists(input_dir):
                c['files'] = [f for f in os.listdir(input_dir) if f.endswith('.tex')]
                c['file_count'] = len(c['files'])
            # Count nodes
            if os.path.exists(paths['graph_path']):
                with open(paths['graph_path'], 'r', encoding='utf-8') as f:
                    graph = json.load(f)
                    c['node_count'] = graph.get('metadata', {}).get('total_nodes', 0)
            break
    save_courses(courses)


def run_parse_pipeline(course_id: str):
    """Run the full parse + build pipeline for a course."""
    paths = get_course_paths(course_id)
    input_dir = paths['input_dir']
    data_dir = paths['course_dir']

    # Import pipeline functions
    from scripts.parse_all import run_parse
    from scripts.build_graph import run_build

    run_parse(input_dir, data_dir)
    run_build(data_dir)
