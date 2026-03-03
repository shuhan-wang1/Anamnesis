"""Learning path API — curated study plan with importance-based selection."""

from collections import defaultdict, deque
from flask import Blueprint, jsonify, request
import server.state as state

learning_bp = Blueprint('learning', __name__)


def _node_payload(n, progress):
    """Build a node dict for API response."""
    status = progress.get('nodes', {}).get(n['id'], {}).get('status', 'unknown')
    return {
        'id': n['id'],
        'type': n['type'],
        'title': n.get('title'),
        'display_number': n.get('display_number'),
        'katex_content': n.get('katex_content', n.get('latex_content', '')),
        'proof_katex': n.get('proof_katex', ''),
        'section_path': n.get('section_path', []),
        'file_source': n.get('file_source'),
        'importance': n.get('importance', 0),
        'status': status,
    }


@learning_bp.route('/learning/study-plan')
def get_study_plan():
    """Return a curated study plan organized by topic sections.

    Groups the most important nodes by their top-level section,
    orders sections by file order (foundations first),
    and within each section orders by dependency (definitions → theorems).
    """
    g = state.graph
    progress = state.progress

    # Skip low-value types
    skip_types = {'note', 'warning', 'question', 'exercise', 'problem'}

    # Collect important nodes
    important_nodes = []
    for n in g['nodes']:
        if n['type'] in skip_types:
            continue
        imp = n.get('importance', 0)
        if imp >= 10:  # Only include somewhat important nodes
            important_nodes.append(n)

    # Group by top-level section
    section_groups = defaultdict(list)
    for n in important_nodes:
        sp = n.get('section_path', [])
        section = sp[0] if sp else 'Uncategorized'
        section_groups[section].append(n)

    # Order nodes within each section by type priority then importance
    type_order = {
        'definition': 0, 'lemma': 1, 'proposition': 2,
        'theorem': 3, 'corollary': 4, 'algorithm': 5,
        'example': 6, 'remark': 7,
    }

    topics = []
    for section, nodes in section_groups.items():
        nodes.sort(key=lambda n: (type_order.get(n['type'], 9), -n.get('importance', 0)))

        # Stats
        total = len(nodes)
        known = sum(1 for n in nodes
                    if progress.get('nodes', {}).get(n['id'], {}).get('status') == 'known')
        shaky = sum(1 for n in nodes
                    if progress.get('nodes', {}).get(n['id'], {}).get('status') == 'shaky')

        # Get file_index for ordering sections
        file_idx = min((n.get('file_index', 99) for n in nodes), default=99)

        topics.append({
            'section': section,
            'file_index': file_idx,
            'total': total,
            'known': known,
            'shaky': shaky,
            'nodes': [_node_payload(n, progress) for n in nodes],
        })

    # Sort topics by file order
    topics.sort(key=lambda t: t['file_index'])

    return jsonify({
        'topics': topics,
        'total_nodes': sum(t['total'] for t in topics),
        'total_known': sum(t['known'] for t in topics),
    })


@learning_bp.route('/learning/path/<path:target_id>')
def get_learning_path(target_id):
    """Return bottom-up learning path for a specific target node."""
    g = state.graph
    progress = state.progress
    node_map = {n['id']: n for n in g['nodes']}

    if target_id not in node_map:
        return jsonify({'error': 'Target node not found'}), 404

    path_ids = _compute_deps_path(g, target_id, progress)
    path_nodes = [_node_payload(node_map[nid], progress)
                  for nid in path_ids if nid in node_map]

    return jsonify({
        'target_id': target_id,
        'target': _node_payload(node_map[target_id], progress),
        'path': path_nodes,
        'total_steps': len(path_nodes),
    })


@learning_bp.route('/learning/auto')
def get_auto_learning_path():
    """Auto-generate a learning path for the most important unknown theorem."""
    g = state.graph
    progress = state.progress

    # Find unknown/shaky theorems sorted by importance
    candidates = []
    for n in g['nodes']:
        if n['type'] in ('theorem', 'proposition', 'lemma', 'corollary'):
            status = progress.get('nodes', {}).get(n['id'], {}).get('status', 'unknown')
            if status in ('unknown', 'shaky'):
                candidates.append(n)

    if not candidates:
        return jsonify({'path': [], 'total_steps': 0, 'message': 'All theorems known!'})

    candidates.sort(key=lambda n: -n.get('importance', 0))
    target = candidates[0]

    path_ids = _compute_deps_path(g, target['id'], progress)
    node_map = {n['id']: n for n in g['nodes']}
    path_nodes = [_node_payload(node_map[nid], progress)
                  for nid in path_ids if nid in node_map]

    return jsonify({
        'target_id': target['id'],
        'target': _node_payload(target, progress),
        'path': path_nodes,
        'total_steps': len(path_nodes),
    })


def _compute_deps_path(graph, target_id, progress):
    """Bottom-up learning path: BFS backward + topological sort."""
    depends_on = defaultdict(set)
    for edge in graph['edges']:
        if edge['type'] == 'depends_on':
            depends_on[edge['source']].add(edge['target'])

    ancestors = set()
    queue = deque([target_id])
    while queue:
        current = queue.popleft()
        for dep in depends_on.get(current, []):
            if dep not in ancestors:
                ancestors.add(dep)
                queue.append(dep)
    ancestors.add(target_id)

    # Filter to unknown/shaky
    def is_unknown(nid):
        status = progress.get('nodes', {}).get(nid, {}).get('status', 'unknown')
        return status in ('unknown', 'shaky')

    unknown_ancestors = {nid for nid in ancestors if is_unknown(nid)}
    if not unknown_ancestors:
        return []

    # Topological sort
    in_degree = defaultdict(int)
    sub_edges = defaultdict(set)
    for nid in unknown_ancestors:
        for dep in depends_on.get(nid, []):
            if dep in unknown_ancestors:
                sub_edges[dep].add(nid)
                in_degree[nid] += 1

    queue = deque([nid for nid in unknown_ancestors if in_degree[nid] == 0])
    topo_order = []
    while queue:
        current = queue.popleft()
        topo_order.append(current)
        for dependent in sub_edges.get(current, []):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    remaining = unknown_ancestors - set(topo_order)
    topo_order.extend(sorted(remaining))
    return topo_order
