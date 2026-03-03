"""Core LaTeX parser: extracts theorem-like environment blocks from .tex files."""

import os
import re
from parser.section_tracker import SectionTracker, SECTION_PATTERN, NUMBERED_ENVS, UNNUMBERED_ENVS, SEPARATE_COUNTER_ENVS

# All environments we want to extract
ALL_ENV_NAMES = sorted(
    NUMBERED_ENVS | UNNUMBERED_ENVS | SEPARATE_COUNTER_ENVS | {'algorithm'}
)

LABEL_PATTERN = re.compile(r'\\label\{([^}]+)\}')


def _find_env_blocks(body: str, env_name: str) -> list[dict]:
    """Find all \\begin{env}[title]...\\end{env} blocks, handling nesting."""
    results = []
    # Pattern to find \begin{env_name}
    begin_tag = f"\\begin{{{env_name}}}"
    end_tag = f"\\end{{{env_name}}}"

    search_start = 0
    while True:
        begin_idx = body.find(begin_tag, search_start)
        if begin_idx == -1:
            break

        # Find the content start (after the begin tag)
        content_start = begin_idx + len(begin_tag)

        # Check for optional [title]
        title = None
        if content_start < len(body) and body[content_start] == '[':
            bracket_end = body.find(']', content_start)
            if bracket_end != -1:
                title = body[content_start + 1:bracket_end].strip()
                content_start = bracket_end + 1

        # Find matching \end{env_name}, handling nesting
        depth = 1
        pos = content_start
        while depth > 0 and pos < len(body):
            next_begin = body.find(begin_tag, pos)
            next_end = body.find(end_tag, pos)

            if next_end == -1:
                break  # unmatched, take rest
            if next_begin != -1 and next_begin < next_end:
                depth += 1
                pos = next_begin + len(begin_tag)
            else:
                depth -= 1
                if depth == 0:
                    content = body[content_start:next_end].strip()
                    results.append({
                        'env_name': env_name,
                        'title': title,
                        'content': content,
                        'start_offset': begin_idx,
                        'end_offset': next_end + len(end_tag),
                    })
                pos = next_end + len(end_tag)

        search_start = pos if depth == 0 else begin_idx + 1

    return results


def _find_algorithm_blocks(body: str) -> list[dict]:
    """Find \\begin{algorithm}...\\end{algorithm} including caption."""
    results = []
    pattern = re.compile(
        r'\\begin\{algorithm\}(.*?)\\end\{algorithm\}',
        re.DOTALL,
    )
    for m in pattern.finditer(body):
        content = m.group(1).strip()
        # Extract caption if present
        cap_match = re.search(r'\\caption\{([^}]+)\}', content)
        title = cap_match.group(1) if cap_match else None
        results.append({
            'env_name': 'algorithm',
            'title': title,
            'content': content,
            'start_offset': m.start(),
            'end_offset': m.end(),
        })
    return results


def parse_file(filepath: str, file_index: int, tracker: SectionTracker) -> list[dict]:
    """Parse a single .tex file and extract all theorem-like environment blocks.

    Returns list of node dicts.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        full_text = f.read()

    # Get body (after \begin{document})
    doc_start = full_text.find('\\begin{document}')
    if doc_start == -1:
        body = full_text
    else:
        body = full_text[doc_start:]

    filename = os.path.basename(filepath)

    # Collect all events: sections and environments
    events = []

    # Section events
    for m in SECTION_PATTERN.finditer(body):
        events.append({
            'type': 'section',
            'level': m.group(1),
            'title': m.group(2),
            'offset': m.start(),
        })

    # Environment events
    for env_name in ALL_ENV_NAMES:
        if env_name == 'algorithm':
            blocks = _find_algorithm_blocks(body)
        else:
            blocks = _find_env_blocks(body, env_name)
        for block in blocks:
            events.append({
                'type': 'environment',
                'offset': block['start_offset'],
                **block,
            })

    # Sort by offset
    events.sort(key=lambda e: e['offset'])

    # Process in document order
    nodes = []
    for event in events:
        if event['type'] == 'section':
            tracker.update_section(event['level'], event['title'])
            continue

        env_name = event['env_name']
        content = event['content']
        title = event.get('title')

        # Get display number
        display_number = tracker.next_number(env_name)

        # Extract label
        label_match = LABEL_PATTERN.search(content)
        label = label_match.group(1) if label_match else None

        # Build node ID
        if label:
            node_id = label
        else:
            sec = tracker.section_num
            node_id = f"f{file_index}_{env_name}_{sec}_{tracker.theorem_counter}"

        node = {
            'id': node_id,
            'type': env_name,
            'title': title,
            'display_number': display_number,
            'label': label,
            'latex_content': content,
            'section_path': tracker.get_section_path(),
            'file_source': filename,
            'file_index': file_index,
            '_offset': event['offset'],  # internal, for proof linking
        }
        nodes.append(node)

    # Link proofs to preceding theorem-like nodes
    for i, node in enumerate(nodes):
        if node['type'] in ('proof', 'proof-sketch'):
            for j in range(i - 1, -1, -1):
                if nodes[j]['type'] in ('theorem', 'lemma', 'proposition', 'corollary'):
                    node['proves'] = nodes[j]['id']
                    break

    # Also detect "Proof of Theorem \ref{...}:" patterns in body text
    # These are standalone proof paragraphs not in \begin{proof}...\end{proof}
    proof_of_pattern = re.compile(
        r'\\textbf\{Proof of (?:Theorem|Lemma|Proposition)\s*\\ref\{([^}]+)\}',
    )
    for m in proof_of_pattern.finditer(body):
        target_label = m.group(1)
        # Find the node closest after this text and mark it
        for node in nodes:
            if node['type'] in ('proof', 'proof-sketch') and node['_offset'] > m.start():
                if 'proves' not in node or not node['proves']:
                    node['proves'] = target_label
                break

    # Clean internal fields
    for node in nodes:
        del node['_offset']

    return nodes


def parse_all_files(filepaths: list[str]) -> list[dict]:
    """Parse multiple .tex files in order. Returns all nodes."""
    tracker = SectionTracker()
    all_nodes = []
    for i, fp in enumerate(filepaths):
        nodes = parse_file(fp, i, tracker)
        all_nodes.extend(nodes)
        # Reset tracker for next file (each file is independent)
        tracker = SectionTracker()
    return all_nodes
