"""CLI script: Build final knowledge graph with concept deps, proof folding, importance."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from inference.graph_merger import merge_edges, build_knowledge_graph
from inference.concept_analyzer import analyze_dependencies, rank_importance
from parser.katex_converter import convert_for_katex


def run_build(data_dir: str, file_order: list[str] | None = None):
    """Build the final knowledge graph from parsed data.

    Args:
        data_dir: Directory containing parsed_nodes.json, explicit_edges.json, etc.
        file_order: Optional file ordering list. If None, extracted from nodes.
    """
    parsed_nodes_path = os.path.join(data_dir, 'parsed_nodes.json')
    explicit_edges_path = os.path.join(data_dir, 'explicit_edges.json')
    inferred_edges_path = os.path.join(data_dir, 'inferred_edges.json')
    knowledge_graph_path = os.path.join(data_dir, 'knowledge_graph.json')
    macro_registry_path = os.path.join(data_dir, 'macro_registry.json')
    name_cache_path = os.path.join(data_dir, 'name_cache.json')

    with open(parsed_nodes_path, 'r', encoding='utf-8') as f:
        nodes = json.load(f)

    if not nodes:
        # Empty graph
        graph = {
            'metadata': {'source_files': [], 'total_nodes': 0, 'total_edges': 0, 'top_important': []},
            'macros': {},
            'nodes': [],
            'edges': [],
        }
        with open(knowledge_graph_path, 'w', encoding='utf-8') as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
        print("No nodes to build graph from.")
        return

    with open(explicit_edges_path, 'r') as f:
        explicit_edges = json.load(f)

    inferred_edges = []
    if os.path.exists(inferred_edges_path):
        with open(inferred_edges_path, 'r') as f:
            inferred_edges = json.load(f)

    # Content-based dependency analysis
    print("Running content-based dependency analysis...")
    concept_edges = analyze_dependencies(nodes)
    print(f"  Found {len(concept_edges)} concept-based edges")

    macros = {}
    if os.path.exists(macro_registry_path):
        with open(macro_registry_path, 'r') as f:
            macros = json.load(f)

    # Merge all edge sources
    print(f"Merging {len(explicit_edges)} explicit + {len(inferred_edges)} inferred + {len(concept_edges)} concept edges...")
    all_edges = merge_edges(explicit_edges, inferred_edges + concept_edges)
    print(f"Total unique edges: {len(all_edges)}")

    # Fold proofs into their parent theorems
    print("Folding proofs into parent theorems...")
    proof_ids = set()
    node_map = {n['id']: n for n in nodes}
    for n in nodes:
        if n['type'] in ('proof', 'proof-sketch') and n.get('proves'):
            parent_id = n['proves']
            # Resolve label to id if needed
            if parent_id in node_map:
                parent = node_map[parent_id]
            else:
                # Try to find by label
                parent = next((p for p in nodes if p.get('label') == parent_id), None)
            if parent:
                parent['proof_content'] = n.get('latex_content', '')
                parent['proof_katex'] = n.get('katex_content', '')
                proof_ids.add(n['id'])

    nodes_clean = [n for n in nodes if n['id'] not in proof_ids]
    all_edges = [e for e in all_edges if e['source'] not in proof_ids and e['target'] not in proof_ids]
    print(f"  Folded {len(proof_ids)} proofs, {len(nodes_clean)} nodes remain")

    # Build label map for \ref resolution
    print("Building label map for \\ref resolution...")
    label_map = {}
    for n in nodes_clean:
        if n.get('label'):
            display = f"{n['type'].capitalize()} {n.get('display_number', '')}"
            if n.get('title'):
                display += f" ({n['title']})"
            label_map[n['label']] = display.strip()
    # Also add labels from non-proof nodes that were folded or pruned
    for n in nodes:
        if n.get('label') and n['label'] not in label_map and n.get('type') != 'proof':
            display = f"{n['type'].capitalize()} {n.get('display_number', '')}"
            label_map[n['label']] = display.strip()

    # Re-run KaTeX conversion with label map for better \ref resolution
    print("Re-running KaTeX conversion with label map...")
    for n in nodes_clean:
        if n.get('latex_content'):
            n['katex_content'] = convert_for_katex(n['latex_content'], label_map)
        if n.get('proof_content'):
            n['proof_katex'] = convert_for_katex(n['proof_content'], label_map)

    # Apply cached auto-names
    if os.path.exists(name_cache_path):
        with open(name_cache_path, 'r', encoding='utf-8') as f:
            name_cache = json.load(f)
        named_count = 0
        for n in nodes_clean:
            if n.get('title') is None and n['id'] in name_cache:
                n['title'] = name_cache[n['id']]
                named_count += 1
        if named_count:
            print(f"  Applied {named_count} cached auto-names")

    # Compute importance scores
    print("Computing importance scores...")
    importance = rank_importance(nodes_clean, all_edges)
    for n in nodes_clean:
        n['importance'] = importance.get(n['id'], 0)

    # Determine file order from nodes if not provided
    if file_order is None:
        seen = set()
        file_order = []
        for n in nodes_clean:
            fs = n.get('file_source', '')
            if fs and fs not in seen:
                seen.add(fs)
                file_order.append(fs)

    # Build final graph
    graph = build_knowledge_graph(nodes_clean, all_edges, macros, file_order)

    # Add top important nodes to metadata
    ranked = sorted(
        [(n['id'], n['importance'], n['type'], n.get('title', ''))
         for n in nodes_clean if n['type'] not in ('note', 'warning', 'question')],
        key=lambda x: -x[1]
    )
    graph['metadata']['top_important'] = [
        {'id': nid, 'score': score, 'type': ntype, 'title': title}
        for nid, score, ntype, title in ranked[:30]
    ]

    with open(knowledge_graph_path, 'w', encoding='utf-8') as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)

    print(f"\nKnowledge graph saved to {knowledge_graph_path}")
    print(f"  Nodes: {graph['metadata']['total_nodes']}")
    print(f"  Edges: {graph['metadata']['total_edges']}")
    if ranked:
        print(f"\nTop 10 most important for exam:")
        for item in ranked[:10]:
            print(f"  [{item[1]}] {item[2]}: {item[3] or item[0]}")
    print("Build complete!")


def main():
    from config import DATA_DIR, FILE_ORDER
    run_build(DATA_DIR, FILE_ORDER)


if __name__ == '__main__':
    main()
