"""
PART A: Verify Regular HDF5 Access
Task: LIGO_PHASE_3C_SYMLINK_TARGET_RESOLUTION_AUDIT
"""
import csv
import h5py
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("E:/clone/ligo-gw240925-gw250207-release")
INVENTORY_DIR = BASE_DIR / "02_INVENTORY"

# Read existing forensics CSV
csv_path = INVENTORY_DIR / "HDF5_SYMLINK_FORENSICS.csv"

records = []
with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        records.append(row)

# Filter regular files (non-symlinks)
regular_files = [r for r in records if r.get('LinkType') != 'SymbolicLink']

print(f"Total regular HDF5 files: {len(regular_files)}")

results = []
for idx, r in enumerate(regular_files):
    full_path = r.get('FullName', '')
    path_obj = Path(full_path)
    
    print(f"\n[{idx+1}/{len(regular_files)}] Testing: {path_obj.name}")
    
    result = {
        'full_path': full_path,
        'filename': path_obj.name,
        'size_bytes': '',
        'can_open_h5py': 'NO',
        'h5py_exception': '',
        'top_level_groups': '',
        'read_only_test': 'NO'
    }
    
    # Check if file exists and get size
    if path_obj.exists():
        try:
            size = path_obj.stat().st_size
            result['size_bytes'] = size
            print(f"  Size: {size:,} bytes ({size/1024/1024:.1f} MB)")
        except Exception as e:
            result['size_bytes'] = f"ERROR: {e}"
            print(f"  Size ERROR: {e}")
    else:
        result['size_bytes'] = "FILE_NOT_FOUND"
        print(f"  File not found!")
        results.append(result)
        continue
    
    # Try to open with h5py read-only
    try:
        with h5py.File(full_path, 'r') as f:
            result['can_open_h5py'] = 'YES'
            print(f"  h5py: OPEN SUCCESS")
            
            # Get top-level groups only (no dataset loading)
            top_items = []
            for name in f.keys():
                obj = f[name]
                item_type = 'group' if isinstance(obj, h5py.Group) else 'dataset'
                if item_type == 'group':
                    top_items.append(f"{name}/")
                else:
                    shape = str(obj.shape) if hasattr(obj, 'shape') else 'N/A'
                    top_items.append(f"{name}[{shape}]")
            
            result['top_level_groups'] = ';'.join(top_items[:20])  # Limit output
            print(f"  Top-level items: {len(top_items)}")
            result['read_only_test'] = 'YES'
    except Exception as e:
        result['can_open_h5py'] = 'NO'
        result['h5py_exception'] = str(e)[:200]
        print(f"  h5py ERROR: {e}")
    
    results.append(result)

# Write CSV
output_csv = INVENTORY_DIR / "REGULAR_HDF5_ACCESS_RECHECK.csv"
with open(output_csv, 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['full_path', 'filename', 'size_bytes', 'can_open_h5py', 
                  'h5py_exception', 'top_level_groups', 'read_only_test']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in results:
        writer.writerow(r)

accessible_count = sum(1 for r in results if r['can_open_h5py'] == 'YES')
print(f"\n{'='*60}")
print(f"SUMMARY:")
print(f"  Total regular files: {len(results)}")
print(f"  h5py accessible: {accessible_count}")
print(f"  h5py failed: {len(results) - accessible_count}")
print(f"  Output: {output_csv}")
