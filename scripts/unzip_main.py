#!/usr/bin/env python3
from pathlib import Path
import zipfile

base = Path("E:/clone/ligo-gw240925-gw250207-release")
zip_path = base / "00_RAW_DOWNLOADS" / "18600070.zip"
extract_to = base / "01_EXTRACTED"

print(f"ZIP: {zip_path}")
print(f"Exists: {zip_path.exists()}")

if zip_path.exists():
    size_mb = zip_path.stat().st_size / (1024**2)
    print(f"Size: {size_mb:.0f} MB")
    
    print(f"\nExtracting to: {extract_to}")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        print(f"Contents: {len(zf.namelist())} items")
        print("First 10 items:")
        for name in zf.namelist()[:10]:
            print(f"  {name}")
        
        # Extract
        zf.extractall(extract_to)
        print(f"\n✅ Extracted to: {extract_to}")
        
        # Check result
        extracted_folder = extract_to / "18600070"
        if extracted_folder.exists():
            items = list(extracted_folder.iterdir())
            print(f"Extracted folder: {extracted_folder}")
            print(f"Items: {len(items)}")
            for item in items[:10]:
                print(f"  {item.name}")
else:
    print("❌ ZIP not found!")
