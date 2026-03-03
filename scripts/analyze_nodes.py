"""Analyze parsed nodes for content issues."""

import json
import re
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import PARSED_NODES_PATH

with open(PARSED_NODES_PATH, 'r', encoding='utf-8') as f:
    nodes = json.load(f)

print(f"Total nodes: {len(nodes)}\n")

issues = []
for n in nodes:
    content = n.get('latex_content', '')

    # Check for stray end tags of non-theorem environments
    for env in ['enumerate', 'itemize', 'tabular', 'center', 'figure']:
        tag = f"\\end{{{env}}}"
        if tag in content and f"\\begin{{{env}}}" not in content:
            issues.append(f"STRAY \\end{{{env}}} in {n['type']} {n.get('display_number','')} ({n['id']})")

    # Check for nested theorem-like envs (parser should not nest these)
    for env in ['definition', 'theorem', 'lemma', 'example', 'remark', 'proof', 'corollary', 'proposition']:
        tag = f"\\begin{{{env}}}"
        if tag in content:
            issues.append(f"NESTED \\begin{{{env}}} inside {n['type']} {n.get('display_number','')} ({n['id']})")

    if len(content.strip()) < 10 and n['type'] not in ('proof', 'proof-sketch'):
        issues.append(f"SHORT: {n['type']} {n.get('display_number','')} ({n['id']}): [{content.strip()[:50]}]")

    if len(content) > 3000:
        issues.append(f"LONG ({len(content)} chars): {n['type']} {n.get('display_number','')} ({n['id']})")

# Check for proofs not linked to theorems
unlinked_proofs = [n for n in nodes if n['type'] in ('proof', 'proof-sketch') and not n.get('proves')]
if unlinked_proofs:
    for p in unlinked_proofs:
        issues.append(f"UNLINKED PROOF: {p['id']} in {p.get('file_source','')}")

print("=== ISSUES ===")
for i in issues:
    print(f"  {i}")
print(f"\nTotal issues: {len(issues)}")

# Also print node summary per file
print("\n=== NODES BY FILE ===")
from collections import Counter
by_file = Counter()
for n in nodes:
    by_file[n.get('file_source', '?')] += 1
for f, c in sorted(by_file.items()):
    print(f"  {f}: {c} nodes")

# Print first few nodes with their content length
print("\n=== SAMPLE NODES (first 5) ===")
for n in nodes[:5]:
    print(f"  {n['type']} {n.get('display_number','')} ({n['id']}): {len(n['latex_content'])} chars, title={n.get('title')}")
    print(f"    content preview: {n['latex_content'][:100]}...")
