"""Quiz API — generate quiz items in multiple modes."""

import random
import re
from flask import Blueprint, jsonify, request
import server.state as state

quiz_bp = Blueprint('quiz', __name__)


def _get_quiz_pool(scope: str | None) -> list[dict]:
    """Get the pool of nodes for quizzing based on scope."""
    g = state.graph
    progress = state.progress

    nodes = g['nodes']

    if scope == 'unknown':
        nodes = [
            n for n in nodes
            if progress.get('nodes', {}).get(n['id'], {}).get('status', 'unknown')
            in ('unknown', 'shaky')
        ]
    elif scope == 'shaky':
        nodes = [
            n for n in nodes
            if progress.get('nodes', {}).get(n['id'], {}).get('status') == 'shaky'
        ]

    return nodes


def _make_blanks(text: str, num_blanks: int = 2) -> dict:
    """Create fill-in-the-blank version of content.

    Blanks out key mathematical expressions.
    """
    # Find $...$ inline math expressions
    math_spans = list(re.finditer(r'\$([^$]+)\$', text))
    if not math_spans:
        return {'blanked': text, 'answers': []}

    # Pick random spans to blank
    to_blank = random.sample(math_spans, min(num_blanks, len(math_spans)))
    to_blank.sort(key=lambda m: m.start(), reverse=True)

    answers = []
    blanked = text
    for m in to_blank:
        answers.append(m.group(0))
        blanked = blanked[:m.start()] + '$ \\boxed{?} $' + blanked[m.end():]

    answers.reverse()  # correct order
    return {'blanked': blanked, 'answers': answers}


@quiz_bp.route('/quiz/generate')
def generate_quiz():
    """Generate quiz items.

    Query params:
        type: definition_recall | theorem_statement | proof_reconstruction | reverse_quiz | fill_blank
        count: number of items (default 5)
        scope: all | unknown | shaky (default all)
    """
    quiz_type = request.args.get('type', 'definition_recall')
    count = int(request.args.get('count', 5))
    scope = request.args.get('scope', 'all')

    pool = _get_quiz_pool(scope if scope != 'all' else None)

    if quiz_type == 'definition_recall':
        # Show name -> recall definition
        candidates = [n for n in pool if n['type'] == 'definition' and n.get('title')]
        random.shuffle(candidates)
        items = []
        for n in candidates[:count]:
            items.append({
                'node_id': n['id'],
                'quiz_type': 'definition_recall',
                'prompt': f"Definition: {n['title']}",
                'prompt_subtitle': f"{n.get('display_number', '')} from {n.get('file_source', '')}",
                'answer': n.get('katex_content', n.get('latex_content', '')),
            })
        return jsonify(items)

    elif quiz_type == 'theorem_statement':
        # Show name -> recall theorem
        candidates = [
            n for n in pool
            if n['type'] in ('theorem', 'proposition', 'corollary', 'lemma')
            and n.get('title')
        ]
        random.shuffle(candidates)
        items = []
        for n in candidates[:count]:
            type_name = n['type'].capitalize()
            items.append({
                'node_id': n['id'],
                'quiz_type': 'theorem_statement',
                'prompt': f"{type_name}: {n['title']}",
                'prompt_subtitle': f"{n.get('display_number', '')} from {n.get('file_source', '')}",
                'answer': n.get('katex_content', n.get('latex_content', '')),
            })
        return jsonify(items)

    elif quiz_type == 'proof_reconstruction':
        # Show theorem statement -> recall proof
        # Proofs are now folded into their parent nodes as proof_katex
        candidates = [
            n for n in pool
            if n.get('proof_katex') and n['type'] in ('theorem', 'lemma', 'proposition', 'corollary')
        ]

        random.shuffle(candidates)
        items = []
        for n in candidates[:count]:
            type_name = n['type'].capitalize()
            title = n.get('title', n.get('display_number', ''))
            items.append({
                'node_id': n['id'],
                'quiz_type': 'proof_reconstruction',
                'prompt': f"Prove: {type_name} {title}",
                'prompt_content': n.get('katex_content', n.get('latex_content', '')),
                'answer': n.get('proof_katex', ''),
            })
        return jsonify(items)

    elif quiz_type == 'reverse_quiz':
        # Show conclusion -> name the theorem
        candidates = [
            n for n in pool
            if n['type'] in ('theorem', 'proposition', 'lemma')
            and n.get('title')
        ]
        random.shuffle(candidates)
        items = []
        for n in candidates[:count]:
            items.append({
                'node_id': n['id'],
                'quiz_type': 'reverse_quiz',
                'prompt': 'What theorem/result states the following?',
                'prompt_content': n.get('katex_content', n.get('latex_content', '')),
                'answer': f"{n['type'].capitalize()} {n.get('display_number', '')}: {n.get('title', '')}",
            })
        return jsonify(items)

    elif quiz_type == 'fill_blank':
        # Hide key parts of definitions/theorems
        candidates = [
            n for n in pool
            if n['type'] in ('definition', 'theorem', 'lemma')
        ]
        random.shuffle(candidates)
        items = []
        for n in candidates[:count]:
            content = n.get('katex_content', n.get('latex_content', ''))
            blanked = _make_blanks(content)
            type_name = n['type'].capitalize()
            title = n.get('title', n.get('display_number', ''))
            items.append({
                'node_id': n['id'],
                'quiz_type': 'fill_blank',
                'prompt': f"Fill in the blanks: {type_name} {title}",
                'prompt_content': blanked['blanked'],
                'answer': content,
                'blank_answers': blanked['answers'],
            })
        return jsonify(items)

    return jsonify({'error': f'Unknown quiz type: {quiz_type}'}), 400
