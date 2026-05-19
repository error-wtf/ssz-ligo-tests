#!/usr/bin/env python3
"""
LIGO_GW240925_GW250207_PHASE_2_SCIENCE_MAPPING

OBJECTIVE:
Map the release contents to scientifically meaningful groups without interpreting results.

RULES:
- No physics conclusions
- No SSZ/GR claims
- Only file/dataset structure inspection
- HDF5: list groups/datasets only, don't load huge arrays
- Notebooks: read metadata only, don't execute
"""

import os
import json
import csv
import h5py
from pathlib import Path
from datetime import datetime

ROOT = Path("E:/clone/ligo-gw240925-gw250207-release")
INVENTORY_DIR = ROOT / "02_INVENTORY"
LOGS_DIR = ROOT / "06_WINDSURF_LOGS"
EXTRACTED_DIR = ROOT / "01_EXTRACTED" / "18600070"
RAW_DIR = ROOT / "00_RAW_DOWNLOADS"

# Ensure dirs exist
for d in [INVENTORY_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Log file
log_path = LOGS_DIR / "PHASE_2_SCIENCE_MAPPING_LOG.md"
science_map_path = INVENTORY_DIR / "LIGO_RELEASE_SCIENCE_MAP.md"
hdf5_report_path = INVENTORY_DIR / "HDF5_STRUCTURE_REPORT.md"
notebook_report_path = INVENTORY_DIR / "NOTEBOOK_DEPENDENCY_REPORT.md"

def log(msg):
    print(msg)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now().isoformat()} - {msg}\n")

log("=== PHASE 2 SCIENCE MAPPING START ===")

# Phase 1 inventory (if exists)
phase1_csv = INVENTORY_DIR / "LIGO_RELEASE_INVENTORY.csv"
inventory = []
if phase1_csv.exists():
    log(f"Loading Phase 1 inventory from {phase1_csv}")
    with open(phase1_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        inventory = list(reader)
    log(f"Loaded {len(inventory)} items from Phase 1")
else:
    log("WARNING: Phase 1 inventory not found, starting fresh")

# Science mapping data structures
science_map = {
    'by_event': {'GW240925': [], 'GW250207': [], 'both': [], 'unknown': []},
    'by_calibration': {'C00': [], 'C01': [], 'envcal': [], 'cal': [], 'unknown': []},
    'by_product': {
        'strain': [],
        'calibration': [],
        'posterior_samples': [],
        'residuals': [],
        'skymaps': [],
        'ringdown_QNM': [],
        'TIGER': [],
        'FTI': [],
        'PCA': [],
        'PSEOBNR': [],
        'QNMRF': [],
        'notebooks': [],
        'unknown': []
    },
    'hdf5_files': [],
    'notebook_files': []
}

# Analyze HDF5 structure
def analyze_hdf5_structure(filepath):
    """Safely inspect HDF5 structure without loading full arrays"""
    try:
        with h5py.File(filepath, 'r') as f:
            structure = {
                'filename': filepath.name,
                'path': str(filepath),
                'groups': [],
                'datasets': [],
                'attributes': {}
            }
            
            def visit_item(name, obj):
                if isinstance(obj, h5py.Group):
                    structure['groups'].append(name)
                    # Get group attributes
                    attrs = dict(obj.attrs)
                    if attrs:
                        structure['attributes'][name] = {k: str(v) for k, v in attrs.items()}
                elif isinstance(obj, h5py.Dataset):
                    shape = obj.shape
                    dtype = str(obj.dtype)
                    size_mb = obj.size * obj.dtype.itemsize / (1024**2) if obj.size > 0 else 0
                    structure['datasets'].append({
                        'name': name,
                        'shape': str(shape),
                        'dtype': dtype,
                        'size_mb': round(size_mb, 2)
                    })
            
            f.visititems(visit_item)
            
            # Get root attributes
            root_attrs = dict(f.attrs)
            if root_attrs:
                structure['attributes']['/'] = {k: str(v) for k, v in root_attrs.items()}
            
            return structure
    except Exception as e:
        log(f"ERROR analyzing HDF5 {filepath}: {e}")
        return None

# Analyze notebook structure
def analyze_notebook(filepath):
    """Read notebook metadata without executing"""
    try:
        import nbformat
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        
        analysis = {
            'filename': filepath.name,
            'path': str(filepath),
            'kernelspec': nb.metadata.get('kernelspec', {}),
            'language_info': nb.metadata.get('language_info', {}),
            'total_cells': len(nb.cells),
            'code_cells': len([c for c in nb.cells if c.cell_type == 'code']),
            'markdown_cells': len([c for c in nb.cells if c.cell_type == 'markdown']),
            'imports': [],
            'referenced_files': [],
            'referenced_events': [],
            'referenced_calibration': [],
            'output_files': [],
            'figure_files': []
        }
        
        # Extract imports and references from code cells
        for cell in nb.cells:
            if cell.cell_type == 'code':
                source = cell.source
                # Look for imports
                if 'import' in source:
                    for line in source.split('\n'):
                        if 'import' in line or 'from ' in line:
                            analysis['imports'].append(line.strip())
                # Look for file references
                for ext in ['.hdf5', '.h5', '.txt', '.json', '.csv', '.tar', '.gz']:
                    if ext in source:
                        # Extract potential filenames
                        import re
                        matches = re.findall(rf'[\w\-\./]+{ext}', source)
                        analysis['referenced_files'].extend(matches)
                # Look for events
                for event in ['240925', '250207', 'GW240925', 'GW250207']:
                    if event in source:
                        analysis['referenced_events'].append(event)
                # Look for calibration tags
                for cal in ['C00', 'C01', 'envcal', 'envelope']:
                    if cal in source:
                        analysis['referenced_calibration'].append(cal)
                # Look for output/figure references
                for pattern in ['.png', '.pdf', '.jpg', 'savefig', 'to_csv', 'to_hdf']:
                    if pattern in source:
                        analysis['output_files'].append(pattern)
        
        # Deduplicate
        analysis['imports'] = list(set(analysis['imports']))[:20]  # Limit
        analysis['referenced_files'] = list(set(analysis['referenced_files']))
        analysis['referenced_events'] = list(set(analysis['referenced_events']))
        analysis['referenced_calibration'] = list(set(analysis['referenced_calibration']))
        
        return analysis
    except Exception as e:
        log(f"ERROR analyzing notebook {filepath}: {e}")
        return None

# Process all files from inventory
log("Processing inventory items for science mapping...")

hdf5_structures = []
notebook_analyses = []

for item in inventory:
    filename = item.get('filename', '')
    category = item.get('category', '')
    event = item.get('event', '')
    calibration = item.get('calibration', '')
    filepath = Path(ROOT) / item.get('path', '')
    
    # Categorize by event
    if event in science_map['by_event']:
        science_map['by_event'][event].append(item)
    else:
        science_map['by_event']['unknown'].append(item)
    
    # Categorize by calibration
    if calibration in science_map['by_calibration']:
        science_map['by_calibration'][calibration].append(item)
    else:
        science_map['by_calibration']['unknown'].append(item)
    
    # Categorize by product
    if category in science_map['by_product']:
        science_map['by_product'][category].append(item)
    else:
        science_map['by_product']['unknown'].append(item)
    
    # Analyze HDF5 files
    if category == 'posterior_samples' or item.get('extension') == '.hdf5':
        if filepath.exists():
            log(f"Analyzing HDF5: {filename}")
            structure = analyze_hdf5_structure(filepath)
            if structure:
                hdf5_structures.append(structure)
                science_map['hdf5_files'].append(structure)
    
    # Analyze notebooks
    if category == 'notebook' or item.get('extension') == '.ipynb':
        if filepath.exists():
            log(f"Analyzing notebook: {filename}")
            analysis = analyze_notebook(filepath)
            if analysis:
                notebook_analyses.append(analysis)
                science_map['notebook_files'].append(analysis)

log(f"Analyzed {len(hdf5_structures)} HDF5 files")
log(f"Analyzed {len(notebook_analyses)} notebooks")

# Write HDF5 Structure Report
log(f"Writing HDF5 report: {hdf5_report_path}")
with open(hdf5_report_path, 'w', encoding='utf-8') as f:
    f.write("# HDF5 Structure Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    f.write("## Summary\n\n")
    f.write(f"Total HDF5 files inspected: {len(hdf5_structures)}\n\n")
    
    for struct in hdf5_structures:
        f.write(f"### {struct['filename']}\n\n")
        f.write(f"**Path:** `{struct['path']}`\n\n")
        f.write(f"**Groups:** {len(struct['groups'])}\n")
        for g in struct['groups'][:10]:  # Limit
            f.write(f"- `{g}`\n")
        if len(struct['groups']) > 10:
            f.write(f"- ... and {len(struct['groups']) - 10} more\n")
        
        f.write(f"\n**Datasets:** {len(struct['datasets'])}\n")
        for d in struct['datasets'][:5]:  # Limit
            f.write(f"- `{d['name']}`: shape={d['shape']}, dtype={d['dtype']}, size={d['size_mb']} MB\n")
        if len(struct['datasets']) > 5:
            f.write(f"- ... and {len(struct['datasets']) - 5} more\n")
        
        if struct['attributes']:
            f.write(f"\n**Attributes:**\n")
            for group, attrs in list(struct['attributes'].items())[:3]:
                f.write(f"- `{group}`: {list(attrs.keys())}\n")
        
        f.write("\n---\n\n")

# Write Notebook Dependency Report
log(f"Writing notebook report: {notebook_report_path}")
with open(notebook_report_path, 'w', encoding='utf-8') as f:
    f.write("# Notebook Dependency Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    f.write("## Summary\n\n")
    f.write(f"Total notebooks analyzed: {len(notebook_analyses)}\n\n")
    
    for nb in notebook_analyses:
        f.write(f"### {nb['filename']}\n\n")
        f.write(f"**Path:** `{nb['path']}`\n\n")
        f.write(f"**Cells:** {nb['total_cells']} total ({nb['code_cells']} code, {nb['markdown_cells']} markdown)\n\n")
        
        if nb['referenced_events']:
            f.write(f"**Events referenced:** {', '.join(nb['referenced_events'])}\n\n")
        
        if nb['referenced_calibration']:
            f.write(f"**Calibration tags:** {', '.join(nb['referenced_calibration'])}\n\n")
        
        if nb['referenced_files']:
            f.write(f"**Input files referenced:**\n")
            for rf in nb['referenced_files'][:5]:
                f.write(f"- `{rf}`\n")
            if len(nb['referenced_files']) > 5:
                f.write(f"- ... and {len(nb['referenced_files']) - 5} more\n")
            f.write("\n")
        
        if nb['imports']:
            f.write(f"**Key imports:**\n")
            for imp in nb['imports'][:5]:
                f.write(f"- `{imp}`\n")
            if len(nb['imports']) > 5:
                f.write(f"- ... and {len(nb['imports']) - 5} more\n")
            f.write("\n")
        
        f.write("---\n\n")

# Write Science Map
log(f"Writing science map: {science_map_path}")
with open(science_map_path, 'w', encoding='utf-8') as f:
    f.write("# LIGO Release Science Map\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    f.write("## Executive Summary\n\n")
    f.write(f"This map categorizes the release files by scientific relevance without drawing physics conclusions.\n\n")
    f.write(f"- Total files mapped: {len(inventory)}\n")
    f.write(f"- HDF5 files inspected: {len(hdf5_structures)}\n")
    f.write(f"- Notebooks analyzed: {len(notebook_analyses)}\n\n")
    
    # Event mapping
    f.write("## Files by Event\n\n")
    for event, items in sorted(science_map['by_event'].items(), key=lambda x: -len(x[1])):
        f.write(f"### {event}\n\n")
        f.write(f"Count: {len(items)}\n\n")
        for item in items[:5]:
            f.write(f"- `{item.get('filename', 'unknown')}` ({item.get('category', 'unknown')})\n")
        if len(items) > 5:
            f.write(f"- ... and {len(items) - 5} more\n")
        f.write("\n")
    
    # Calibration mapping
    f.write("## Files by Calibration\n\n")
    for cal, items in sorted(science_map['by_calibration'].items(), key=lambda x: -len(x[1])):
        f.write(f"### {cal}\n\n")
        f.write(f"Count: {len(items)}\n\n")
        for item in items[:3]:
            f.write(f"- `{item.get('filename', 'unknown')}`\n")
        if len(items) > 3:
            f.write(f"- ... and {len(items) - 3} more\n")
        f.write("\n")
    
    # Data product mapping
    f.write("## Files by Data Product\n\n")
    for product, items in sorted(science_map['by_product'].items(), key=lambda x: -len(x[1])):
        if items:
            f.write(f"### {product}\n\n")
            f.write(f"Count: {len(items)}\n\n")
            for item in items[:3]:
                f.write(f"- `{item.get('filename', 'unknown')}` ({item.get('size_human', 'unknown')})\n")
            if len(items) > 3:
                f.write(f"- ... and {len(items) - 3} more\n")
            f.write("\n")
    
    # C00 vs C01 comparison files
    f.write("## Files for C00 vs C01 Comparison\n\n")
    c00_files = science_map['by_calibration'].get('C00', [])
    c01_files = science_map['by_calibration'].get('C01', [])
    f.write(f"- C00 files: {len(c00_files)}\n")
    f.write(f"- C01 files: {len(c01_files)}\n\n")
    f.write("Key comparison targets:\n\n")
    for item in c00_files[:3]:
        f.write(f"- C00: `{item.get('filename', 'unknown')}`\n")
    for item in c01_files[:3]:
        f.write(f"- C01: `{item.get('filename', 'unknown')}`\n")
    f.write("\n")
    
    # Unknown files
    f.write("## Unknown or Ambiguous Files\n\n")
    unknown_items = science_map['by_product'].get('unknown', [])
    f.write(f"Count: {len(unknown_items)}\n\n")
    for item in unknown_items[:5]:
        f.write(f"- `{item.get('filename', 'unknown')}` (category: {item.get('category', 'unknown')}, confidence: {item.get('confidence', 'unknown')})\n")
    f.write("\n")
    
    f.write("## DO NOT INTERPRET YET\n\n")
    f.write("""**This is a structure map, not a physics analysis.**

What this map does NOT tell us:
- Whether C00 or C01 calibration produces different physical conclusions
- Whether any GR tests show deviations
- Whether residuals contain unmodeled physics
- Whether ringdown/QNM parameters are anomalous
- Whether SSZ predictions match the data

What we know:
- Which files exist
- Their structure (HDF5 groups/datasets)
- Notebook dependencies
- Event and calibration associations

Required before physics interpretation:
1. Execute notebooks and capture outputs
2. Load posterior samples and compare variants
3. Compute numerical metrics (not just file existence)
4. Compare against theoretical predictions
""")
    
    f.write("\n## Recommended Phase 3\n\n")
    f.write("""Create reproduction readiness plan:

1. Python environment specification
2. Notebook execution order
3. Dependency installation (local, not global)
4. Output capture strategy
5. Comparison methodology for C00/C01
6. Comparison methodology for posteriors
7. Comparison methodology for GR tests

Do NOT run full science analysis until Phase 3 plan is complete.
""")

# Update log
log("=== PHASE 2 SCIENCE MAPPING COMPLETE ===")
log(f"Science map: {science_map_path}")
log(f"HDF5 report: {hdf5_report_path}")
log(f"Notebook report: {notebook_report_path}")
log(f"Total items mapped: {len(inventory)}")
log(f"HDF5 structures: {len(hdf5_structures)}")
log(f"Notebooks analyzed: {len(notebook_analyses)}")
log("STATUS: PASS")

print(f"\n=== PHASE 2 COMPLETE ===")
print(f"Science Map: {science_map_path}")
print(f"HDF5 Report: {hdf5_report_path}")
print(f"Notebook Report: {notebook_report_path}")
print(f"Log: {log_path}")
