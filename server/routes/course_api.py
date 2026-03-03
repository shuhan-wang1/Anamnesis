"""Course management API routes."""

from flask import Blueprint, jsonify, request
import server.state as state
from server import course_manager as cm

course_bp = Blueprint('courses', __name__)


@course_bp.route('/courses')
def list_courses():
    """List all courses with which one is currently active."""
    courses = cm.load_courses()
    return jsonify({
        'courses': courses,
        'active_course_id': state.current_course_id,
    })


@course_bp.route('/courses/current')
def get_current_course():
    """Get currently active course info."""
    if not state.current_course_id:
        return jsonify({'course': None})
    course = cm.get_course(state.current_course_id)
    return jsonify({'course': course})


@course_bp.route('/courses', methods=['POST'])
def create_course():
    """Create a new course from uploaded .tex files.

    Expects multipart/form-data with:
      - name: course display name
      - files: one or more .tex files
    """
    name = request.form.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Course name is required'}), 400

    uploaded_files = request.files.getlist('files')
    if not uploaded_files:
        return jsonify({'error': 'At least one .tex file is required'}), 400

    # Filter to .tex files only
    tex_files = {}
    for f in uploaded_files:
        filename = f.filename
        if not filename:
            continue
        # Handle folder uploads: extract just the filename
        if '/' in filename:
            filename = filename.split('/')[-1]
        if '\\' in filename:
            filename = filename.split('\\')[-1]
        if filename.endswith('.tex'):
            tex_files[filename] = f.read()

    if not tex_files:
        return jsonify({'error': 'No .tex files found in upload'}), 400

    try:
        course = cm.create_course(name, tex_files)
        # Auto-switch to the new course
        state.switch_course(course['id'])
        return jsonify({'ok': True, 'course': course})
    except Exception as e:
        return jsonify({'error': f'Failed to create course: {str(e)}'}), 500


@course_bp.route('/courses/<course_id>/switch', methods=['POST'])
def switch_course(course_id):
    """Switch to a different course."""
    course = cm.get_course(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    success = state.switch_course(course_id)
    if success:
        return jsonify({'ok': True, 'course': course})
    return jsonify({'error': 'Failed to switch course'}), 500


@course_bp.route('/courses/<course_id>', methods=['DELETE'])
def delete_course(course_id):
    """Delete a course and all its data."""
    # Don't allow deleting the currently active course if it's the only one
    courses = cm.load_courses()
    if len(courses) <= 1:
        return jsonify({'error': 'Cannot delete the only remaining course'}), 400

    if course_id == state.current_course_id:
        # Switch to another course first
        other = next(c for c in courses if c['id'] != course_id)
        state.switch_course(other['id'])

    cm.delete_course(course_id)
    return jsonify({'ok': True})


@course_bp.route('/courses/<course_id>/rebuild', methods=['POST'])
def rebuild_course(course_id):
    """Re-run the parse pipeline for a course."""
    course = cm.get_course(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    try:
        cm.run_parse_pipeline(course_id)
        cm.update_course_meta(course_id)

        # If this is the active course, reload the graph
        if course_id == state.current_course_id:
            state.switch_course(course_id)

        return jsonify({'ok': True, 'course': cm.get_course(course_id)})
    except Exception as e:
        return jsonify({'error': f'Failed to rebuild: {str(e)}'}), 500


@course_bp.route('/courses/<course_id>/upload', methods=['POST'])
def upload_files(course_id):
    """Add more .tex files to an existing course and rebuild."""
    course = cm.get_course(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    import os
    uploaded_files = request.files.getlist('files')
    paths = cm.get_course_paths(course_id)

    saved = 0
    for f in uploaded_files:
        filename = f.filename
        if not filename:
            continue
        if '/' in filename:
            filename = filename.split('/')[-1]
        if '\\' in filename:
            filename = filename.split('\\')[-1]
        if filename.endswith('.tex'):
            filepath = os.path.join(paths['input_dir'], filename)
            f.save(filepath)
            saved += 1

    if saved == 0:
        return jsonify({'error': 'No .tex files found in upload'}), 400

    # Rebuild after adding files
    try:
        cm.run_parse_pipeline(course_id)
        cm.update_course_meta(course_id)

        if course_id == state.current_course_id:
            state.switch_course(course_id)

        return jsonify({'ok': True, 'files_added': saved, 'course': cm.get_course(course_id)})
    except Exception as e:
        return jsonify({'error': f'Failed to rebuild after upload: {str(e)}'}), 500
