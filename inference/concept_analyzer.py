"""Content-based dependency analysis — no LLM required.

Analyzes the mathematical content of each node to determine which definitions
and concepts it uses. Works by:
1. Building a "concept signature" for each definition (key terms, symbols, notation)
2. Scanning each theorem/lemma for usage of those concepts
3. Using file ordering to respect temporal ordering (can't depend on later content)
"""

import re
from collections import defaultdict


def _extract_concept_terms(node: dict) -> set[str]:
    """Extract key mathematical terms and symbols from a node's content."""
    content = node.get('latex_content', '')
    title = node.get('title', '') or ''

    terms = set()

    # Add title words (lowercased, excluding common words)
    stop_words = {
        'the', 'a', 'an', 'of', 'for', 'and', 'or', 'in', 'on', 'is', 'are',
        'we', 'let', 'given', 'then', 'that', 'with', 'from', 'to', 'if',
        'be', 'by', 'as', 'at', 'it', 'not', 'can', 'has', 'have', 'this',
        'any', 'all', 'each', 'there', 'some', 'such', 'where', 'which',
        'also', 'may', 'set', 'case', 'note', 'i.e.', 'e.g.',
    }
    for word in re.findall(r'[A-Za-z]+', title):
        w = word.lower()
        if w not in stop_words and len(w) > 2:
            terms.add(w)

    # Extract key mathematical notation patterns
    # \mathcal{X}, \mathbb{R}, etc.
    for m in re.finditer(r'\\math(?:cal|bb|bf|rm)\{([A-Za-z])\}', content):
        terms.add(f'math_{m.group(1)}')

    # Named operators: \operatorname{...}
    for m in re.finditer(r'\\operatorname\*?\{([^}]+)\}', content):
        terms.add(m.group(1).lower())

    # Key phrases that identify concepts
    concept_phrases = [
        r'hypothesis\s+class', r'hypothesis\s+space', r'VC\s+dimension',
        r'Rademacher', r'PAC', r'bayes\s+error', r'bayes\s+estimator',
        r'bayes\s+classifier', r'empirical\s+error', r'expected\s+error',
        r'generali[sz]ation\s+error', r'loss\s+function', r'square\s+loss',
        r'hinge\s+loss', r'margin', r'kernel', r'kernel\s+trick',
        r'SVM', r'support\s+vector', r'separating\s+hyperplane',
        r'perceptron', r'gradient\s+descent', r'regulariz',
        r'ridge\s+regression', r'cross.?validation', r'bias.?variance',
        r'overfitting', r'underfitting', r'training\s+error',
        r'nearest\s+neighbor', r'k-?NN', r'decision\s+tree',
        r'boosting', r'AdaBoost', r'ensemble', r'random\s+forest',
        r'linear\s+model', r'feature\s+map', r'dual', r'primal',
        r'Lagrangian', r'KKT', r'Hoeffding', r'union\s+bound',
        r'concentration\s+inequalit', r'shattering', r'growth\s+function',
        r'Sauer', r'online\s+learning', r'regret', r'expert',
        r'multiplicative\s+weight', r'weighted\s+majority',
        r'graph\s+Laplacian', r'Laplacian', r'spectral',
        r'realizab', r'agnostic', r'ERM', r'uniform\s+convergence',
        r'sample\s+complexity', r'no\s+free\s+lunch',
        r'representer\s+theorem', r'kernel\s+matrix', r'Gram\s+matrix',
        r'Mercer', r'positive\s+definite', r'RKHS',
        r'soft\s+margin', r'slack\s+variable', r'C-?SVM',
        r'classification', r'regression', r'binary\s+classification',
        r'multi.?class', r'logistic', r'sigmoid',
    ]

    combined = (title + ' ' + content).lower()
    for phrase in concept_phrases:
        if re.search(phrase, combined, re.IGNORECASE):
            # Normalize the phrase
            terms.add(re.sub(r'\\s\+|\\s\*|\[.?\]', '_', phrase).lower().replace('\\', ''))

    return terms


def analyze_dependencies(nodes: list[dict]) -> list[dict]:
    """Analyze content-based dependencies between nodes.

    Returns list of edge dicts.
    """
    # Build concept signatures for definitions
    def_signatures = {}
    node_by_id = {n['id']: n for n in nodes}

    for n in nodes:
        if n['type'] == 'definition':
            sig = _extract_concept_terms(n)
            if sig:
                def_signatures[n['id']] = sig

    # For each non-definition node, find which definitions it likely uses
    edges = []
    seen = set()

    for i, node in enumerate(nodes):
        if node['type'] in ('definition',):
            continue

        node_terms = _extract_concept_terms(node)
        node_content_lower = (node.get('latex_content', '') + ' ' + (node.get('title', '') or '')).lower()

        # Only look at definitions that appear before this node (same file or earlier files)
        for def_id, def_sig in def_signatures.items():
            def_node = node_by_id[def_id]

            # Must be from same or earlier file
            if def_node.get('file_index', 0) > node.get('file_index', 0):
                continue
            # If same file, must appear earlier in the node list
            def_idx = next((j for j, n in enumerate(nodes) if n['id'] == def_id), -1)
            if def_idx >= i:
                continue

            # Check overlap
            overlap = node_terms & def_sig
            if len(overlap) >= 2:  # at least 2 shared concept terms
                edge_key = (node['id'], def_id)
                if edge_key not in seen:
                    seen.add(edge_key)
                    edges.append({
                        'source': node['id'],
                        'target': def_id,
                        'type': 'depends_on',
                        'origin': 'content_analysis',
                        'confidence': len(overlap),
                    })

            # Also check if the definition's title appears in this node's content
            def_title = (def_node.get('title') or '').lower()
            if def_title and len(def_title) > 3 and def_title in node_content_lower:
                edge_key = (node['id'], def_id)
                if edge_key not in seen:
                    seen.add(edge_key)
                    edges.append({
                        'source': node['id'],
                        'target': def_id,
                        'type': 'depends_on',
                        'origin': 'title_match',
                        'confidence': 5,  # high confidence for title match
                    })

    return edges


def rank_importance(nodes: list[dict], edges: list[dict]) -> list[dict]:
    """Rank nodes by importance for exam preparation.

    Importance heuristics:
    1. Theorems with proofs are most important (they'll be on the exam)
    2. Definitions that many theorems depend on are critical foundations
    3. Nodes with more dependencies are more "connected" = more important
    4. Named theorems (have a title) are more important than unnamed ones
    """
    # Count inbound edges (how many things depend on me)
    depended_count = defaultdict(int)
    depends_count = defaultdict(int)
    for e in edges:
        depended_count[e['target']] += 1
        depends_count[e['source']] += 1

    # Find which nodes have proofs
    has_proof = set()
    for n in nodes:
        if n.get('proves'):
            has_proof.add(n['proves'])

    importance_scores = {}
    for n in nodes:
        nid = n['id']
        score = 0

        # Base score by type (theorems/lemmas most exam-relevant)
        type_scores = {
            'theorem': 20,
            'lemma': 15,
            'proposition': 16,
            'corollary': 14,
            'definition': 12,
            'algorithm': 10,
            'example': 4,
            'remark': 3,
            'proof': 0,
            'proof-sketch': 0,
            'exercise': 5,
            'problem': 5,
            'note': 1,
            'warning': 1,
            'question': 2,
        }
        score += type_scores.get(n['type'], 1)

        # Bonus for having a name/title (named theorems are exam staples)
        if n.get('title'):
            score += 5

        # Bonus for having a proof (exam-relevant)
        if nid in has_proof or n.get('proof_content'):
            score += 8

        # Bonus for being depended on (capped to avoid dominance)
        dep_bonus = min(depended_count.get(nid, 0), 10)
        score += dep_bonus

        # Small bonus for depending on many things (complex node)
        score += min(depends_count.get(nid, 0), 5)

        importance_scores[nid] = score

    return importance_scores
