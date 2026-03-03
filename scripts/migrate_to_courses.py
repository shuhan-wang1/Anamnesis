"""One-time migration: move existing single-course data into courses/ structure."""

import json
import os
import shutil
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import DATA_DIR, INPUT_DIR


def migrate():
    courses_dir = os.path.join(DATA_DIR, 'courses')
    courses_file = os.path.join(DATA_DIR, 'courses.json')
    default_dir = os.path.join(courses_dir, 'default')
    default_input = os.path.join(default_dir, 'input')

    # Check if already migrated
    if os.path.exists(courses_file):
        print("Migration already complete (courses.json exists).")
        return

    print("Migrating existing data to course structure...")

    # Create directories
    os.makedirs(default_input, exist_ok=True)

    # Copy data files
    data_files = [
        'knowledge_graph.json',
        'parsed_nodes.json',
        'explicit_edges.json',
        'inferred_edges.json',
        'macro_registry.json',
        'name_cache.json',
        'user_progress.json',
        'session.json',
    ]

    copied = 0
    for fname in data_files:
        src = os.path.join(DATA_DIR, fname)
        dst = os.path.join(default_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            copied += 1
            print(f"  Copied {fname}")

    # Copy input .tex files
    tex_files = []
    if os.path.exists(INPUT_DIR):
        for fname in os.listdir(INPUT_DIR):
            if fname.endswith('.tex'):
                src = os.path.join(INPUT_DIR, fname)
                dst = os.path.join(default_input, fname)
                shutil.copy2(src, dst)
                tex_files.append(fname)
                print(f"  Copied input/{fname}")

    # Count nodes from knowledge graph
    node_count = 0
    kg_path = os.path.join(default_dir, 'knowledge_graph.json')
    if os.path.exists(kg_path):
        with open(kg_path, 'r', encoding='utf-8') as f:
            graph = json.load(f)
            node_count = graph.get('metadata', {}).get('total_nodes', 0)

    # Create courses.json
    courses = [{
        'id': 'default',
        'name': 'COMP0078 Supervised Learning',
        'created_at': datetime.now().isoformat(),
        'file_count': len(tex_files),
        'node_count': node_count,
        'files': tex_files,
    }]

    with open(courses_file, 'w', encoding='utf-8') as f:
        json.dump(courses, f, indent=2, ensure_ascii=False)

    print(f"\nMigration complete!")
    print(f"  Copied {copied} data files + {len(tex_files)} .tex files")
    print(f"  Created course 'COMP0078 Supervised Learning' with {node_count} nodes")


if __name__ == '__main__':
    migrate()
