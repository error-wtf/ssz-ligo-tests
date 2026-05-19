#!/usr/bin/env python3
from pathlib import Path

base = Path("E:/clone/ligo-gw240925-gw250207-release")
archive_path = base / "01_EXTRACTED" / "18600070" / "combined_samples.tar.gz"

print(f"Checking: {archive_path}")
print(f"Exists: {archive_path.exists()}")

if not archive_path.exists():
    print("\nChecking parent directory:")
    parent = base / "01_EXTRACTED"
    if parent.exists():
        print(f"Contents of {parent}:")
        for item in parent.iterdir():
            print(f"  {item.name} ({'DIR' if item.is_dir() else 'FILE'})")
    else:
        print(f"Parent does not exist: {parent}")
