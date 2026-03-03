"""CLI script: Auto-name unnamed nodes.

Uses Claude API if ANTHROPIC_API_KEY is set, otherwise falls back to
heuristic naming based on LaTeX content analysis.

Usage:
    python scripts/name_nodes.py             # Name all unnamed nodes (uses cache)
    python scripts/name_nodes.py --force     # Re-name all, ignoring cache
    python scripts/name_nodes.py --dry-run   # Preview without saving
    python scripts/name_nodes.py --heuristic # Force heuristic mode (no API)
"""

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import KNOWLEDGE_GRAPH_PATH, NAME_CACHE_PATH, INFERENCE_MODEL

# Types worth auto-naming
NAMEABLE_TYPES = {'theorem', 'definition', 'lemma', 'corollary', 'proposition', 'example', 'remark'}


def main():
    force = '--force' in sys.argv
    dry_run = '--dry-run' in sys.argv
    force_heuristic = '--heuristic' in sys.argv

    # Load knowledge graph
    with open(KNOWLEDGE_GRAPH_PATH, 'r', encoding='utf-8') as f:
        graph = json.load(f)

    nodes = graph['nodes']

    # Load cache
    cache = {}
    if os.path.exists(NAME_CACHE_PATH) and not force:
        with open(NAME_CACHE_PATH, 'r', encoding='utf-8') as f:
            cache = json.load(f)

    # Find unnamed nodes that need naming
    to_name = [
        n for n in nodes
        if n.get('title') is None
        and n['type'] in NAMEABLE_TYPES
        and n['id'] not in cache
    ]

    total_unnamed = sum(1 for n in nodes if n.get('title') is None and n['type'] in NAMEABLE_TYPES)
    already_cached = total_unnamed - len(to_name)

    print(f"Total unnamed nameable nodes: {total_unnamed}")
    print(f"Already cached: {already_cached}")
    print(f"To name: {len(to_name)}")

    if len(to_name) == 0:
        print("Nothing to do!")
        if not dry_run:
            _apply_names(graph, cache)
        return

    if dry_run:
        print("\n--- DRY RUN (heuristic preview) ---")
        for n in to_name[:10]:
            name = _heuristic_name(n)
            type_name = n['type'].capitalize()
            number = n.get('display_number', '?')
            print(f"  {type_name} {number} -> \"{name}\"")
        if len(to_name) > 10:
            print(f"  ... and {len(to_name) - 10} more")
        return

    # Try Claude API first (if available and not forced heuristic)
    use_api = False
    if not force_heuristic:
        try:
            import anthropic
            client = anthropic.Anthropic()
            # Test with a quick call
            client.messages.create(
                model=INFERENCE_MODEL,
                max_tokens=10,
                messages=[{"role": "user", "content": "Say 'ok'"}],
            )
            use_api = True
            print(f"\nUsing Claude API ({INFERENCE_MODEL})")
        except Exception as e:
            print(f"\nClaude API not available ({e})")
            print("Falling back to heuristic naming...")

    if use_api:
        _name_with_api(to_name, cache, client)
    else:
        _name_with_heuristics(to_name, cache)

    # Save cache
    os.makedirs(os.path.dirname(NAME_CACHE_PATH), exist_ok=True)
    with open(NAME_CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
    print(f"\nCache saved: {len(cache)} names in {NAME_CACHE_PATH}")

    # Apply names to graph
    _apply_names(graph, cache)
    print("Done!")


def _name_with_api(to_name, cache, client):
    """Name nodes using Claude API."""
    from inference.prompt_templates import NAMING_SYSTEM_PROMPT, build_naming_prompt

    named = 0
    errors = 0

    for i, node in enumerate(to_name):
        type_name = node['type'].capitalize()
        number = node.get('display_number', '?')

        try:
            prompt = build_naming_prompt(node)
            response = client.messages.create(
                model=INFERENCE_MODEL,
                max_tokens=50,
                system=NAMING_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            name = response.content[0].text.strip().strip('"').strip("'")
            words = name.split()
            if len(words) > 8:
                name = ' '.join(words[:5])
            if len(words) == 0:
                name = None

            if name:
                cache[node['id']] = name
                named += 1
                print(f"  [{i+1}/{len(to_name)}] {type_name} {number} -> \"{name}\"")
            else:
                errors += 1

        except Exception as e:
            errors += 1
            print(f"  [{i+1}/{len(to_name)}] {type_name} {number} -> ERROR: {e}")

        if i < len(to_name) - 1:
            time.sleep(0.3)

    print(f"\nAPI naming: {named} named, {errors} errors")


def _name_with_heuristics(to_name, cache):
    """Name nodes using content analysis heuristics."""
    named = 0

    for i, node in enumerate(to_name):
        type_name = node['type'].capitalize()
        number = node.get('display_number', '?')
        name = _heuristic_name(node)

        if name:
            cache[node['id']] = name
            named += 1
            print(f"  [{i+1}/{len(to_name)}] {type_name} {number} -> \"{name}\"")

    print(f"\nHeuristic naming: {named} named")


def _heuristic_name(node: dict) -> str:
    """Generate a descriptive name from LaTeX content using heuristics."""
    content = node.get('latex_content', '')
    section_path = node.get('section_path', [])
    node_type = node['type']

    # Strategy 1: Extract key math concepts from the content
    name = _extract_concept_name(content, node_type)
    if name:
        return name

    # Strategy 2: Use the most specific section name
    if section_path:
        last_section = section_path[-1]
        # Strip numbering like "3.2 " from section titles
        last_section = re.sub(r'^\d+(\.\d+)*\s*', '', last_section).strip()
        if last_section and len(last_section) <= 40:
            return last_section

    # Strategy 3: First meaningful sentence
    return _extract_first_phrase(content)


def _extract_concept_name(content: str, node_type: str) -> str | None:
    """Try to extract a concept name from LaTeX content."""
    # Common patterns that define concepts
    patterns = [
        # "We say X is ..."  / "A function f is called X if ..."
        r'(?:we\s+(?:say|call|define)|is\s+called|is\s+said\s+to\s+be)\s+[a-z]*\s*\*?\s*\\?(?:textbf|textit|emph)?\{?([A-Z][a-z]+(?:\s+[A-Za-z]+){0,3})',
        # "The X of ..." / "An X is ..."
        r'(?:^|\.\s+)(?:The|A|An)\s+\\?(?:textbf|textit|emph)?\{?([A-Z][a-z]+(?:\s+[A-Za-z]+){0,3})\}?\s+(?:of|is|for)',
        # Bold/italic terms (often the defined concept)
        r'\\textbf\{([^}]{3,30})\}',
        r'\\textit\{([^}]{3,30})\}',
        r'\\emph\{([^}]{3,30})\}',
    ]

    for pat in patterns:
        m = re.search(pat, content, re.IGNORECASE)
        if m:
            name = m.group(1).strip().strip('{}')
            # Clean up LaTeX artifacts
            name = re.sub(r'\\[a-zA-Z]+\{?', '', name).strip('}{ ')
            if 2 <= len(name.split()) <= 6 and len(name) <= 40:
                return _title_case(name)

    # For definitions: look for "Let X denote" / "Define X"
    if node_type == 'definition':
        m = re.search(r'(?:Let|Define|Denote)\s+(?:the\s+)?\\?(?:\w+\{)?([A-Za-z][A-Za-z\s]{2,25})', content)
        if m:
            name = m.group(1).strip().strip('{}')
            name = re.sub(r'\\[a-zA-Z]+\{?', '', name).strip('}{ ')
            if 1 <= len(name.split()) <= 5 and len(name) <= 30:
                return _title_case(name)

    # For theorems: look for key inequality/bound patterns
    if node_type in ('theorem', 'lemma', 'proposition', 'corollary'):
        # Check for well-known bound/inequality patterns
        bound_patterns = [
            (r'\\leq.*\\frac', 'Upper Bound'),
            (r'\\geq.*\\frac', 'Lower Bound'),
            (r'convergence|converges', 'Convergence'),
            (r'regret', 'Regret Bound'),
            (r'generalization|generaliz', 'Generalization Bound'),
            (r'concentration|concentrate', 'Concentration Inequality'),
            (r'if\s+and\s+only\s+if', 'Characterization'),
            (r'positive\s+(?:semi)?definite', 'Positive Definiteness'),
            (r'equivalent|equivalence', 'Equivalence'),
            (r'unique|uniqueness', 'Uniqueness'),
            (r'exist|existence', 'Existence'),
            (r'optimal|optimality', 'Optimality'),
        ]
        for pat, label in bound_patterns:
            if re.search(pat, content, re.IGNORECASE):
                # Try to make it more specific with context
                return _contextualize(label, content)

    return None


def _contextualize(base_label: str, content: str) -> str:
    """Add context from content to a base label."""
    # Look for key mathematical objects mentioned
    objects = []
    object_patterns = [
        (r'\\(?:mathcal|mathbb)\{([A-Z])\}', None),  # \mathcal{H}, \mathbb{R}
        (r'kernel', 'Kernel'),
        (r'loss', 'Loss'),
        (r'risk', 'Risk'),
        (r'classifier', 'Classifier'),
        (r'hypothesis', 'Hypothesis'),
        (r'margin', 'Margin'),
        (r'norm', 'Norm'),
        (r'matrix', 'Matrix'),
        (r'eigenvalue', 'Eigenvalue'),
        (r'gradient', 'Gradient'),
        (r'VC\s*dim', 'VC Dimension'),
        (r'Rademacher', 'Rademacher'),
    ]

    for pat, label in object_patterns:
        if re.search(pat, content, re.IGNORECASE):
            if label:
                objects.append(label)
            break  # Take first match only

    if objects:
        return f"{objects[0]} {base_label}"
    return base_label


def _extract_first_phrase(content: str) -> str:
    """Extract first meaningful phrase from content as a name."""
    # Strip math and commands
    text = re.sub(r'\$[^$]+\$', '', content)
    text = re.sub(r'\\[a-zA-Z]+\{?', '', text)
    text = re.sub(r'[{}\\]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()

    # Take first meaningful words
    words = [w for w in text.split() if len(w) > 1 and w[0].isalpha()]
    if len(words) >= 2:
        phrase = ' '.join(words[:4])
        if len(phrase) <= 40:
            return _title_case(phrase)
        return _title_case(' '.join(words[:3]))

    return "Unnamed"


def _title_case(s: str) -> str:
    """Convert to title case, keeping short words lowercase."""
    small_words = {'a', 'an', 'the', 'of', 'in', 'for', 'on', 'at', 'to', 'by', 'is', 'and', 'or', 'with'}
    words = s.split()
    result = []
    for i, w in enumerate(words):
        if i == 0 or w.lower() not in small_words:
            result.append(w.capitalize() if w.islower() else w)
        else:
            result.append(w.lower())
    return ' '.join(result)


def _apply_names(graph, cache):
    """Apply cached names to the knowledge graph and save."""
    applied = 0
    for n in graph['nodes']:
        if n.get('title') is None and n['id'] in cache:
            n['title'] = cache[n['id']]
            applied += 1

    if applied > 0:
        with open(KNOWLEDGE_GRAPH_PATH, 'w', encoding='utf-8') as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
        print(f"Applied {applied} names to knowledge graph")


if __name__ == '__main__':
    main()
