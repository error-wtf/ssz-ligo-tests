#!/usr/bin/env python3
"""
Extract single archive with progress - quick test
"""

import tarfile
from pathlib import Path

base = Path("E:/clone/ligo-gw240925-gw250207-release")
source_dir = base / "01_EXTRACTED" / "18600070"
target_dir = base / "01_EXTRACTED" / "nested"

# Combined samples first (smaller, faster)
archive_name = "combined_samples.tar.gz"
folder_name = "posteriors"

archive_path = source_dir / archive_name
target = target_dir / folder_name

print(f"Source: {archive_path}")
print(f"Target: {target}")
print(f"Exists: {archive_path.exists()}")

if not archive_path.exists():
    print(f"❌ Archive not found: {archive_path}")
    # List what we have
    if source_dir.exists():
        print(f"Contents of {source_dir}:")
        for item in source_dir.iterdir():
            print(f"  {item.name}")
    exit(1)

target.mkdir(parents=True, exist_ok=True)

print(f"\n📦 Extracting {archive_name}...")
with tarfile.open(archive_path, 'r:gz') as tar:
    members = tar.getmembers()
    print(f"   Found {len(members)} members")
    
    # Extract with progress
    for i, member in enumerate(members):
        tar.extract(member, target)
        if (i + 1) % 100 == 0 or i == len(members) - 1:
            print(f"   Progress: {i+1}/{len(members)}")

print(f"✅ Done: {archive_name} → {target}")

# Show result
if target.exists():
    files = list(target.rglob("*"))
    print(f"   Total items: {len(files)}")
    for f in files[:10]:
        print(f"   - {f.relative_to(target)}")
    if len(files) > 10:
        print(f"   ... and {len(files)-10} more")
