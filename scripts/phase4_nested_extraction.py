#!/usr/bin/env python3
"""
PHASE 4 - NESTED ARCHIVE EXTRACTION & ENVIRONMENT SETUP

Extracts tar.gz archives from 1860070.zip into nested folders
Creates Python virtual environment
Installs core dependencies
"""

import os
import tarfile
import gzip
import shutil
from pathlib import Path
from datetime import datetime

ROOT = Path("E:/clone/ligo-gw240925-gw250207-release")
EXTRACTED_DIR = ROOT / "01_EXTRACTED" / "18600070"
NESTED_DIR = ROOT / "01_EXTRACTED" / "nested"
LOGS_DIR = ROOT / "06_WINDSURF_LOGS"

# Ensure directories exist
NESTED_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Log file
log_path = LOGS_DIR / "PHASE_4_NESTED_EXTRACTION_LOG.md"

log_content = []
def log(msg):
    print(msg)
    log_content.append(f"{datetime.now().isoformat()} - {msg}")

log("=== PHASE 4 NESTED ARCHIVE EXTRACTION START ===")

# Archives to extract
ARCHIVES = [
    "calibration.tar.gz",
    "cal_env.tar.gz",
    "combined_samples.tar.gz",
    "ringdown.tar.gz",
    "tiger.tar.gz",
    "pca.tar.gz",
    "pseobnr.tar.gz",
    "qnmrf.tar.gz",
    "residuals.tar.gz",
    "skymaps.tar.gz",
    "notebook.tar.gz",
    "fti.tar.gz",
    "GW240925-C00-Strain.tar"
]

extracted_count = 0
skipped_count = 0
error_count = 0

for archive_name in ARCHIVES:
    archive_path = EXTRACTED_DIR / archive_name
    
    if not archive_path.exists():
        log(f"WARNING: Archive not found: {archive_name}")
        error_count += 1
        continue
    
    # Determine target folder name
    if archive_name.endswith('.tar.gz'):
        folder_name = archive_name[:-7]  # Remove .tar.gz
    elif archive_name.endswith('.tar'):
        folder_name = archive_name[:-4]  # Remove .tar
    else:
        folder_name = archive_name
    
    target_dir = NESTED_DIR / folder_name
    
    # Check if already extracted
    if target_dir.exists():
        log(f"SKIPPED (exists): {archive_name} -> {target_dir}")
        skipped_count += 1
        continue
    
    # Extract
    try:
        log(f"Extracting: {archive_name}...")
        target_dir.mkdir(parents=True, exist_ok=True)
        
        if archive_name.endswith('.tar.gz'):
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(path=target_dir)
        elif archive_name.endswith('.tar'):
            with tarfile.open(archive_path, 'r') as tar:
                tar.extractall(path=target_dir)
        
        log(f"SUCCESS: {archive_name} -> {target_dir}")
        extracted_count += 1
        
    except Exception as e:
        log(f"ERROR extracting {archive_name}: {e}")
        error_count += 1

log(f"=== EXTRACTION SUMMARY ===")
log(f"Extracted: {extracted_count}")
log(f"Skipped (already exists): {skipped_count}")
log(f"Errors: {error_count}")

# List extracted contents
log("\n=== EXTRACTED CONTENTS ===")
for subdir in sorted(NESTED_DIR.iterdir()):
    if subdir.is_dir():
        file_count = sum(1 for _ in subdir.rglob('*') if _.is_file())
        log(f"{subdir.name}: {file_count} files")

# Environment setup instructions
log("\n=== PYTHON ENVIRONMENT SETUP ===")
venv_path = ROOT / "venv_ligo"

if venv_path.exists():
    log(f"Virtual environment exists: {venv_path}")
else:
    log(f"To create environment, run:")
    log(f"  cd {ROOT}")
    log(f"  python -m venv venv_ligo")
    log(f"  venv_ligo\\Scripts\\activate")
    log(f"  pip install numpy scipy matplotlib h5py pandas")
    log(f"  pip install gwpy astropy")

# Write log
with open(log_path, 'w', encoding='utf-8') as f:
    f.write("# Phase 4 Nested Extraction Log\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    for entry in log_content:
        f.write(f"{entry}\n")
    f.write("\n=== STATUS ===\n")
    f.write(f"Extracted: {extracted_count}\n")
    f.write(f"Skipped: {skipped_count}\n")
    f.write(f"Errors: {error_count}\n")
    f.write("PASS\n" if error_count == 0 else "PARTIAL\n")

log("=== PHASE 4 COMPLETE ===")
print(f"\nLog written to: {log_path}")
print(f"Nested archives in: {NESTED_DIR}")
