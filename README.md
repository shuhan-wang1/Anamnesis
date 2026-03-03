# Anamnesis

**Anamnesis** (Greek: *ἀνάμνησις*, "recollection") — a spaced-repetition study tool that parses LaTeX lecture notes into an interactive knowledge graph with adaptive review scheduling.

Built for exam revision of theorem-heavy university courses. Upload your `.tex` notes, and Anamnesis extracts every definition, theorem, lemma, proof, and example into a browsable, quizzable, reviewable knowledge base.

## Features

- **LaTeX Parsing** — Extracts theorem-like environments (`\begin{theorem}`, `\begin{definition}`, etc.) from `.tex` files, resolves `\ref`/`\eqref` cross-references, and renders math via KaTeX
- **Knowledge Graph** — Automatically infers concept dependencies (which theorems depend on which definitions) and visualizes them as an interactive D3.js force graph
- **Spaced Repetition** — FSRS-inspired scheduling tracks per-concept difficulty and stability, prioritizing review of items closest to being forgotten
- **Diagnostic Assessment** — Quick self-rating of the most important concepts to identify knowledge gaps
- **Guided Learning Paths** — Topologically-sorted study plans: learn prerequisites before target theorems
- **Six Quiz Modes** — Definition recall, theorem statement, proof reconstruction, reverse identification, fill-in-the-blank, and smart review
- **Multi-Course Support** — Create, switch between, and manage multiple courses with isolated progress tracking
- **Full State Persistence** — All UI state (current page, quiz progress, expanded sections) survives page reloads

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
git clone https://github.com/shuhan-wang1/Anamnesis.git
cd Anamnesis
pip install -r requirements.txt
```

### First Run

1. **Prepare your notes**: Place your `.tex` files in the `input/` directory (create it if needed).

2. **Parse the notes**:
   ```bash
   python scripts/parse_all.py
   python scripts/build_graph.py
   ```

3. **Run the migration** (creates the course structure):
   ```bash
   python scripts/migrate_to_courses.py
   ```

4. **Start the server**:
   ```bash
   python server/app.py
   ```

5. Open `http://localhost:5000` in your browser.

### Adding Courses via the UI

After the first run, you can add new courses directly through the browser:

1. Click **Courses** in the nav bar
2. Enter a course name and upload `.tex` files (drag & drop or file/folder picker)
3. Anamnesis will parse and build the knowledge graph automatically

## Architecture

```
Anamnesis/
├── config.py                 # Global configuration
├── requirements.txt
│
├── parser/                   # LaTeX → structured nodes
│   ├── latex_parser.py       # Environment extraction (\begin{theorem}...)
│   ├── katex_converter.py    # LaTeX → HTML+KaTeX conversion
│   ├── macro_expander.py     # \newcommand resolution
│   ├── ref_resolver.py       # \ref{} cross-reference resolution
│   └── section_tracker.py    # Section numbering (Theorem 2.5, etc.)
│
├── inference/                # Dependency analysis
│   ├── concept_analyzer.py   # Content-based edge detection
│   ├── dependency_inferrer.py # LLM-assisted inference (optional)
│   ├── graph_merger.py       # Edge deduplication & graph building
│   └── prompt_templates.py
│
├── scripts/                  # CLI pipeline
│   ├── parse_all.py          # .tex → parsed_nodes.json
│   ├── build_graph.py        # nodes → knowledge_graph.json
│   ├── infer_deps.py         # Claude API → inferred_edges.json
│   ├── migrate_to_courses.py # One-time data migration
│   └── name_nodes.py         # Auto-naming via Claude API
│
├── server/                   # Flask backend
│   ├── app.py                # Entry point + static serving
│   ├── state.py              # Course-aware global state
│   ├── course_manager.py     # Course CRUD + pipeline runner
│   └── routes/
│       ├── graph_api.py      # GET /api/graph, /api/node/:id
│       ├── progress_api.py   # Progress tracking + reset
│       ├── dashboard_api.py  # Readiness statistics
│       ├── learning_api.py   # Study plans + learning paths
│       ├── quiz_api.py       # Quiz generation (6 types)
│       ├── diagnostic_api.py # Diagnostic assessment
│       ├── spaced_repetition.py # SR engine + due items
│       └── course_api.py     # Course management endpoints
│
└── frontend/                 # Vanilla JS SPA
    ├── index.html
    ├── css/main.css          # GitHub dark theme
    └── js/
        ├── api.js            # API client + Session manager
        ├── app.js            # SPA router
        ├── katex_setup.js    # Math rendering config
        └── components/
            ├── dashboard.js  # Exam readiness overview
            ├── diagnostic.js # Quick knowledge assessment
            ├── learning.js   # Study plans + focus paths
            ├── quiz.js       # Six quiz modes
            ├── graph_viewer.js # D3 force-directed graph
            ├── browse.js     # All concepts browser
            ├── courses.js    # Course management
            └── node_card.js  # Reusable concept card
```

## Supported LaTeX Environments

Anamnesis recognizes these environments from your `.tex` files:

| Environment | Numbered | Notes |
|---|---|---|
| `theorem` | Yes | Proofs auto-folded into parent |
| `lemma` | Yes | |
| `proposition` | Yes | |
| `corollary` | Yes | |
| `definition` | Yes | |
| `example` | Yes | |
| `algorithm` | Yes | Pseudocode rendered |
| `exercise` | Yes | |
| `proof` | No | Linked to preceding theorem |
| `remark` | No | |
| `note` | No | |

## Tips for Best Results

For the parser to work well, your `.tex` notes should:

- Use standard `\begin{theorem}...\end{theorem}` environments
- Include `\label{thm:name}` for cross-referencing
- Use `\ref{thm:name}` when one theorem depends on another
- Give titles to important results: `\begin{theorem}[Perceptron Bound]`
- Use `\begin{proof}` immediately after the theorem it proves

See the **LaTeX Revision Prompt** section below for a Claude prompt that can clean up your notes for optimal parsing.

## LaTeX Revision Prompt

If your `.tex` notes have inconsistent formatting, missing cross-references, or unnamed theorems, you can use Claude to revise them before uploading. See [LATEX_REVISION_PROMPT.md](LATEX_REVISION_PROMPT.md) for a ready-to-use prompt.

## Tech Stack

- **Backend**: Python 3.11+, Flask
- **Frontend**: Vanilla JS, KaTeX (math rendering), D3.js (graph visualization)
- **Spaced Repetition**: FSRS-inspired algorithm (difficulty, stability, retrievability)
- **Optional**: Anthropic Claude API for dependency inference and auto-naming

## License

MIT
