"""CLI script: Parse all LaTeX files in input/ and produce parsed_nodes.json + explicit_edges.json."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from parser.latex_parser import parse_all_files
from parser.macro_expander import extract_macros_from_file, merge_macros
from parser.ref_resolver import resolve_references
from parser.katex_converter import convert_for_katex


def run_parse(input_dir: str, data_dir: str, file_order: list[str] | None = None):
    """Parse .tex files and produce parsed_nodes.json + explicit_edges.json.

    Args:
        input_dir: Directory containing .tex source files.
        data_dir: Directory to write output files.
        file_order: Optional ordered list of filenames. If None, auto-detects
                    all .tex files sorted alphabetically.
    """
    os.makedirs(data_dir, exist_ok=True)

    parsed_nodes_path = os.path.join(data_dir, 'parsed_nodes.json')
    explicit_edges_path = os.path.join(data_dir, 'explicit_edges.json')
    macro_registry_path = os.path.join(data_dir, 'macro_registry.json')

    # Build file paths
    if file_order is None:
        # Auto-detect .tex files, sorted alphabetically
        file_order = sorted(
            f for f in os.listdir(input_dir)
            if f.endswith('.tex')
        )

    filepaths = []
    for fname in file_order:
        fp = os.path.join(input_dir, fname)
        if os.path.exists(fp):
            filepaths.append(fp)
        else:
            print(f"Warning: {fname} not found in {input_dir}, skipping")

    if not filepaths:
        print("No .tex files found!")
        # Write empty outputs
        with open(parsed_nodes_path, 'w') as f:
            json.dump([], f)
        with open(explicit_edges_path, 'w') as f:
            json.dump([], f)
        with open(macro_registry_path, 'w') as f:
            json.dump({}, f)
        return

    print(f"Parsing {len(filepaths)} files...")

    # Step 1: Extract macros from all files
    print("  Extracting macros...")
    all_macros = merge_macros([extract_macros_from_file(fp) for fp in filepaths])
    print(f"  Found {len(all_macros)} macros")

    # Save macro registry
    katex_macros = {}
    for name, info in all_macros.items():
        katex_macros[name] = info['expansion']

    with open(macro_registry_path, 'w') as f:
        json.dump(katex_macros, f, indent=2)
    print(f"  Saved macros to {macro_registry_path}")

    # Step 2: Parse all files
    print("  Parsing environments...")
    nodes = parse_all_files(filepaths)
    print(f"  Extracted {len(nodes)} nodes")

    # Count by type
    type_counts = {}
    for n in nodes:
        type_counts[n['type']] = type_counts.get(n['type'], 0) + 1
    for t, c in sorted(type_counts.items()):
        print(f"    {t}: {c}")

    # Step 3: Convert content for KaTeX
    print("  Converting content for KaTeX...")
    for node in nodes:
        node['katex_content'] = convert_for_katex(node['latex_content'])

    # Step 4: Resolve references
    print("  Resolving references...")
    edges = resolve_references(nodes)
    print(f"  Found {len(edges)} explicit edges")

    # Save
    with open(parsed_nodes_path, 'w', encoding='utf-8') as f:
        json.dump(nodes, f, indent=2, ensure_ascii=False)
    print(f"  Saved nodes to {parsed_nodes_path}")

    with open(explicit_edges_path, 'w') as f:
        json.dump(edges, f, indent=2)
    print(f"  Saved edges to {explicit_edges_path}")

    print("Parse complete!")


def main():
    from config import INPUT_DIR, DATA_DIR, FILE_ORDER
    run_parse(INPUT_DIR, DATA_DIR, FILE_ORDER)


if __name__ == '__main__':
    main()
