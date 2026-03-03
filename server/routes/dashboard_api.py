"""Dashboard API — exam readiness stats."""

from collections import defaultdict
from flask import Blueprint, jsonify
import server.state as state

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
def get_dashboard():
    """Return exam readiness dashboard data."""
    g = state.graph
    progress = state.progress

    # Count by status
    total = len(g['nodes'])
    known = 0
    shaky = 0
    unknown = 0

    for n in g['nodes']:
        status = progress.get('nodes', {}).get(n['id'], {}).get('status', 'unknown')
        if status == 'known':
            known += 1
        elif status == 'shaky':
            shaky += 1
        else:
            unknown += 1

    # Breakdown by type
    type_stats = defaultdict(lambda: {'known': 0, 'shaky': 0, 'unknown': 0, 'total': 0})
    for n in g['nodes']:
        t = n['type']
        status = progress.get('nodes', {}).get(n['id'], {}).get('status', 'unknown')
        type_stats[t][status] += 1
        type_stats[t]['total'] += 1

    # Critical gaps: unknown nodes depended on by the most other unknown nodes
    depends_on = defaultdict(set)
    for edge in g['edges']:
        if edge['type'] == 'depends_on':
            depends_on[edge['source']].add(edge['target'])

    # Count how many unknown nodes depend on each unknown node
    dep_count = defaultdict(int)
    for n in g['nodes']:
        status = progress.get('nodes', {}).get(n['id'], {}).get('status', 'unknown')
        if status in ('unknown', 'shaky'):
            for dep in depends_on.get(n['id'], []):
                dep_status = progress.get('nodes', {}).get(dep, {}).get('status', 'unknown')
                if dep_status in ('unknown', 'shaky'):
                    dep_count[dep] += 1

    # Top critical gaps
    node_map = {n['id']: n for n in g['nodes']}
    critical_gaps = sorted(dep_count.items(), key=lambda x: -x[1])[:10]
    critical_gap_nodes = []
    for nid, count in critical_gaps:
        n = node_map.get(nid)
        if n:
            critical_gap_nodes.append({
                'id': n['id'],
                'type': n['type'],
                'title': n.get('title'),
                'display_number': n.get('display_number'),
                'file_source': n.get('file_source'),
                'dependency_count': count,
            })

    # File stats
    file_stats = defaultdict(lambda: {'known': 0, 'shaky': 0, 'unknown': 0, 'total': 0})
    for n in g['nodes']:
        f = n.get('file_source', 'unknown')
        status = progress.get('nodes', {}).get(n['id'], {}).get('status', 'unknown')
        file_stats[f][status] += 1
        file_stats[f]['total'] += 1

    readiness = round(known / total * 100, 1) if total > 0 else 0

    return jsonify({
        'readiness_percent': readiness,
        'total': total,
        'known': known,
        'shaky': shaky,
        'unknown': unknown,
        'type_stats': dict(type_stats),
        'file_stats': dict(file_stats),
        'critical_gaps': critical_gap_nodes,
    })
