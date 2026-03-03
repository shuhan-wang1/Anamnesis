"""Convert LaTeX content to HTML with KaTeX-renderable math blocks.

The key insight: LaTeX content is a mix of text-mode commands (enumerate, itemize,
textbf, etc.) and math-mode blocks ($...$, $$...$$, equation, align).
KaTeX only handles math. So we convert text-mode LaTeX to HTML, and leave
math blocks for KaTeX to render client-side.
"""

import re


def convert_for_katex(latex_content: str, label_map: dict | None = None) -> str:
    """Convert LaTeX content to HTML with embedded math for KaTeX rendering.

    Args:
        latex_content: Raw LaTeX content.
        label_map: Optional mapping of label -> display string for resolving \\ref{}.
    """
    content = latex_content

    # Remove \label{} commands
    content = re.sub(r'\\label\{[^}]*\}', '', content)

    # Resolve \ref{} and \eqref{} to display text
    def _ref_fallback(key):
        """For unresolved labels, produce a clean fallback."""
        if key.startswith('eq:'):
            return '(*)'  # generic equation reference
        return key

    if label_map:
        def _ref_replacer(m):
            return label_map.get(m.group(1), _ref_fallback(m.group(1)))
        content = re.sub(r'\\ref\{([^}]*)\}', _ref_replacer, content)
        content = re.sub(r'\\eqref\{([^}]*)\}',
                         lambda m: f'({label_map.get(m.group(1), _ref_fallback(m.group(1)))})', content)
    else:
        content = re.sub(r'\\ref\{([^}]*)\}',
                         lambda m: _ref_fallback(m.group(1)), content)
        content = re.sub(r'\\eqref\{([^}]*)\}',
                         lambda m: f'({_ref_fallback(m.group(1))})', content)

    # --- Convert math environments FIRST (before text processing) ---

    # \begin{equation}...\end{equation} -> $$ ... $$
    content = re.sub(
        r'\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}',
        r'$$\1$$',
        content, flags=re.DOTALL,
    )

    # \begin{align*}...\end{align*} -> $$ \begin{aligned}...\end{aligned} $$
    content = re.sub(
        r'\\begin\{align\*?\}(.*?)\\end\{align\*?\}',
        r'$$\\begin{aligned}\1\\end{aligned}$$',
        content, flags=re.DOTALL,
    )

    # \[ ... \] -> $$ ... $$
    content = re.sub(
        r'\\\[(.*?)\\\]',
        r'$$\1$$',
        content, flags=re.DOTALL,
    )

    # --- Protect math blocks from text-mode processing ---
    content, math_blocks = _protect_math(content)

    # --- Convert text-mode environments to HTML ---

    # \begin{enumerate} ... \end{enumerate} -> <ol>...</ol>
    content = _convert_list_env(content, 'enumerate', 'ol')
    content = _convert_list_env(content, 'itemize', 'ul')

    # \begin{cases} stays as math (KaTeX handles it)
    # \begin{tabular} -> HTML table
    content = _convert_tabular(content)

    # --- Convert text-mode commands to HTML (with proper brace matching) ---

    content = _replace_text_command(content, 'textbf', 'strong')
    content = _replace_text_command(content, 'textit', 'em')
    content = _replace_text_command(content, 'emph', 'em')
    content = _replace_text_command(content, 'underline', 'u')
    content = _replace_text_command(content, 'texttt', 'code')
    content = _replace_text_command(content, 'paragraph', 'strong')

    # \noindent -> nothing
    content = content.replace('\\noindent', '')

    # \bigskip, \medskip, \smallskip -> <br>
    content = re.sub(r'\\(bigskip|medskip|smallskip)', '<br>', content)

    # --- Convert algorithm environments ---
    content = _convert_algorithms(content)

    # --- Clean up unknown environments BEFORE restoring math ---
    # (so we don't accidentally strip \begin{aligned} etc. inside $$...$$)
    content = re.sub(r'\\begin\{[^}]*\}\s*', '', content)
    content = re.sub(r'\\end\{[^}]*\}\s*', '', content)

    # --- Restore math blocks ---
    content = _restore_math(content, math_blocks)

    # --- Clean up ---

    # Convert double newlines to paragraph breaks
    content = re.sub(r'\n\s*\n', '\n<br>\n', content)

    # Clean up excessive whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)

    # Remove stray \hline
    content = content.replace('\\hline', '')

    return content.strip()


# --- Math block protection ---

def _protect_math(content: str) -> tuple[str, list[str]]:
    """Replace math blocks with placeholders to protect from text-mode processing."""
    blocks = []

    def _save_block(m):
        blocks.append(m.group(0))
        return f'\x00MATH{len(blocks) - 1}\x00'

    # Display math first ($$...$$), then inline ($...$)
    content = re.sub(r'\$\$.*?\$\$', _save_block, content, flags=re.DOTALL)
    content = re.sub(r'\$(?!\$)([^$]+)\$', _save_block, content)
    return content, blocks


def _restore_math(content: str, blocks: list[str]) -> str:
    """Restore math blocks from placeholders."""
    for i, block in enumerate(blocks):
        content = content.replace(f'\x00MATH{i}\x00', block)
    return content


# --- Brace matching ---

def _match_braces(text: str, start: int) -> int:
    """Find the matching closing brace for the opening brace at position `start`.

    Returns the index of the closing brace, or -1 if not found.
    """
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return i
    return -1


def _replace_text_command(content: str, latex_cmd: str, html_tag: str) -> str:
    r"""Replace \latex_cmd{...} with <html_tag>...</html_tag>, handling nested braces."""
    search = '\\' + latex_cmd + '{'
    while True:
        idx = content.find(search)
        if idx == -1:
            break
        brace_start = idx + len(search) - 1  # position of '{'
        brace_end = _match_braces(content, brace_start)
        if brace_end == -1:
            break  # malformed, skip
        inner = content[brace_start + 1:brace_end]
        replacement = f'<{html_tag}>{inner}</{html_tag}>'
        content = content[:idx] + replacement + content[brace_end + 1:]
    return content


# --- Environment converters ---

def _convert_list_env(content: str, env_name: str, html_tag: str) -> str:
    r"""Convert \begin{enumerate/itemize}...\end{...} to <ol>/<ul> with <li>."""
    pattern = re.compile(
        rf'\\begin\{{{env_name}\}}(?:\[[^\]]*\])?(.*?)\\end\{{{env_name}\}}',
        re.DOTALL,
    )

    def replacer(match):
        body = match.group(1)
        # Split on \item
        items = re.split(r'\\item\s*', body)
        items = [i.strip() for i in items if i.strip()]
        html = f'<{html_tag}>\n'
        for item in items:
            html += f'  <li>{item}</li>\n'
        html += f'</{html_tag}>'
        return html

    return pattern.sub(replacer, content)


def _convert_tabular(content: str) -> str:
    r"""Convert \begin{tabular}...\end{tabular} to HTML table."""
    pattern = re.compile(
        r'\\begin\{tabular\}\{[^}]*\}(.*?)\\end\{tabular\}',
        re.DOTALL,
    )

    def replacer(match):
        body = match.group(1).strip()
        rows = body.split('\\\\')
        html = '<table class="math-table">\n'
        for row in rows:
            row = row.strip()
            if not row or row == '\\hline':
                continue
            row = row.replace('\\hline', '')
            cells = row.split('&')
            html += '  <tr>'
            for cell in cells:
                html += f'<td>{cell.strip()}</td>'
            html += '</tr>\n'
        html += '</table>'
        return html

    return pattern.sub(replacer, content)


def _convert_algorithms(content: str) -> str:
    """Convert algorithmic environments to readable pseudocode HTML."""
    if '\\begin{algorithmic}' not in content:
        return content

    def algo_replacer(match):
        algo_body = match.group(1)
        lines = []
        indent = 0

        for raw_line in algo_body.split('\n'):
            line = raw_line.strip()
            if not line:
                continue

            if re.match(r'\\END(FOR|IF|WHILE)', line, re.IGNORECASE):
                indent = max(0, indent - 1)
                continue

            prefix = '&nbsp;&nbsp;&nbsp;&nbsp;' * indent

            if line.startswith('\\STATE') or line.startswith('\\State'):
                text = re.sub(r'\\STATE\s*|\\State\s*', '', line, count=1)
                lines.append(f"{prefix}{text}")
            elif line.startswith('\\IF') or line.startswith('\\If'):
                cond = re.search(r'\{(.+?)\}', line)
                lines.append(f"{prefix}<strong>if</strong> {cond.group(1) if cond else ''}:")
                indent += 1
            elif line.startswith('\\ELSIF') or line.startswith('\\ElsIf'):
                indent = max(0, indent - 1)
                cond = re.search(r'\{(.+?)\}', line)
                prefix = '&nbsp;&nbsp;&nbsp;&nbsp;' * indent
                lines.append(f"{prefix}<strong>elif</strong> {cond.group(1) if cond else ''}:")
                indent += 1
            elif line.startswith('\\ELSE') or line.startswith('\\Else'):
                indent = max(0, indent - 1)
                prefix = '&nbsp;&nbsp;&nbsp;&nbsp;' * indent
                lines.append(f"{prefix}<strong>else</strong>:")
                indent += 1
            elif line.startswith('\\FOR') or line.startswith('\\For'):
                cond = re.search(r'\{(.+?)\}', line)
                lines.append(f"{prefix}<strong>for</strong> {cond.group(1) if cond else ''}:")
                indent += 1
            elif line.startswith('\\WHILE') or line.startswith('\\While'):
                cond = re.search(r'\{(.+?)\}', line)
                lines.append(f"{prefix}<strong>while</strong> {cond.group(1) if cond else ''}:")
                indent += 1
            elif line.startswith('\\RETURN') or line.startswith('\\Return'):
                text = re.sub(r'\\RETURN\s*|\\Return\s*', '', line, count=1)
                lines.append(f"{prefix}<strong>return</strong> {text}")
            elif line.startswith('\\REQUIRE') or line.startswith('\\Require'):
                text = re.sub(r'\\REQUIRE\s*|\\Require\s*', '', line, count=1)
                lines.append(f"<strong>Input:</strong> {text}")
            elif line.startswith('\\ENSURE') or line.startswith('\\Ensure'):
                text = re.sub(r'\\ENSURE\s*|\\Ensure\s*', '', line, count=1)
                lines.append(f"<strong>Output:</strong> {text}")
            else:
                lines.append(f"{prefix}{line}")

        return '<div class="algorithm-block">' + '<br>\n'.join(lines) + '</div>'

    content = re.sub(
        r'\\begin\{algorithmic\}(.*?)\\end\{algorithmic\}',
        algo_replacer,
        content, flags=re.DOTALL,
    )

    # Remove leftover algorithm wrappers and captions
    content = re.sub(r'\\begin\{algorithm\}\s*', '', content)
    content = re.sub(r'\\end\{algorithm\}\s*', '', content)
    content = re.sub(r'\\caption\{([^}]*)\}', r'<div class="text-muted text-sm"><strong>Algorithm:</strong> \1</div>', content)

    return content
