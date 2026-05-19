#!/usr/bin/env python3
"""
LIGO_GW240925_GW250207_RELEASE_PHASE_1_EVIDENCE_INVENTORY
Strict inventory only - no scientific interpretation
"""

import os
import json
import csv
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
log_path = LOGS_DIR / "PHASE_1_EVIDENCE_INVENTORY_LOG.md"
inventory_path = INVENTORY_DIR / "LIGO_RELEASE_INVENTORY.md"

def log(msg):
    print(msg)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now().isoformat()} - {msg}\n")

log("=== PHASE 1 EVIDENCE INVENTORY START ===")

# File categorization rules
def categorize_file(path: Path, filename: str, ext: str):
    """Categorize file by name and extension - conservative approach"""
    name_lower = filename.lower()
    
    # Notebooks
    if ext == '.ipynb':
        return 'notebook', 'HIGH'
    
    # Strain data
    if 'strain' in name_lower and ext in ['.tar', '.gz']:
        return 'strain_data', 'HIGH'
    
    # Calibration
    if 'calibration' in name_lower and ext in ['.tar', '.gz']:
        return 'calibration_data', 'HIGH'
    if 'cal_env' in name_lower or 'envelope' in name_lower:
        return 'calibration_environment', 'HIGH'
    if 'envcal' in name_lower:
        return 'calibration_environment', 'HIGH'
    
    # Posterior samples
    if 'combined' in name_lower and 'sample' in name_lower:
        return 'posterior_samples', 'HIGH'
    if 'metafile' in name_lower and ext == '.hdf5':
        return 'posterior_samples', 'HIGH'
    
    # Skymaps
    if 'skymap' in name_lower:
        return 'skymap', 'HIGH'
    
    # Residuals
    if 'residual' in name_lower:
        return 'residual_data', 'HIGH'
    
    # Ringdown / QNM
    if 'ringdown' in name_lower:
        return 'ringdown_QNM', 'HIGH'
    if 'qnm' in name_lower or 'qnmrf' in name_lower:
        return 'ringdown_QNM', 'HIGH'
    
    # TIGER / FTI / PCA / PSEOBNR
    if 'tiger' in name_lower:
        return 'TIGER', 'HIGH'
    if 'fti' in name_lower:
        return 'FTI', 'HIGH'
    if 'pca' in name_lower:
        return 'PCA', 'HIGH'
    if 'pseobnr' in name_lower:
        return 'PSEOBNR', 'HIGH'
    
    # HDF5 files (likely posterior/samples)
    if ext == '.hdf5':
        if 'combined' in name_lower:
            return 'posterior_samples', 'HIGH'
        if 'cal' in name_lower or 'env' in name_lower:
            return 'calibration_data', 'MEDIUM'
        return 'unknown_hdf5', 'LOW'
    
    # Plots/Figures
    if ext in ['.png', '.jpg', '.jpeg', '.pdf']:
        if 'fig' in name_lower or 'plot' in name_lower:
            return 'plot_figure', 'HIGH'
        return 'plot_figure', 'MEDIUM'
    
    # Documentation
    if ext in ['.md', '.txt', '.rst']:
        return 'documentation', 'HIGH'
    if ext == '.json' and ('metadata' in name_lower or 'manifest' in name_lower):
        return 'metadata', 'HIGH'
    
    # Scripts
    if ext in ['.py', '.m', '.sh']:
        return 'script_code', 'HIGH'
    
    # Archives
    if ext in ['.tar', '.gz', '.zip']:
        return 'archive', 'HIGH'
    
    return 'unknown', 'LOW'

def identify_event(filename: str):
    """Identify associated GW event"""
    name_lower = filename.lower()
    if '240925' in name_lower:
        return 'GW240925'
    if '250207' in name_lower:
        return 'GW250207'
    if 'combined' in name_lower:
        return 'both'
    return 'unknown'

def identify_calibration(filename: str):
    """Identify calibration tag"""
    name_lower = filename.lower()
    if 'c00' in name_lower:
        return 'C00'
    if 'c01' in name_lower or 'envcalc01' in name_lower:
        return 'C01'
    if 'envcal' in name_lower or 'envelope' in name_lower:
        return 'envcal'
    if 'cal' in name_lower and 'meta' in name_lower:
        return 'cal'
    return 'unknown'

# Collect all files
inventory = []

# 1. Raw downloads
log("Scanning 00_RAW_DOWNLOADS...")
for f in RAW_DIR.iterdir():
    if f.is_file():
        category, confidence = categorize_file(f, f.name, f.suffix.lower())
        inventory.append({
            'path': str(f.relative_to(ROOT)),
            'filename': f.name,
            'extension': f.suffix.lower(),
            'size_bytes': f.stat().st_size,
            'size_human': f"{f.stat().st_size / (1024**3):.2f} GB" if f.stat().st_size > 1024**3 else f"{f.stat().st_size / (1024**2):.2f} MB",
            'category': category,
            'event': identify_event(f.name),
            'calibration': identify_calibration(f.name),
            'confidence': confidence,
            'source': 'raw_download'
        })
        log(f"  Found: {f.name} ({category}, {confidence})")

# 2. Extracted files (top level)
log("Scanning 01_EXTRACTED/18600070 (top level)...")
if EXTRACTED_DIR.exists():
    for f in EXTRACTED_DIR.iterdir():
        if f.is_file():
            category, confidence = categorize_file(f, f.name, f.suffix.lower())
            inventory.append({
                'path': str(f.relative_to(ROOT)),
                'filename': f.name,
                'extension': f.suffix.lower(),
                'size_bytes': f.stat().st_size,
                'size_human': f"{f.stat().st_size / (1024**3):.2f} GB" if f.stat().st_size > 1024**3 else f"{f.stat().st_size / (1024**2):.2f} MB",
                'category': category,
                'event': identify_event(f.name),
                'calibration': identify_calibration(f.name),
                'confidence': confidence,
                'source': 'extracted_top_level'
            })
            log(f"  Found: {f.name} ({category}, {confidence})")

# Write inventory CSV
csv_path = INVENTORY_DIR / "LIGO_RELEASE_INVENTORY.csv"
with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    if inventory:
        writer = csv.DictWriter(f, fieldnames=inventory[0].keys())
        writer.writeheader()
        writer.writerows(inventory)

log(f"Wrote inventory CSV: {csv_path}")

# Generate markdown inventory report
with open(inventory_path, 'w', encoding='utf-8') as f:
    f.write("# LIGO Release Inventory\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    f.write("## Executive Summary\n\n")
    f.write(f"- Total files inventoried: {len(inventory)}\n")
    
    # Count by category
    categories = {}
    for item in inventory:
        cat = item['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    f.write("\n### Files by Category\n\n")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        f.write(f"- {cat}: {count}\n")
    
    # Count by event
    events = {}
    for item in inventory:
        evt = item['event']
        events[evt] = events.get(evt, 0) + 1
    
    f.write("\n### Files by Event\n\n")
    for evt, count in sorted(events.items(), key=lambda x: -x[1]):
        f.write(f"- {evt}: {count}\n")
    
    # Key files sections
    f.write("\n## Key Files for Calibration Robustness\n\n")
    for item in inventory:
        if item['category'] in ['calibration_data', 'calibration_environment', 'strain_data']:
            f.write(f"- `{item['path']}` ({item['size_human']})\n")
    
    f.write("\n## Key Files for C00 vs C01 Comparison\n\n")
    for item in inventory:
        if item['calibration'] in ['C00', 'C01'] and item['category'] in ['strain_data', 'posterior_samples']:
            f.write(f"- `{item['path']}` ({item['calibration']}, {item['size_human']})\n")
    
    f.write("\n## Key Files for GR-Test/Ringdown/QNM\n\n")
    for item in inventory:
        if item['category'] in ['ringdown_QNM', 'TIGER', 'FTI', 'PCA', 'PSEOBNR']:
            f.write(f"- `{item['path']}` ({item['category']}, {item['size_human']})\n")
    
    f.write("\n## Unknown or Ambiguous Files\n\n")
    for item in inventory:
        if item['confidence'] == 'LOW' or item['category'] == 'unknown':
            f.write(f"- `{item['path']}` (category: {item['category']}, confidence: {item['confidence']})\n")
    
    f.write("\n## DO NOT INTERPRET YET\n\n")
    f.write("""This inventory is **evidence handling only**. No scientific conclusions have been drawn.

**What this inventory does NOT tell us:**
- Whether C00 or C01 calibration is "correct"
- Whether GR deviations exist in the data
- Whether calibration artifacts mimic physics
- Whether ringdown/QNM parameters are robust

**Required before interpretation:**
1. Nested archives (tar.gz) must be extracted and inventoried
2. HDF5 files must be inspected for structure (not just listed)
3. Notebooks must be run to verify reproducibility
4. Calibration envelopes must be loaded and plotted
5. Posterior samples must be loaded and compared

**Phase 2 required:** Nested archive extraction and detailed file inspection.
""")
    
    f.write("\n## Recommended Phase 2\n\n")
    f.write("""Next phase should:

1. Extract nested tar.gz archives into separate folders:
   - calibration.tar.gz → 01_EXTRACTED/nested/calibration/
   - ringdown.tar.gz → 01_EXTRACTED/nested/ringdown/
   - etc.

2. Load and inspect one HDF5 posterior file to verify structure

3. Run one notebook to verify Python environment works

4. Identify which files are:
   - Raw strain (C00 vs C01 vs envcal)
   - Posterior samples (C00 vs C01)
   - Ringdown posteriors
   - GR-test results

5. Create mapping: File → Comparison type (C00/C01, calibration envelope, GR test)

6. Document data volumes and compute requirements

**Do NOT run:**
- Full parameter estimation
- GR deviation tests
- Calibration robustness analysis
- Plotting of "SSZ vs GR" comparisons

**Do NOT claim:**
- "This proves/disproves SSZ"
- "Calibration explains all deviations"
- "Ringdown shows GR violation"
""")

log(f"Wrote inventory report: {inventory_path}")

# Update log with completion
log("=== PHASE 1 EVIDENCE INVENTORY COMPLETE ===")
log(f"Total files: {len(inventory)}")
log(f"Categories: {len(categories)}")
log(f"Events: {list(events.keys())}")
log("STATUS: PASS")

print(f"\n=== PHASE 1 COMPLETE ===")
print(f"Inventory: {inventory_path}")
print(f"Log: {log_path}")
print(f"CSV: {csv_path}")
