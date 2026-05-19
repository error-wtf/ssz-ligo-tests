#!/usr/bin/env python3
"""
Extract nested archives with progress reporting
"""

import tarfile
import os
from pathlib import Path

def extract_archive(archive_path, target_dir):
    """Extract a tar or tar.gz archive"""
    target_dir.mkdir(parents=True, exist_ok=True)
    
    if str(archive_path).endswith('.tar.gz'):
        mode = 'r:gz'
    else:
        mode = 'r'
    
    with tarfile.open(archive_path, mode) as tar:
        members = tar.getmembers()
        print(f"  Extracting {len(members)} members...")
        tar.extractall(path=target_dir)
    
    return len(members)

# Paths
base = Path("E:/clone/ligo-gw240925-gw250207-release")
source_dir = base / "01_EXTRACTED" / "18600070"
nested_dir = base / "01_EXTRACTED" / "nested"

# Archives to extract
archives = [
    ("combined_samples.tar.gz", "posteriors"),
    ("calibration.tar.gz", "calibration"),
    ("cal_env.tar.gz", "cal_env"),
    ("ringdown.tar.gz", "ringdown"),
    ("residuals.tar.gz", "residuals"),
    ("notebook.tar.gz", "notebooks"),
    ("tiger.tar.gz", "tiger"),
    ("fti.tar.gz", "fti"),
    ("pca.tar.gz", "pca"),
    ("pseobnr.tar.gz", "pseobnr"),
    ("qnmrf.tar.gz", "qnmrf"),
    ("skymaps.tar.gz", "skymaps"),
    ("GW240925-C00-Strain.tar", "strain"),
]

print("=== NESTED ARCHIVE EXTRACTION ===")
print(f"Source: {source_dir}")
print(f"Target: {nested_dir}")
print()

extracted = []
errors = []

for archive_name, folder_name in archives:
    archive_path = source_dir / archive_name
    target = nested_dir / folder_name
    
    if not archive_path.exists():
        print(f"❌ NOT FOUND: {archive_name}")
        errors.append((archive_name, "File not found"))
        continue
    
    if target.exists() and any(target.iterdir()):
        print(f"⏭️  SKIPPED (exists): {archive_name}")
        continue
    
    size_mb = archive_path.stat().st_size / (1024**2)
    print(f"📦 Extracting: {archive_name} ({size_mb:.1f} MB) -> {folder_name}/")
    
    try:
        members = extract_archive(archive_path, target)
        extracted.append((archive_name, folder_name, members))
        print(f"   ✅ {members} members extracted")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        errors.append((archive_name, str(e)))

print()
print("=== SUMMARY ===")
print(f"Extracted: {len(extracted)}")
print(f"Errors: {len(errors)}")
print()

if extracted:
    print("Successfully extracted:")
    for name, folder, members in extracted:
        print(f"  ✅ {name} -> {folder}/ ({members} items)")

if errors:
    print("\nFailed:")
    for name, err in errors:
        print(f"  ❌ {name}: {err}")

# Write summary file
summary_path = base / "01_EXTRACTED" / "EXTRACTION_SUMMARY.txt"
with open(summary_path, 'w') as f:
    f.write("=== NESTED ARCHIVE EXTRACTION SUMMARY ===\n\n")
    f.write(f"Extracted: {len(extracted)}\n")
    f.write(f"Errors: {len(errors)}\n\n")
    f.write("SUCCESS:\n")
    for name, folder, members in extracted:
        f.write(f"  {name} -> {folder}/ ({members} items)\n")
    if errors:
        f.write("\nFAILED:\n")
        for name, err in errors:
            f.write(f"  {name}: {err}\n")

print(f"\nSummary written to: {summary_path}")
