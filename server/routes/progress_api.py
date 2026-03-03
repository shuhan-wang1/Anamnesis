"""Progress and session API routes."""

from datetime import datetime
from flask import Blueprint, jsonify, request
import server.state as state
from server.routes.spaced_repetition import update_sr_state, DEFAULT_SR, DEFAULT_SETTINGS

progress_bp = Blueprint('progress', __name__)


@progress_bp.route('/progress')
def get_progress():
    """Return all user progress."""
    return jsonify(state.progress)


@progress_bp.route('/progress/<path:node_id>', methods=['POST'])
def update_progress(node_id):
    """Update progress for a single node."""
    data = request.get_json()
    status = data.get('status', 'unknown')
    source = data.get('source', 'manual')  # manual, quiz, diagnostic, learning

    if status not in ('unknown', 'shaky', 'known'):
        return jsonify({'error': 'Invalid status'}), 400

    now = datetime.now().isoformat()

    if node_id not in state.progress['nodes']:
        state.progress['nodes'][node_id] = {
            'status': status,
            'review_count': 0,
            'quiz_history': [],
            'first_seen': now,
            'last_reviewed': now,
        }
    else:
        state.progress['nodes'][node_id]['last_reviewed'] = now

    prev_status = state.progress['nodes'][node_id].get('status')
    state.progress['nodes'][node_id]['status'] = status
    state.progress['nodes'][node_id]['review_count'] = \
        state.progress['nodes'][node_id].get('review_count', 0) + 1

    # Track status change history
    state.progress['nodes'][node_id].setdefault('history', [])
    state.progress['nodes'][node_id]['history'].append({
        'from': prev_status,
        'to': status,
        'source': source,
        'at': now,
    })
    # Keep last 20 history entries per node
    state.progress['nodes'][node_id]['history'] = \
        state.progress['nodes'][node_id]['history'][-20:]

    # Update spaced repetition state
    settings = state.progress.get('sr_settings', DEFAULT_SETTINGS)
    sr = state.progress['nodes'][node_id].get('sr', dict(DEFAULT_SR))
    state.progress['nodes'][node_id]['sr'] = update_sr_state(sr, status, settings)

    state.save_progress()
    return jsonify({'ok': True, 'node_id': node_id, 'status': status})


@progress_bp.route('/progress/reset', methods=['POST'])
def reset_progress():
    """Reset all progress."""
    sr_settings = state.progress.get('sr_settings')
    state.progress = {'nodes': {}, 'quiz_sessions': [], 'study_time': {}}
    if sr_settings:
        state.progress['sr_settings'] = sr_settings
    state.save_progress()
    state.session = {}
    state.save_session()
    return jsonify({'ok': True})


# --- Session state (UI persistence) ---

@progress_bp.route('/session', methods=['GET'])
def get_session():
    """Return saved UI session state."""
    return jsonify(state.session)


@progress_bp.route('/session', methods=['POST'])
def save_session():
    """Save UI session state. Merges with existing session."""
    data = request.get_json()
    state.session.update(data)
    state.save_session()
    return jsonify({'ok': True})


@progress_bp.route('/session/<key>', methods=['POST'])
def save_session_key(key):
    """Save a single session key."""
    data = request.get_json()
    state.session[key] = data.get('value')
    state.save_session()
    return jsonify({'ok': True})


# --- Quiz session tracking ---

@progress_bp.route('/quiz/complete', methods=['POST'])
def complete_quiz():
    """Record a completed quiz session."""
    data = request.get_json()
    now = datetime.now().isoformat()

    session_record = {
        'type': data.get('type'),
        'scope': data.get('scope', 'all'),
        'total': data.get('total', 0),
        'correct': data.get('correct', 0),
        'items': data.get('items', []),  # [{node_id, rating}]
        'completed_at': now,
    }

    state.progress.setdefault('quiz_sessions', [])
    state.progress['quiz_sessions'].append(session_record)
    # Keep last 50 quiz sessions
    state.progress['quiz_sessions'] = state.progress['quiz_sessions'][-50:]

    # Update individual node quiz history
    for item in session_record.get('items', []):
        nid = item.get('node_id')
        if nid and nid in state.progress['nodes']:
            state.progress['nodes'][nid].setdefault('quiz_history', [])
            state.progress['nodes'][nid]['quiz_history'].append({
                'type': session_record['type'],
                'rating': item.get('rating'),
                'at': now,
            })
            # Keep last 10 per node
            state.progress['nodes'][nid]['quiz_history'] = \
                state.progress['nodes'][nid]['quiz_history'][-10:]

    state.save_progress()
    return jsonify({'ok': True})
