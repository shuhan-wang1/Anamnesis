"""Resolve \\ref, \\eqref, and prose references into dependency edges."""

import re


REF_PATTERN = re.compile(r'\\(?:ref|eqref)\{([^}]+)\}')

# "by Lemma 3.2", "from Definition 2.1", "using Theorem 1.3", etc.
PROSE_REF_PATTERN = re.compile(
    r'(?:by|from|see|using|via|applying|of)\s+'
    r'(Theorem|Lemma|Definition|Corollary|Proposition|Remark|Example)\s+'
    r'(\d+\.\d+)',
    re.IGNORECASE,
)

# "Hoeffding's inequality (Lemma \ref{...})" - already caught by REF_PATTERN


def resolve_references(all_nodes: list[dict]) -> list[dict]:
    """Build explicit dependency edges from references in node content.

    Returns list of edge dicts: {"source": id, "target": id, "type": str, "origin": "explicit_ref"|"prose_ref"}
    """
    # Build label -> node_id map
    label_map = {}
    for node in all_nodes:
        if node.get('label'):
            label_map[node['label']] = node['id']

    # Build "Type Number" -> node_id map for prose references
    number_map = {}
    for node in all_nodes:
        if node.get('display_number') and node['type'] not in ('proof', 'proof-sketch'):
            type_name = node['type'].capitalize()
            key = f"{type_name} {node['display_number']}"
            number_map[key] = node['id']

    edges = []
    seen = set()

    for node in all_nodes:
        content = node['latex_content']
        source_id = node['id']

        # \ref{} and \eqref{} references
        for m in REF_PATTERN.finditer(content):
            target_label = m.group(1)
            target_id = label_map.get(target_label)
            if target_id and target_id != source_id:
                edge_key = (source_id, target_id)
                if edge_key not in seen:
                    seen.add(edge_key)
                    edges.append({
                        'source': source_id,
                        'target': target_id,
                        'type': 'depends_on',
                        'origin': 'explicit_ref',
                    })

        # Prose references like "by Lemma 3.2"
        for m in PROSE_REF_PATTERN.finditer(content):
            type_name = m.group(1).capitalize()
            number = m.group(2)
            key = f"{type_name} {number}"
            target_id = number_map.get(key)
            if target_id and target_id != source_id:
                edge_key = (source_id, target_id)
                if edge_key not in seen:
                    seen.add(edge_key)
                    edges.append({
                        'source': source_id,
                        'target': target_id,
                        'type': 'depends_on',
                        'origin': 'prose_ref',
                    })

    # Add "proves" edges
    for node in all_nodes:
        if node.get('proves'):
            target_id = node['proves']
            # The 'proves' field may be a label, resolve it
            if target_id in label_map:
                target_id = label_map[target_id]
            edge_key = (node['id'], target_id)
            if edge_key not in seen:
                seen.add(edge_key)
                edges.append({
                    'source': node['id'],
                    'target': target_id,
                    'type': 'proves',
                    'origin': 'structural',
                })

    return edges
