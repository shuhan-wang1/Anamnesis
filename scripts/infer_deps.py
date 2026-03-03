"""CLI script: Run LLM dependency inference using Claude API."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import DATA_DIR, PARSED_NODES_PATH, INFERRED_EDGES_PATH, INFERENCE_MODEL
from inference.dependency_inferrer import infer_all_dependencies


def main():
    # Check for API key
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        print("Set it with: export ANTHROPIC_API_KEY=your-key-here")
        sys.exit(1)

    # Load parsed nodes
    if not os.path.exists(PARSED_NODES_PATH):
        print(f"Error: {PARSED_NODES_PATH} not found. Run parse_all.py first.")
        sys.exit(1)

    with open(PARSED_NODES_PATH, 'r', encoding='utf-8') as f:
        nodes = json.load(f)

    print(f"Loaded {len(nodes)} nodes")
    print(f"Using model: {INFERENCE_MODEL}")

    # Initialize Anthropic client
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)

    print("Running dependency inference...")
    edges = infer_all_dependencies(
        nodes=nodes,
        client=client,
        model=INFERENCE_MODEL,
        cache_path=INFERRED_EDGES_PATH,
    )

    print(f"Inferred {len(edges)} dependency edges")

    with open(INFERRED_EDGES_PATH, 'w') as f:
        json.dump(edges, f, indent=2)
    print(f"Saved to {INFERRED_EDGES_PATH}")
    print("Done!")


if __name__ == '__main__':
    main()
