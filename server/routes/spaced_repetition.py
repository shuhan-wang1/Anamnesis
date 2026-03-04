"""Spaced repetition engine and API routes.

FSRS-inspired scheduling: tracks per-node difficulty and stability to
predict when the user will forget each concept, and prioritizes review
of items closest to being forgotten.

Online RL layer: Thompson Sampling with Beta-distributed per-node failure
probabilities.  The RL component learns from each user interaction and
gradually takes over question selection from the static SR formula.
"""

import math
import random
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

DEFAULT_RL = {
    'alpha': 1.0,       # failure count + prior (Beta parameter)
    'beta': 1.0,        # success count + prior (Beta parameter)
    'last_update': None,
    'total_interactions': 0,
}

RL_SETTINGS = {
    'decay_half_life_days': 14.0,
    'max_rl_weight': 0.7,
    'rl_weight_per_interaction': 0.1,
    'dependency_boost_factor': 0.3,
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


# --- Online RL functions (Thompson Sampling) ---

def _get_decayed_params(rl_state: dict, now: datetime) -> tuple:
    """Apply exponential time decay to Beta parameters.

    Only the evidence portion (above the prior of 1.0) decays, so a node
    with no recent interactions gradually reverts to the uniform prior,
    increasing variance and triggering re-exploration.
    """
    HALF_LIFE_DAYS = RL_SETTINGS['decay_half_life_days']
    DECAY_RATE = math.log(2) / HALF_LIFE_DAYS
    MIN_PARAM = 1.0  # never decay below the prior

    last_update = rl_state.get('last_update')
    if not last_update:
        return (rl_state.get('alpha', 1.0), rl_state.get('beta', 1.0))

    elapsed_days = max((now - datetime.fromisoformat(last_update)).total_seconds() / 86400, 0)
    decay_factor = math.exp(-DECAY_RATE * elapsed_days)

    alpha_raw = rl_state.get('alpha', 1.0)
    beta_raw = rl_state.get('beta', 1.0)

    alpha_evidence = max(alpha_raw - 1.0, 0) * decay_factor
    beta_evidence = max(beta_raw - 1.0, 0) * decay_factor

    return (MIN_PARAM + alpha_evidence, MIN_PARAM + beta_evidence)


def thompson_sample_failure_prob(rl_state: dict, now: datetime = None) -> float:
    """Sample from the posterior Beta distribution for failure probability."""
    now = now or datetime.now()
    alpha_d, beta_d = _get_decayed_params(rl_state, now)
    return random.betavariate(alpha_d, beta_d)


def update_rl_state(rl_state: dict | None, rating: str) -> dict:
    """Update RL state after a review/quiz interaction.

    Decay existing evidence first, then add fresh observation:
      unknown/incorrect  -> alpha += 1   (failure)
      shaky/partial      -> alpha += 0.5, beta += 0.5
      known/correct      -> beta  += 1   (success)
    """
    rl = dict(rl_state) if rl_state else dict(DEFAULT_RL)
    now = datetime.now()

    # Decay historical evidence before adding new observation
    alpha_d, beta_d = _get_decayed_params(rl, now)

    if rating in ('unknown', 'incorrect'):
        alpha_d += 1.0
    elif rating in ('shaky', 'partial'):
        alpha_d += 0.5
        beta_d += 0.5
    elif rating in ('known', 'correct'):
        beta_d += 1.0

    rl['alpha'] = round(alpha_d, 4)
    rl['beta'] = round(beta_d, 4)
    rl['last_update'] = now.isoformat()
    rl['total_interactions'] = rl.get('total_interactions', 0) + 1

    return rl


def initialize_rl_from_status(status: str) -> dict:
    """Warm-start RL state from an initial status assignment."""
    now = datetime.now().isoformat()
    if status == 'unknown':
        return {'alpha': 2.0, 'beta': 1.0, 'last_update': now, 'total_interactions': 0}
    elif status == 'shaky':
        return {'alpha': 1.5, 'beta': 1.5, 'last_update': now, 'total_interactions': 0}
    else:  # known
        return {'alpha': 1.0, 'beta': 2.0, 'last_update': now, 'total_interactions': 0}


def _compute_dependency_boost(node_id: str, edges: list, all_progress: dict, now: datetime) -> float:
    """Boost score if prerequisites have high failure probability.

    boost = 1 + 0.3 * max(prerequisite mean failure probabilities)
    """
    factor = RL_SETTINGS['dependency_boost_factor']
    prereq_ids = [e['target'] for e in edges if e['source'] == node_id and e.get('type') == 'depends_on']

    if not prereq_ids:
        return 1.0

    max_prereq_failure = 0.0
    for prereq_id in prereq_ids:
        prereq_progress = all_progress.get('nodes', {}).get(prereq_id, {})
        prereq_rl = prereq_progress.get('rl', DEFAULT_RL)
        alpha_d, beta_d = _get_decayed_params(prereq_rl, now)
        mean_failure = alpha_d / (alpha_d + beta_d)
        max_prereq_failure = max(max_prereq_failure, mean_failure)

    return 1.0 + factor * max_prereq_failure


def compute_rl_score(node: dict, node_progress: dict, edges: list,
                     all_progress: dict, now: datetime = None) -> float:
    """Compute RL-enhanced selection score for a node.

    score = thompson_sample * importance_weight * dependency_boost * sr_urgency
    """
    now = now or datetime.now()
    rl_state = node_progress.get('rl', DEFAULT_RL)
    sr_state = node_progress.get('sr')
    importance = node.get('importance', 0)

    # 1. Thompson sample (core RL signal)
    theta = thompson_sample_failure_prob(rl_state, now)

    # 2. Importance weight
    importance_weight = 1 + importance / 20

    # 3. Dependency boost
    dep_boost = _compute_dependency_boost(node['id'], edges, all_progress, now)

    # 4. SR urgency (mild boost for items closer to being forgotten)
    sr_urgency = 1.0
    if sr_state and sr_state.get('last_review'):
        retrievability = get_retrievability(sr_state, now)
        sr_urgency = 1 + (1 - retrievability) * 0.5  # [1.0, 1.5]

    return theta * importance_weight * dep_boost * sr_urgency


def migrate_existing_progress(progress: dict, settings: dict = None):
    """One-time migration: create SR and RL state for nodes that were rated
    before those subsystems were added.

    Nodes with a status but no 'sr' sub-object get retroactive SR initialization.
    Nodes with a status but no 'rl' sub-object get warm-started RL state.
    """
    settings = settings or DEFAULT_SETTINGS
    now = datetime.now().isoformat()
    nodes = progress.get('nodes', {})
    migrated_sr = 0
    migrated_rl = 0

    for node_id, node_data in nodes.items():
        status = node_data.get('status')
        if not status:
            continue

        # SR migration
        if not node_data.get('sr'):
            if status == 'known':
                node_data['sr'] = {
                    'difficulty': 0.25,
                    'stability': 1.25,
                    'last_review': now,
                    'reps': 1,
                }
                migrated_sr += 1
            elif status == 'shaky':
                node_data['sr'] = {
                    'difficulty': 0.35,
                    'stability': 0.5,
                    'last_review': now,
                    'reps': 0,
                }
                migrated_sr += 1
            elif status == 'unknown':
                node_data['sr'] = {
                    'difficulty': 0.3,
                    'stability': 0.1,
                    'last_review': now,
                    'reps': 0,
                }
                migrated_sr += 1

        # RL migration
        if not node_data.get('rl'):
            node_data['rl'] = initialize_rl_from_status(status)
            migrated_rl += 1

    if migrated_sr > 0 or migrated_rl > 0:
        progress['_sr_migrated'] = True
        state.save_progress()


def get_due_items(graph_nodes: list, progress: dict, settings: dict = None,
                   limit: int = 20, mode: str = 'hybrid', edges: list = None) -> list:
    """Get items due for review, ranked by RL-enhanced priority.

    mode:
      'sr_only':  Original FSRS priority (backward compatible)
      'rl_only':  Pure Thompson Sampling ranking
      'hybrid':   Weighted combination (default)

    In hybrid mode the RL weight grows with average interactions:
      rl_weight = min(max_rl_weight, rl_weight_per_interaction * avg_interactions)
    """
    settings = settings or DEFAULT_SETTINGS
    rl_cfg = progress.get('rl_settings', RL_SETTINGS)
    edges = edges or []
    now = datetime.now()
    items = []

    for node in graph_nodes:
        if node.get('type') in ('note', 'warning', 'question'):
            continue

        node_progress = progress.get('nodes', {}).get(node['id'], {})
        sr = node_progress.get('sr')
        rl = node_progress.get('rl', dict(DEFAULT_RL))
        importance = node.get('importance', 0)

        # --- SR priority (existing logic) ---
        sr_priority = 0.0
        retrievability = 0.0
        included_by_sr = False

        if sr and sr.get('last_review'):
            retrievability = get_retrievability(sr, now)
            difficulty = sr.get('difficulty', 0.3)
            sr_priority = (1 - retrievability) * (1 + importance / 20) * (1 + difficulty)
            if retrievability < settings['desired_retention']:
                included_by_sr = True
        else:
            status = node_progress.get('status', 'unknown')
            if status in ('unknown', 'shaky') and importance >= 10:
                sr_priority = (1 + importance / 20) * (2.0 if status == 'unknown' else 1.5)
                included_by_sr = True

        # --- RL score ---
        rl_score = compute_rl_score(node, node_progress, edges, progress, now)

        # Include node if SR says it's due OR if RL thinks failure is likely
        # (RL may surface items the SR would skip because retrievability is high)
        alpha_d, beta_d = _get_decayed_params(rl, now)
        mean_failure = alpha_d / (alpha_d + beta_d)
        included_by_rl = mean_failure > 0.5 and rl.get('total_interactions', 0) >= 2

        if not included_by_sr and not included_by_rl:
            continue

        items.append({
            'node_id': node['id'],
            'retrievability': round(retrievability, 3),
            'difficulty': round(sr.get('difficulty', 0.3) if sr else 0.3, 3),
            'stability_days': round(sr['stability'], 2) if sr else 0,
            'sr_priority': round(sr_priority, 3),
            'rl_score': round(rl_score, 4),
            'rl_alpha': round(rl.get('alpha', 1.0), 2),
            'rl_beta': round(rl.get('beta', 1.0), 2),
            'last_review': sr['last_review'] if sr else None,
            'status': node_progress.get('status', 'unknown'),
        })

    if not items:
        return []

    # --- Normalize and combine ---
    if mode == 'sr_only':
        for item in items:
            item['priority'] = item['sr_priority']
    elif mode == 'rl_only':
        for item in items:
            item['priority'] = item['rl_score']
    else:  # hybrid
        max_sr = max((it['sr_priority'] for it in items), default=1.0) or 1.0
        max_rl = max((it['rl_score'] for it in items), default=1.0) or 1.0

        # Adaptive RL weight: increases with average interactions
        all_interactions = [
            progress.get('nodes', {}).get(it['node_id'], {})
            .get('rl', {}).get('total_interactions', 0)
            for it in items
        ]
        avg_interactions = sum(all_interactions) / len(all_interactions) if all_interactions else 0
        rl_weight = min(
            rl_cfg.get('max_rl_weight', 0.7),
            rl_cfg.get('rl_weight_per_interaction', 0.1) * avg_interactions,
        )
        sr_weight = 1 - rl_weight

        for item in items:
            sr_norm = item['sr_priority'] / max_sr
            rl_norm = item['rl_score'] / max_rl
            item['priority'] = round(sr_weight * sr_norm + rl_weight * rl_norm, 4)
            item['rl_weight'] = round(rl_weight, 3)

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
    mode = request.args.get('mode', 'hybrid')
    if mode not in ('hybrid', 'sr_only', 'rl_only'):
        mode = 'hybrid'
    settings = state.progress.get('sr_settings', DEFAULT_SETTINGS)
    migrate_existing_progress(state.progress, settings)
    edges = state.graph.get('edges', [])
    items = get_due_items(state.graph['nodes'], state.progress, settings, limit,
                          mode=mode, edges=edges)
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

    # Update RL state
    rl = node_data.get('rl', dict(DEFAULT_RL))
    updated_rl = update_rl_state(rl, rating)
    node_data['rl'] = updated_rl

    state.save_progress()
    return jsonify({'ok': True, 'sr': updated_sr, 'rl': updated_rl})


@sr_bp.route('/sr/rl-stats')
def api_rl_stats():
    """Return RL algorithm statistics for the dashboard."""
    nodes = state.progress.get('nodes', {})
    rl_cfg = state.progress.get('rl_settings', RL_SETTINGS)

    all_interactions = [
        n.get('rl', {}).get('total_interactions', 0)
        for n in nodes.values() if n.get('rl')
    ]
    nodes_with_rl = len(all_interactions)
    total_interactions = sum(all_interactions)
    avg_interactions = total_interactions / nodes_with_rl if nodes_with_rl else 0

    current_rl_weight = min(
        rl_cfg.get('max_rl_weight', 0.7),
        rl_cfg.get('rl_weight_per_interaction', 0.1) * avg_interactions,
    )

    return jsonify({
        'total_interactions': total_interactions,
        'nodes_with_rl_state': nodes_with_rl,
        'avg_interactions_per_node': round(avg_interactions, 2),
        'current_rl_weight': round(current_rl_weight, 3),
        'mode': 'hybrid',
    })
