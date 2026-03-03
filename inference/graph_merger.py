"""Merge explicit references and LLM-inferred dependencies into final graph."""

import json


def merge_edges(explicit_edges: list[dict], inferred_edges: list[dict]) -> list[dict]:
    """Merge and deduplicate edges from multiple sources."""
    seen = set()
    merged = []

    # Explicit edges take priority
    for edge in explicit_edges:
        key = (edge['source'], edge['target'], edge['type'])
        if key not in seen:
            seen.add(key)
            merged.append(edge)

    # Add inferred edges that don't duplicate
    for edge in inferred_edges:
        key = (edge['source'], edge['target'], edge['type'])
        # Also check without type (same source/target with different type)
        key_simple = (edge['source'], edge['target'])
        existing_simple = {(e['source'], e['target']) for e in merged}
        if key not in seen and key_simple not in existing_simple:
            seen.add(key)
            merged.append(edge)

    return merged


def build_knowledge_graph(
    nodes: list[dict],
    edges: list[dict],
    macros: dict,
    source_files: list[str],
) -> dict:
    """Build the final knowledge graph JSON structure."""
    # Validate edges: ensure all endpoints exist
    node_ids = {n['id'] for n in nodes}
    valid_edges = [
        e for e in edges
        if e['source'] in node_ids and e['target'] in node_ids
    ]

    invalid_count = len(edges) - len(valid_edges)
    if invalid_count > 0:
        print(f"  Warning: dropped {invalid_count} edges with invalid endpoints")

    return {
        'metadata': {
            'source_files': source_files,
            'total_nodes': len(nodes),
            'total_edges': len(valid_edges),
        },
        'macros': macros,
        'nodes': nodes,
        'edges': valid_edges,
    }
