#!/usr/bin/env python3
"""
Extract main ZIP first, then nested archives
"""

import zipfile
import tarfile
from pathlib import Path

base = Path("E:/clone/ligo-gw240925-gw250207-release")
zip_path = base / "00_RAW_DOWNLOADS" / "18600070.zip"
extract_dir = base / "01_EXTRACTED"
nested_dir = extract_dir / "nested"

print("=== LIGO Release Extraction ===\n")

# Step 1: Extract main ZIP
print(f"1. Main ZIP: {zip_path}")
print(f"   Exists: {zip_path.exists()}")

if not zip_path.exists():
    print("   ❌ ZIP not found!")
    exit(1)

print(f"   Extracting to: {extract_dir}")
extract_dir.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(zip_path, 'r') as zf:
    print(f"   ZIP contents: {len(zf.namelist())} items")
    
    # Check if already extracted
    target_folder = extract_dir / "18600070"
    if target_folder.exists():
        print(f"   ⚠️  Target folder exists: {target_folder}")
        print(f"   Checking for .tar files...")
        tar_files = list(target_folder.glob("*.tar*"))
        print(f"   Found {len(tar_files)} archive files")
        
        if len(tar_files) > 0:
            print(f"   ✅ ZIP already extracted (found {len(tar_files)} archives)")
            extract_dir = target_folder
        else:
            print(f"   🔄 Re-extracting ZIP...")
            zf.extractall(extract_dir)
            extract_dir = target_folder
    else:
        print(f"   🔄 Extracting ZIP...")
        zf.extractall(extract_dir)
        extract_dir = target_folder
        print(f"   ✅ ZIP extracted to: {extract_dir}")

# Step 2: List archives to extract
print(f"\n2. Nested archives in: {extract_dir}")
archives_to_extract = [
    ("combined_samples.tar.gz", "posteriors"),
    ("calibration.tar.gz", "calibration"),
    ("cal_env.tar.gz", "cal_env"),
    ("ringdown.tar.gz", "ringdown"),
    ("residuals.tar.gz", "residuals"),
    ("notebook.tar.gz", "notebooks"),
]

nested_dir.mkdir(parents=True, exist_ok=True)

for archive_name, folder_name in archives_to_extract:
    archive_path = extract_dir / archive_name
    target = nested_dir / folder_name
    
    print(f"\n   📦 {archive_name}")
    print(f"      Source: {archive_path}")
    print(f"      Exists: {archive_path.exists()}")
    
    if not archive_path.exists():
        print(f"      ⚠️  Skipped (not found)")
        continue
    
    if target.exists() and any(target.iterdir()):
        print(f"      ⏭️  Skipped (already extracted)")
        continue
    
    print(f"      🔄 Extracting to: {target}")
    target.mkdir(parents=True, exist_ok=True)
    
    try:
        if archive_name.endswith('.tar.gz'):
            with tarfile.open(archive_path, 'r:gz') as tar:
                print(f"         Members: {len(tar.getmembers())}")
                tar.extractall(target)
        elif archive_name.endswith('.tar'):
            with tarfile.open(archive_path, 'r') as tar:
                print(f"         Members: {len(tar.getmembers())}")
                tar.extractall(target)
        
        files = list(target.rglob("*"))
        print(f"      ✅ Done ({len(files)} items)")
        
    except Exception as e:
        print(f"      ❌ Error: {e}")

print(f"\n=== Extraction Complete ===")
print(f"Nested directory: {nested_dir}")
