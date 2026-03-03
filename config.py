import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input")
DATA_DIR = os.path.join(BASE_DIR, "data")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Legacy paths (used by CLI scripts when run directly)
KNOWLEDGE_GRAPH_PATH = os.path.join(DATA_DIR, "knowledge_graph.json")
USER_PROGRESS_PATH = os.path.join(DATA_DIR, "user_progress.json")
MACRO_REGISTRY_PATH = os.path.join(DATA_DIR, "macro_registry.json")
PARSED_NODES_PATH = os.path.join(DATA_DIR, "parsed_nodes.json")
EXPLICIT_EDGES_PATH = os.path.join(DATA_DIR, "explicit_edges.json")
INFERRED_EDGES_PATH = os.path.join(DATA_DIR, "inferred_edges.json")
NAME_CACHE_PATH = os.path.join(DATA_DIR, "name_cache.json")

# Claude API model for dependency inference
INFERENCE_MODEL = "claude-sonnet-4-20250514"

# File ordering for the original course (used by CLI scripts)
FILE_ORDER = [
    "slide_1_note (2).tex",
    "slide_1_note (3).tex",
    "slide_2_note (1).tex",
    "slide_2_note_continue (1).tex",
    "slide_3_note (1).tex",
    "slide_4_note (1).tex",
    "slide_5 (2).tex",
    "slide_6_note (1).tex",
    "slide_7 (1).tex",
]
