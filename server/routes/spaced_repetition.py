"""Spaced repetition engine and API routes.

FSRS-inspired scheduling: tracks per-node difficulty and stability to
predict when the user will forget each concept, and prioritizes review
of items closest to being forgotten.
"""

import math
from datetime import datetime
from flask import Blueprint, jsonify, request
import server.state as state

sr_bp = Blueprint('sr', __name__)

# --- Default parameters ---

DEFAULT_SR = {
    'difficulty': 0.3,
    'stability': 0.5,  # days until recall drops to desired_retention
    'last_review': None,
    'reps': 0,
}

DEFAULT_SETTINGS = {
    'desired_retention': 0.9,
    'base_stability': 0.5,
    'stability_growth_known': 2.5,
    'stability_growth_shaky': 1.0,
    'stability_growth_unknown': 0.2,
    'difficulty_delta_known': -0.05,
    'difficulty_delta_shaky': 0.05,
    'difficulty_delta_unknown': 0.15,
    'max_difficulty': 1.0,
    'min_difficulty': 0.0,
}


# --- Core SR functions ---

def get_retrievability(sr_state: dict, now: datetime = None) -> float:
    """Compute current retrievability (recall probability) for a node."""
    if not sr_state or not sr_state.get('last_review'):
        return 0.0
    now = now or datetime.now()
    last = datetime.fromisoformat(sr_state['last_review'])
    elapsed_days = max((now - last).total_seconds() / 86400, 0)
    stability = sr_state.get('stability', 0.5)
    if stability <= 0:
        return 0.0
    return math.exp(-elapsed_days / stability)


def update_sr_state(sr_state: dict | None, rating: str, settings: dict = None) -> dict:
    """Update SR state after a review.

    rating: 'known', 'shaky', or 'unknown'
    """
    settings = settings or DEFAULT_SETTINGS
    now = datetime.now().isoformat()

    sr = dict(sr_state) if sr_state else dict(DEFAULT_SR)

    if rating == 'known':
        sr['stability'] = max(sr.get('stability', 0.5), settings['base_stability']) * settings['stability_growth_known']
        sr['difficulty'] = max(
            settings['min_difficulty'],
            sr.get('difficulty', 0.3) + settings['difficulty_delta_known']
        )
        sr['reps'] = sr.get('reps', 0) + 1
    elif rating == 'shaky':
        sr['stability'] = max(sr.get('stability', 0.5), settings['base_stability']) * settings['stability_growth_shaky']
        sr['difficulty'] = min(
            settings['max_difficulty'],
            sr.get('difficulty', 0.3) + settings['difficulty_delta_shaky']
        )
        sr['reps'] = max(0, sr.get('reps', 0) - 1)
    elif rating == 'unknown':
        sr['stability'] = settings['base_stability'] * settings['stability_growth_unknown']
        sr['difficulty'] = min(
            settings['max_difficulty'],
            sr.get('difficulty', 0.3) + settings['difficulty_delta_unknown']
        )
        sr['reps'] = 0

    sr['last_review'] = now
    return sr


def migrate_existing_progress(progress: dict, settings: dict = None):
    """One-time migration: create SR state for nodes that were rated before SR was added.

    Nodes with a status but no 'sr' sub-object get retroactive SR initialization
    so they appear in the SR dashboard and due-item calculations.
    """
    if progress.get('_sr_migrated'):
        return  # already done

    settings = settings or DEFAULT_SETTINGS
    now = datetime.now().isoformat()
    nodes = progress.get('nodes', {})
    migrated = 0

    for node_id, node_data in nodes.items():
        if node_data.get('sr'):
            continue  # already has SR state
        status = node_data.get('status')
        if not status:
            continue

        if status == 'known':
            node_data['sr'] = {
                'difficulty': 0.25,
                'stability': 1.25,  # review in ~1 day
                'last_review': now,
                'reps': 1,
            }
            migrated += 1
        elif status == 'shaky':
            node_data['sr'] = {
                'difficulty': 0.35,
                'stability': 0.5,
                'last_review': now,
                'reps': 0,
            }
            migrated += 1
        elif status == 'unknown':
            node_data['sr'] = {
                'difficulty': 0.3,
                'stability': 0.1,
                'last_review': now,
                'reps': 0,
            }
            migrated += 1

    if migrated > 0:
        progress['_sr_migrated'] = True
        state.save_progress()


def get_due_items(graph_nodes: list, progress: dict, settings: dict = None, limit: int = 20) -> list:
    """Get items due for review, sorted by priority.

    Priority = (1 - retrievability) * importance_weight * (1 + difficulty)
    """
    settings = settings or DEFAULT_SETTINGS
    now = datetime.now()
    items = []

    for node in graph_nodes:
        # Skip minor types
        if node.get('type') in ('note', 'warning', 'question'):
            continue

        node_progress = progress.get('nodes', {}).get(node['id'], {})
        sr = node_progress.get('sr')
        importance = node.get('importance', 0)

        if sr and sr.get('last_review'):
            retrievability = get_retrievability(sr, now)
            difficulty = sr.get('difficulty', 0.3)
            priority = (1 - retrievability) * (1 + importance / 20) * (1 + difficulty)

            if retrievability < settings['desired_retention']:
                items.append({
                    'node_id': node['id'],
                    'retrievability': round(retrievability, 3),
                    'difficulty': round(difficulty, 3),
                    'stability_days': round(sr['stability'], 2),
                    'priority': round(priority, 3),
                    'last_review': sr['last_review'],
                    'status': node_progress.get('status', 'unknown'),
                })
        else:
            # Never reviewed via SR — include unknown/shaky items
            status = node_progress.get('status', 'unknown')
            if status in ('unknown', 'shaky') and importance >= 10:
                base_priority = (1 + importance / 20) * (2.0 if status == 'unknown' else 1.5)
                items.append({
                    'node_id': node['id'],
                    'retrievability': 0.0,
                    'difficulty': 0.3,
                    'stability_days': 0,
                    'priority': round(base_priority, 3),
                    'last_review': None,
                    'status': status,
                })

    items.sort(key=lambda x: -x['priority'])
    return items[:limit]


def get_sr_summary(graph_nodes: list, progress: dict, settings: dict = None) -> dict:
    """Get summary stats for the dashboard."""
    settings = settings or DEFAULT_SETTINGS
    now = datetime.now()

    total_reviewed = 0
    due_today = 0
    total_retrievability = 0.0

    for node in graph_nodes:
        if node.get('type') in ('note', 'warning', 'question'):
            continue
        node_progress = progress.get('nodes', {}).get(node['id'], {})
        sr = node_progress.get('sr')
        if sr and sr.get('last_review'):
            total_reviewed += 1
            r = get_retrievability(sr, now)
            total_retrievability += r
            if r < settings['desired_retention']:
                due_today += 1

    avg_retrievability = total_retrievability / total_reviewed if total_reviewed > 0 else 0

    return {
        'total_in_sr': total_reviewed,
        'due_for_review': due_today,
        'avg_retrievability': round(avg_retrievability, 3),
        'retention_target': settings['desired_retention'],
    }


# --- API Routes ---

@sr_bp.route('/sr/due')
def api_get_due():
    """Get items due for spaced repetition review."""
    limit = int(request.args.get('limit', 20))
    settings = state.progress.get('sr_settings', DEFAULT_SETTINGS)
    migrate_existing_progress(state.progress, settings)
    items = get_due_items(state.graph['nodes'], state.progress, settings, limit)
    return jsonify(items)


@sr_bp.route('/sr/summary')
def api_sr_summary():
    """Get SR summary stats for dashboard."""
    settings = state.progress.get('sr_settings', DEFAULT_SETTINGS)
    migrate_existing_progress(state.progress, settings)
    summary = get_sr_summary(state.graph['nodes'], state.progress, settings)
    return jsonify(summary)


@sr_bp.route('/sr/review', methods=['POST'])
def api_record_review():
    """Record an SR review result and update the node's SR state."""
    data = request.get_json()
    node_id = data.get('node_id')
    rating = data.get('rating')

    if rating not in ('known', 'shaky', 'unknown'):
        return jsonify({'error': 'Invalid rating'}), 400

    settings = state.progress.get('sr_settings', DEFAULT_SETTINGS)

    if node_id not in state.progress['nodes']:
        state.progress['nodes'][node_id] = {
            'status': rating, 'review_count': 0, 'quiz_history': [],
        }

    node_data = state.progress['nodes'][node_id]
    sr = node_data.get('sr', dict(DEFAULT_SR))
    updated_sr = update_sr_state(sr, rating, settings)
    node_data['sr'] = updated_sr
    node_data['status'] = rating

    state.save_progress()
    return jsonify({'ok': True, 'sr': updated_sr})
