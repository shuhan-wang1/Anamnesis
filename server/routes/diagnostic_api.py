"""Diagnostic API routes — identify what the user doesn't know."""

from collections import defaultdict, deque
from flask import Blueprint, jsonify, request
import server.state as state
from server.routes.spaced_repetition import initialize_rl_from_status

diagnostic_bp = Blueprint('diagnostic', __name__)


@diagnostic_bp.route('/diagnostic/targets')
def get_targets():
    """Return top-level nodes for diagnostic rating.

    These are theorems/propositions/corollaries that are "leaf" results
    (nothing else depends on them).
    """
    g = state.graph
    # Find nodes that nothing depends on (no edge has them as target where source is a theorem)
    depended_targets = {e['target'] for e in g['edges']}

    target_types = {'theorem', 'proposition', 'corollary', 'lemma'}
    targets = []
    for n in g['nodes']:
        if n['type'] in target_types:
            targets.append({
                'id': n['id'],
                'type': n['type'],
                'title': n.get('title'),
                'display_number': n.get('display_number'),
                'section_path': n.get('section_path', []),
                'file_source': n.get('file_source'),
                'katex_content': n.get('katex_content', n.get('latex_content', '')),
                'proof_katex': n.get('proof_katex', ''),
                'importance': n.get('importance', 0),
                'is_leaf': n['id'] not in depended_targets,
            })

    # Sort by importance (most important first)
    targets.sort(key=lambda t: -t['importance'])

    return jsonify(targets)


@diagnostic_bp.route('/diagnostic/rate', methods=['POST'])
def rate_nodes():
    """Accept ratings and propagate through dependency graph."""
    data = request.get_json()
    ratings = data.get('ratings', {})  # {node_id: "known"|"shaky"|"unknown"}

    g = state.graph
    progress = state.progress

    # Build dependency map
    depends_on = defaultdict(set)
    for edge in g['edges']:
        if edge['type'] == 'depends_on':
            depends_on[edge['source']].add(edge['target'])

    explicitly_rated = set(ratings.keys())

    for node_id, rating in ratings.items():
        progress['nodes'].setdefault(node_id, {
            'status': rating, 'review_count': 0, 'quiz_history': []
        })
        progress['nodes'][node_id]['status'] = rating
        progress['nodes'][node_id].setdefault('rl', initialize_rl_from_status(rating))

        if rating == 'known':
            # Propagate known downward (optimistic)
            queue = deque(depends_on.get(node_id, []))
            while queue:
                dep = queue.popleft()
                if dep not in explicitly_rated and dep not in progress['nodes']:
                    progress['nodes'][dep] = {
                        'status': 'known', 'review_count': 0, 'quiz_history': [],
                        'rl': initialize_rl_from_status('known'),
                    }
                    queue.extend(depends_on.get(dep, []))

        elif rating == 'unknown':
            # Mark dependencies as unknown unless explicitly rated
            queue = deque(depends_on.get(node_id, []))
            visited = set()
            while queue:
                dep = queue.popleft()
                if dep in visited:
                    continue
                visited.add(dep)
                if dep not in explicitly_rated:
                    existing = progress['nodes'].get(dep, {}).get('status')
                    if existing != 'known':
                        progress['nodes'].setdefault(dep, {
                            'status': 'unknown', 'review_count': 0, 'quiz_history': [],
                        })
                        progress['nodes'][dep]['status'] = 'unknown'
                        progress['nodes'][dep].setdefault('rl', initialize_rl_from_status('unknown'))
                        queue.extend(depends_on.get(dep, []))

    state.save_progress()

    # Return summary
    unknowns = [nid for nid, p in progress['nodes'].items() if p['status'] == 'unknown']
    shaky = [nid for nid, p in progress['nodes'].items() if p['status'] == 'shaky']

    return jsonify({
        'ok': True,
        'total_unknown': len(unknowns),
        'total_shaky': len(shaky),
    })


@diagnostic_bp.route('/diagnostic/unknowns')
def get_unknowns():
    """Return all unknown/shaky nodes sorted by dependency depth."""
    g = state.graph
    progress = state.progress

    unknowns = []
    for n in g['nodes']:
        status = progress['nodes'].get(n['id'], {}).get('status', 'unknown')
        if status in ('unknown', 'shaky'):
            unknowns.append({
                'id': n['id'],
                'type': n['type'],
                'title': n.get('title'),
                'display_number': n.get('display_number'),
                'status': status,
                'section_path': n.get('section_path', []),
                'file_source': n.get('file_source'),
            })

    return jsonify(unknowns)
