"""Graph API routes."""

from flask import Blueprint, jsonify
import server.state as state

graph_bp = Blueprint('graph', __name__)


@graph_bp.route('/graph')
def get_graph():
    """Return full graph for D3.js visualization."""
    g = state.graph
    # Return simplified nodes for the graph view
    nodes = []
    for n in g['nodes']:
        nodes.append({
            'id': n['id'],
            'type': n['type'],
            'title': n.get('title'),
            'display_number': n.get('display_number'),
            'section_path': n.get('section_path', []),
            'file_source': n.get('file_source'),
        })
    return jsonify({
        'nodes': nodes,
        'edges': g['edges'],
        'macros': g.get('macros', {}),
        'metadata': g['metadata'],
    })


@graph_bp.route('/nodes')
def get_all_nodes():
    """Return all nodes with content for browse view."""
    g = state.graph
    nodes = []
    for n in g['nodes']:
        nodes.append({
            'id': n['id'],
            'type': n['type'],
            'title': n.get('title'),
            'display_number': n.get('display_number'),
            'section_path': n.get('section_path', []),
            'file_source': n.get('file_source'),
            'katex_content': n.get('katex_content', ''),
            'proof_katex': n.get('proof_katex', ''),
            'importance': n.get('importance', 0),
        })
    return jsonify(nodes)


@graph_bp.route('/node/<path:node_id>')
def get_node(node_id):
    """Return full node detail."""
    g = state.graph
    for n in g['nodes']:
        if n['id'] == node_id:
            # Find edges involving this node
            deps = [e for e in g['edges'] if e['source'] == node_id]
            depended_by = [e for e in g['edges'] if e['target'] == node_id]
            return jsonify({
                **n,
                'dependencies': deps,
                'depended_by': depended_by,
            })
    return jsonify({'error': 'Node not found'}), 404


@graph_bp.route('/macros')
def get_macros():
    """Return KaTeX macros."""
    return jsonify(state.graph.get('macros', {}))
