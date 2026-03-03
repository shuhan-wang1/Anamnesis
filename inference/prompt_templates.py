"""Prompt templates for LLM dependency inference."""

SYSTEM_PROMPT = """You are a mathematics teaching assistant analyzing dependency relationships between mathematical concepts in lecture notes.

Given a theorem/lemma/proposition and a list of available definitions and results, identify which ones are DIRECTLY used or required to understand the given statement and its proof.

Rules:
- Only list DIRECT dependencies, not transitive ones
- A definition is a dependency if the theorem's statement or proof uses that concept
- A lemma/theorem is a dependency if it is invoked in the proof
- Notation dependencies count (e.g., if a theorem uses a notation defined elsewhere)
- Only reference items from the candidate list
- Return ONLY a valid JSON array of IDs. If no dependencies, return []
- Do not include any explanation, just the JSON array"""


def build_inference_prompt(target_node: dict, candidate_nodes: list[dict]) -> str:
    """Build a prompt for dependency inference.

    candidate_nodes: definitions/lemmas/theorems that appear before this node.
    """
    candidates_text = ""
    for c in candidate_nodes:
        type_label = c['type'].capitalize()
        number = c.get('display_number', '?')
        title = f" ({c['title']})" if c.get('title') else ""
        # Truncate content for context efficiency
        preview = c['latex_content'][:300].replace('\n', ' ')
        candidates_text += f'- ["{c["id"]}"] {type_label} {number}{title}: {preview}\n'

    target_type = target_node['type'].capitalize()
    target_number = target_node.get('display_number', '?')
    target_title = f" ({target_node['title']})" if target_node.get('title') else ""

    return f"""Analyze this {target_type} {target_number}{target_title}:

--- CONTENT ---
{target_node['latex_content']}
--- END CONTENT ---

Available prior definitions and results:
{candidates_text}

Which of the above items are direct dependencies of this {target_type}?
Return ONLY a JSON array of their IDs."""


# --- Auto-naming prompts ---

NAMING_SYSTEM_PROMPT = """You are a mathematics teaching assistant. Given a mathematical statement (theorem, definition, lemma, etc.), generate a short descriptive name (2-5 words) that captures its key concept.

Rules:
- Return ONLY the name, nothing else
- Use standard mathematical terminology
- Keep it concise: 2-5 words
- For well-known results, use their standard names (e.g., "Hoeffding's Inequality", "Representer Theorem")
- For definitions, name the concept being defined (e.g., "VC Dimension", "Kernel Function")
- For examples, describe what is being demonstrated (e.g., "Linear Kernel Example", "Bias-Variance Tradeoff")
- Do NOT include the type prefix (don't say "Theorem about X", just say "X")"""


def build_naming_prompt(node: dict) -> str:
    """Build a prompt for naming an unnamed node."""
    type_name = node['type'].capitalize()
    number = node.get('display_number', '?')
    section = ' > '.join(node.get('section_path', []))
    content = node.get('latex_content', '')[:600]

    return f"""Name this {type_name} {number}:

Section context: {section}

Content:
{content}

Respond with ONLY the name (2-5 words):"""
