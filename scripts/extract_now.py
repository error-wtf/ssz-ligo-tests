#!/usr/bin/env python3
"""
Extract nested archives from 01_EXTRACTED/ to 01_EXTRACTED/nested/
"""

import tarfile
from pathlib import Path

base = Path("E:/clone/ligo-gw240925-gw250207-release")
source_dir = base / "01_EXTRACTED"
nested_dir = source_dir / "nested"

# Archives to extract (name, folder)
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
]

print("=== Extracting LIGO Nested Archives ===\n")
print(f"Source: {source_dir}")
print(f"Target: {nested_dir}\n")

nested_dir.mkdir(parents=True, exist_ok=True)

for archive_name, folder_name in archives:
    archive_path = source_dir / archive_name
    target = nested_dir / folder_name
    
    print(f"📦 {archive_name}")
    
    if not archive_path.exists():
        print(f"   ⚠️  Not found: {archive_path}")
        continue
    
    size_mb = archive_path.stat().st_size / (1024**2)
    print(f"   Size: {size_mb:.1f} MB")
    
    if target.exists() and any(target.iterdir()):
        print(f"   ⏭️  Already extracted")
        continue
    
    print(f"   🔄 Extracting to: {folder_name}/")
    target.mkdir(parents=True, exist_ok=True)
    
    try:
        with tarfile.open(archive_path, 'r:gz') as tar:
            members = tar.getmembers()
            print(f"      Members: {len(members)}")
            tar.extractall(target)
        
        files = list(target.rglob("*"))
        print(f"   ✅ Done ({len(files)} items)")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")

print(f"\n=== Done ===")
print(f"Check: {nested_dir}")
