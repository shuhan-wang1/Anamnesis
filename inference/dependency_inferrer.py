"""LLM-based dependency inference using Claude API."""

import json
import os
import time

from inference.prompt_templates import SYSTEM_PROMPT, build_inference_prompt


def infer_dependencies_for_node(
    target: dict,
    candidates: list[dict],
    client,
    model: str,
) -> list[str]:
    """Infer dependencies for a single node using Claude API.

    Returns list of dependency node IDs.
    """
    if not candidates:
        return []

    prompt = build_inference_prompt(target, candidates)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        # Handle markdown code block wrapping
        if "```" in text:
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1].strip()
                if text.startswith("json"):
                    text = text[4:].strip()

        dep_ids = json.loads(text)

        # Validate: only keep IDs that exist in candidates
        valid_ids = {c['id'] for c in candidates}
        return [d for d in dep_ids if d in valid_ids]

    except (json.JSONDecodeError, IndexError, KeyError):
        return []
    except Exception as e:
        print(f"  API error for {target['id']}: {e}")
        return []


def infer_all_dependencies(
    nodes: list[dict],
    client,
    model: str,
    cache_path: str | None = None,
) -> list[dict]:
    """Run dependency inference for all non-definition nodes.

    Returns list of edge dicts.
    """
    # Load cache if exists
    cache = {}
    if cache_path and os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            cached_edges = json.load(f)
            for edge in cached_edges:
                cache.setdefault(edge['source'], []).append(edge['target'])

    # Types that need dependency inference (they depend on other things)
    infer_types = {'theorem', 'lemma', 'corollary', 'proposition', 'remark', 'example', 'proof', 'proof-sketch'}

    # Types that can be candidates (things that get depended on)
    candidate_types = {'definition', 'theorem', 'lemma', 'corollary', 'proposition', 'remark', 'example'}

    edges = []
    total = sum(1 for n in nodes if n['type'] in infer_types and n['id'] not in cache)
    done = 0

    for i, node in enumerate(nodes):
        if node['type'] not in infer_types:
            continue

        # Use cache if available
        if node['id'] in cache:
            for target_id in cache[node['id']]:
                edges.append({
                    'source': node['id'],
                    'target': target_id,
                    'type': 'depends_on',
                    'origin': 'llm_inferred',
                })
            continue

        # Build candidate list: all prior nodes of candidate types
        candidates = [
            n for n in nodes[:i]
            if n['type'] in candidate_types
        ]

        if not candidates:
            continue

        done += 1
        print(f"  [{done}/{total}] Inferring deps for {node['type']} {node.get('display_number', '')} "
              f"({node.get('title', node['id'])})")

        dep_ids = infer_dependencies_for_node(node, candidates, client, model)

        for target_id in dep_ids:
            edges.append({
                'source': node['id'],
                'target': target_id,
                'type': 'depends_on',
                'origin': 'llm_inferred',
            })

        # Rate limiting
        time.sleep(0.5)

        # Periodic cache save
        if cache_path and done % 10 == 0:
            _save_edges(edges, cache_path)

    # Final cache save
    if cache_path:
        _save_edges(edges, cache_path)

    return edges


def _save_edges(edges: list[dict], path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(edges, f, indent=2)
