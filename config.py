import os
import sys

# --- Determine runtime mode ---
IS_DESKTOP = os.environ.get('ANAMNESIS_DESKTOP') == '1'
IS_FROZEN = getattr(sys, 'frozen', False)

if IS_FROZEN:
    # PyInstaller bundle: bundled files are in sys._MEIPASS
    BUNDLE_DIR = sys._MEIPASS
elif os.environ.get('ANAMNESIS_BUNDLE_DIR'):
    BUNDLE_DIR = os.environ['ANAMNESIS_BUNDLE_DIR']
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))

# Frontend is always relative to the bundle (read-only in frozen mode)
FRONTEND_DIR = os.path.join(BUNDLE_DIR, "frontend")

# Data directory: platform-appropriate user location for desktop, local for dev
if IS_DESKTOP or IS_FROZEN:
    import platformdirs
    DATA_DIR = os.path.join(
        platformdirs.user_data_dir("Anamnesis", appauthor=False),
        "data",
    )
else:
    DATA_DIR = os.path.join(BUNDLE_DIR, "data")

INPUT_DIR = os.path.join(BUNDLE_DIR, "input")

# Ensure data dir exists
os.makedirs(DATA_DIR, exist_ok=True)

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
