#!/usr/bin/env python3
"""Regenerate the combined root openapi.yaml from source files.

Reads:
  - info.yaml          → metadata (info, tags, x-tagGroups)
  - model/openapi.yaml → DTO schemas
  - api/openapi.yaml   → App paths
  - intools/openapi.yaml → Intools paths
  - landing/openapi.yaml → Landing paths
  - webhook/openapi.yaml → Webhook paths
  - internal/openapi.yaml → Internal paths

Writes:
  - openapi.yaml (root) → self-contained combined spec

Usage: python3 regen.py
"""

import os, re, yaml

BASE = os.path.dirname(os.path.abspath(__file__))
INFO = os.path.join(BASE, 'info.yaml')
MODEL = os.path.join(BASE, 'model', 'openapi.yaml')
ROOT = os.path.join(BASE, 'openapi.yaml')
PLATFORMS = ['api', 'intools', 'landing', 'webhook', 'internal']

# ---- Read info.yaml (metadata) ----
with open(INFO) as f:
    info_content = f.read()

# Extract info section
info_lines = []
in_info = False
for line in info_content.splitlines(True):
    if line.rstrip() == 'info:':
        in_info = True
        continue
    if in_info:
        if line.startswith('  ') or line.strip() == '':
            info_lines.append(line)
        else:
            break

# Extract x-tagGroups
xtg_lines = []
in_xtg = False
for line in info_content.splitlines(True):
    if line.rstrip() == 'x-tagGroups:':
        in_xtg = True
        continue
    if in_xtg:
        if not line.startswith('  ') and line.strip():
            break
        xtg_lines.append(line)

# ---- Collect enriched tags from platform files ----
all_tags = {}
for p in PLATFORMS:
    fp = os.path.join(BASE, p, 'openapi.yaml')
    if not os.path.exists(fp):
        continue
    try:
        with open(fp) as f:
            spec = yaml.safe_load(f.read())
        for tag in spec.get('tags', []):
            all_tags[tag['name']] = tag
    except Exception:
        pass

# ---- Read model schemas ----
with open(MODEL) as f:
    model_content = f.read()

# ---- Build root spec ----
output = []
output.append('openapi: 3.1.0\n')
output.append('info:\n')
output.extend(info_lines)
output.append('servers:\n  - url: /\n    description: Base URL\n')

# Tags (enriched from platform files)
output.append('tags:\n')
for tag_name in sorted(all_tags.keys()):
    tag = all_tags[tag_name]
    output.append(f'  - name: {tag["name"]}\n')
    if tag.get('x-displayName'):
        output.append(f'    x-displayName: {tag["x-displayName"]}\n')
    if tag.get('description'):
        output.append(f'    description: {tag["description"]}\n')

# x-tagGroups from info.yaml
output.append('x-tagGroups:\n')
output.extend(xtg_lines)

# Paths from platform files
output.append('paths:\n')
for p in PLATFORMS:
    fp = os.path.join(BASE, p, 'openapi.yaml')
    if not os.path.exists(fp):
        continue
    with open(fp) as f:
        content = f.read()
    m = re.search(r'^paths:\n(.*?)(?=\n\w|\Z)', content, re.DOTALL | re.MULTILINE)
    if m:
        pb = m.group(1).rstrip()
        pb = pb.replace(
            "'../model/openapi.yaml#/components/schemas/",
            "'#/components/schemas/"
        )
        output.append(pb + '\n')

# Schemas from model
output.append('components:\n')
m = re.search(r'^  schemas:\n(.*?)(?=\Z)', model_content, re.DOTALL | re.MULTILINE)
if m:
    output.append(m.group(0).rstrip() + '\n')

# ---- Write root ----
combined = ''.join(output).replace('\n\n\n', '\n\n')

with open(ROOT, 'w') as f:
    f.write(combined)

print(f'Root regenerated: {len(combined.splitlines())} lines')
print(f'  Metadata from: info.yaml')
print(f'  Schemas from:  model/openapi.yaml')
print(f'  Paths from:    {", ".join(PLATFORMS)}/openapi.yaml')
