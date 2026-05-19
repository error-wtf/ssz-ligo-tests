#!/usr/bin/env python3
"""
PHASE 1B: Extraction Validation + PHASE 2: Science Mapping
LIGO GW240925/GW250207 Data Release

Validate extraction completeness, then map scientific structure
"""

import os
import json
import csv
from pathlib import Path
from datetime import datetime

# Paths
ROOT = Path("E:/clone/ligo-gw240925-gw250207-release")
EXTRACTED_DIR = ROOT / "18600070"  # User extracted here
NESTED_DIR = EXTRACTED_DIR  # Archives extracted in place
INVENTORY_DIR = ROOT / "02_INVENTORY"
LOGS_DIR = ROOT / "06_WINDSURF_LOGS"

# Ensure directories
INVENTORY_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Expected archives and their typical contents
EXPECTED_ARCHIVES = {
    "combined_samples.tar.gz": {"folder": "combined_samples", "type": "posteriors", "critical": True},
    "calibration.tar.gz": {"folder": "calibration", "type": "calibration", "critical": True},
    "cal_env.tar.gz": {"folder": "cal_env", "type": "calibration_env", "critical": True},
    "ringdown.tar.gz": {"folder": "ringdown", "type": "ringdown", "critical": True},
    "residuals.tar.gz": {"folder": "residuals", "type": "residuals", "critical": True},
    "notebook.tar.gz": {"folder": "notebook", "type": "notebooks", "critical": True},
    "tiger.tar.gz": {"folder": "tiger", "type": "gr_tests", "critical": False},
    "fti.tar.gz": {"folder": "fti", "type": "gr_tests", "critical": False},
    "pca.tar.gz": {"folder": "pca", "type": "gr_tests", "critical": False},
    "pseobnr.tar.gz": {"folder": "pseobnr", "type": "waveforms", "critical": False},
    "qnmrf.tar.gz": {"folder": "qnmrf", "type": "qnm", "critical": True},
    "skymaps.tar.gz": {"folder": "skymaps", "type": "skymaps", "critical": False},
    "GW240925-C00-Strain.tar": {"folder": "strain", "type": "strain", "critical": True},
}

log_content = []
def log(msg):
    print(msg)
    log_content.append(f"{datetime.now().isoformat()} - {msg}")

log("=== PHASE 1B: EXTRACTION VALIDATION ===")
log(f"Scanning: {NESTED_DIR}")

# 1. Check what exists
validation_results = {}
all_ok = True

for archive_name, info in EXPECTED_ARCHIVES.items():
    folder = NESTED_DIR / info["folder"]
    
    exists = folder.exists()
    if exists:
        files = list(folder.rglob("*")) if folder.is_dir() else []
        file_count = len([f for f in files if f.is_file()])
        total_size = sum(f.stat().st_size for f in files if f.is_file()) if files else 0
        status = "PASS" if file_count > 0 else "EMPTY"
    else:
        file_count = 0
        total_size = 0
        status = "MISSING"
    
    if info["critical"] and status != "PASS":
        all_ok = False
    
    validation_results[archive_name] = {
        "folder": str(folder),
        "exists": exists,
        "file_count": file_count,
        "size_bytes": total_size,
        "status": status,
        "critical": info["critical"],
        "type": info["type"]
    }
    
    status_icon = "✅" if status == "PASS" else "⚠️" if status == "EMPTY" else "❌"
    log(f"{status_icon} {archive_name}: {status} ({file_count} files, {total_size/1024**2:.1f} MB)")

# Overall status
overall_status = "PASS" if all_ok else "PARTIAL"
log(f"\n=== OVERALL: {overall_status} ===")
log(f"Critical archives OK: {sum(1 for r in validation_results.values() if r['critical'] and r['status'] == 'PASS')}/{sum(1 for r in validation_results.values() if r['critical'])}")

# 2. Generate Manifest
manifest_path = INVENTORY_DIR / "NESTED_EXTRACTION_MANIFEST.csv"
with open(manifest_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['archive_name', 'extraction_folder', 'file_path', 'filename', 'extension', 'size_bytes', 'status'])
    
    for archive_name, info in validation_results.items():
        folder = Path(info["folder"])
        if folder.exists() and folder.is_dir():
            for file_path in folder.rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(NESTED_DIR)
                    writer.writerow([
                        archive_name,
                        folder.name,
                        str(rel_path),
                        file_path.name,
                        file_path.suffix,
                        file_path.stat().st_size,
                        info["status"]
                    ])

log(f"✅ Manifest: {manifest_path}")

# 3. Generate Validation Report
report_path = INVENTORY_DIR / "NESTED_EXTRACTION_VALIDATION_REPORT.md"
with open(report_path, 'w', encoding='utf-8') as f:
    f.write("# Nested Archive Extraction Validation Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    f.write(f"**Overall Status:** {overall_status}\n\n")
    
    f.write("## Summary Table\n\n")
    f.write("| Archive | Status | Files | Size (MB) | Critical |\n")
    f.write("|---------|--------|-------|-----------|----------|\n")
    
    for archive_name, info in validation_results.items():
        size_mb = info["size_bytes"] / 1024**2
        critical_mark = "✅" if info["critical"] else ""
        f.write(f"| {archive_name} | {info['status']} | {info['file_count']} | {size_mb:.1f} | {critical_mark} |\n")
    
    f.write("\n## Critical Archives\n\n")
    for archive_name, info in validation_results.items():
        if info["critical"]:
            f.write(f"- **{archive_name}** ({info['type']}): {info['status']}\n")
    
    f.write("\n## Recommendations\n\n")
    if overall_status == "PASS":
        f.write("✅ **Proceed to Phase 2: Science Mapping**\n\n")
        f.write("All critical archives extracted. Ready for HDF5 inspection and notebook analysis.\n")
    else:
        f.write("⚠️ **Missing critical archives**\n\n")
        f.write("Some critical archives missing or empty. Review extraction.\n")

log(f"✅ Validation Report: {report_path}")

# 4. Generate Log
log_path = LOGS_DIR / "PHASE_1B_EXTRACTION_VALIDATION_LOG.md"
with open(log_path, 'w', encoding='utf-8') as f:
    f.write("# Phase 1B Extraction Validation Log\n\n")
    f.write(f"**Status:** {overall_status}\n\n")
    for entry in log_content:
        f.write(f"{entry}\n")

log(f"✅ Log: {log_path}")

# 5. If PASS, proceed to Phase 2: Science Mapping
if overall_status == "PASS":
    log("\n=== PHASE 2: SCIENCE MAPPING ===")
    
    # Find HDF5 files
    hdf5_files = []
    for folder in NESTED_DIR.iterdir():
        if folder.is_dir():
            hdf5_files.extend(folder.rglob("*.hdf5"))
            hdf5_files.extend(folder.rglob("*.h5"))
    
    log(f"Found {len(hdf5_files)} HDF5 files")
    
    # Find notebooks
    notebook_files = []
    for folder in NESTED_DIR.iterdir():
        if folder.is_dir():
            notebook_files.extend(folder.rglob("*.ipynb"))
    
    log(f"Found {len(notebook_files)} Jupyter notebooks")
    
    # Generate Science Mapping Report
    science_map_path = INVENTORY_DIR / "LIGO_RELEASE_SCIENCE_MAP.md"
    with open(science_map_path, 'w', encoding='utf-8') as f:
        f.write("# LIGO Release Science Map\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
        
        f.write("## Data Products by Type\n\n")
        f.write("| Type | Archives | Key Files |\n")
        f.write("|------|----------|-----------|\n")
        
        type_groups = {}
        for archive_name, info in validation_results.items():
            dtype = info["type"]
            if dtype not in type_groups:
                type_groups[dtype] = []
            type_groups[dtype].append(archive_name)
        
        for dtype, archives in sorted(type_groups.items()):
            f.write(f"| {dtype} | {', '.join(archives)} | TBD |\n")
        
        f.write("\n## HDF5 Files\n\n")
        for hdf5_path in sorted(hdf5_files)[:20]:
            rel_path = hdf5_path.relative_to(NESTED_DIR)
            size_mb = hdf5_path.stat().st_size / 1024**2
            f.write(f"- `{rel_path}` ({size_mb:.1f} MB)\n")
        if len(hdf5_files) > 20:
            f.write(f"- ... and {len(hdf5_files) - 20} more\n")
        
        f.write("\n## Notebooks\n\n")
        for nb_path in sorted(notebook_files)[:10]:
            rel_path = nb_path.relative_to(NESTED_DIR)
            f.write(f"- `{rel_path}`\n")
        if len(notebook_files) > 10:
            f.write(f"- ... and {len(notebook_files) - 10} more\n")
        
        f.write("\n## Next Steps\n\n")
        f.write("1. Inspect HDF5 structure (headers only)\n")
        f.write("2. Map notebook dependencies\n")
        f.write("3. Identify C00/C01/envcal variants\n")
        f.write("4. Locate QNM/ringdown data for SSZ test\n")
    
    log(f"✅ Science Map: {science_map_path}")

log("\n=== COMPLETE ===")
print(f"\nFinal Status: {overall_status}")
print(f"Validation Report: {report_path}")
print(f"Science Map: {science_map_path if overall_status == 'PASS' else 'N/A'}")
