"""Extract custom LaTeX macros from preambles for KaTeX registration."""

import re


def extract_macros_from_preamble(preamble: str) -> dict:
    """Extract \\newcommand and \\DeclareMathOperator definitions.

    Returns dict mapping macro name -> {"args": int, "expansion": str}
    """
    macros = {}

    # \newcommand{\name}[args]{expansion} or \newcommand{\name}{expansion}
    # Also handles \renewcommand
    newcmd_pattern = re.compile(
        r'\\(?:re)?newcommand\s*\{(\\[a-zA-Z]+)\}'
        r'(?:\[(\d+)\])?'
        r'\s*\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}',
    )
    for m in newcmd_pattern.finditer(preamble):
        name = m.group(1)
        args = int(m.group(2)) if m.group(2) else 0
        expansion = m.group(3).strip()
        macros[name] = {"args": args, "expansion": expansion}

    # \DeclareMathOperator*{\name}{display} or \DeclareMathOperator{\name}{display}
    mathop_pattern = re.compile(
        r'\\DeclareMathOperator(\*?)\s*\{(\\[a-zA-Z]+)\}\s*\{([^}]*)\}'
    )
    for m in mathop_pattern.finditer(preamble):
        star = m.group(1)
        name = m.group(2)
        display = m.group(3).strip()
        if star:
            macros[name] = {"args": 0, "expansion": f"\\operatorname*{{{display}}}"}
        else:
            macros[name] = {"args": 0, "expansion": f"\\operatorname{{{display}}}"}

    return macros


def extract_macros_from_file(filepath: str) -> dict:
    """Extract macros from the preamble of a .tex file."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Preamble is everything before \begin{document}
    idx = content.find("\\begin{document}")
    if idx == -1:
        return {}
    preamble = content[:idx]
    return extract_macros_from_preamble(preamble)


def merge_macros(macro_list: list[dict]) -> dict:
    """Merge macro dicts from multiple files. Later files override earlier ones."""
    merged = {}
    for macros in macro_list:
        merged.update(macros)
    return merged
