"""
Phase 3D: Second Priority - Product Folder Inspection
"""
import h5py
import csv
from pathlib import Path

ROOT_DIR = Path("E:/clone/ligo-gw240925-gw250207-release/18600070")
INVENTORY_DIR = Path("E:/clone/ligo-gw240925-gw250207-release/02_INVENTORY")

product_folders = [
    "ringdown",
    "qnmrf",
    "pca",
    "pseobnr",
    "GW240925-C00-Strain",
    "combined_samples"
]

print("="*70)
print("PHASE 3D: Product Folder Inspection")
print("="*70)

all_files = []

for folder_name in product_folders:
    folder_path = ROOT_DIR / folder_name
    print(f"\n{'='*70}")
    print(f"Folder: {folder_name}")
    print(f"Path: {folder_path}")
    
    if not folder_path.exists():
        print(f"  Folder does not exist - skipping")
        continue
    
    # Find HDF5 files
    h5_files = []
    for ext in ['*.hdf5', '*.h5']:
        h5_files.extend(folder_path.rglob(ext))
    
    print(f"  HDF5 files found: {len(h5_files)}")
    
    usable_count = 0
    symlink_count = 0
    broken_count = 0
    
    for idx, h5_path in enumerate(h5_files, 1):
        print(f"\n  [{idx}/{len(h5_files)}] {h5_path.name}")
        
        # Check if it's a symlink
        try:
            is_symlink = h5_path.is_symlink()
        except:
            is_symlink = False
        
        # Try to get size
        try:
            size = h5_path.stat().st_size
            print(f"    Size: {size:,} bytes")
        except Exception as e:
            print(f"    Size: ERROR - {e}")
            size = -1
        
        result = {
            'folder': folder_name,
            'filename': h5_path.name,
            'full_path': str(h5_path),
            'size_bytes': size,
            'is_symlink': 'YES' if is_symlink else 'NO',
            'h5py_open': 'NO',
            'h5py_error': '',
            'top_level_items': '',
            'status': 'FAILED'
        }
        
        if is_symlink:
            symlink_count += 1
            # Try to resolve
            try:
                target = h5_path.readlink()
                print(f"    Symlink target: {target}")
                result['h5py_error'] = f"Symlink to {target}"
            except Exception as e:
                print(f"    Symlink target: ERROR - {e}")
                result['h5py_error'] = f"Symlink unreadable: {e}"
        else:
            # Try h5py open
            try:
                with h5py.File(h5_path, 'r') as f:
                    result['h5py_open'] = 'YES'
                    top_items = list(f.keys())
                    result['top_level_items'] = ';'.join(top_items[:20])
                    print(f"    h5py: OPEN SUCCESS")
                    print(f"    Top items: {len(top_items)}")
                    result['status'] = 'SUCCESS'
                    usable_count += 1
            except Exception as e:
                result['h5py_error'] = str(e)[:150]
                print(f"    h5py ERROR: {e}")
                broken_count += 1
        
        all_files.append(result)
    
    print(f"\n  Folder summary:")
    print(f"    Total HDF5 files: {len(h5_files)}")
    print(f"    Usable (h5py OK): {usable_count}")
    print(f"    Symlinks: {symlink_count}")
    print(f"    Broken: {broken_count}")

# Write CSV
print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")

total_usable = sum(1 for r in all_files if r['h5py_open'] == 'YES')
total_symlinks = sum(1 for r in all_files if r['is_symlink'] == 'YES')
total_broken = sum(1 for r in all_files 
                   if r['h5py_open'] == 'NO' and r['is_symlink'] == 'NO')

print(f"Total HDF5 files found: {len(all_files)}")
print(f"Usable (h5py accessible): {total_usable}")
print(f"Symlinks: {total_symlinks}")
print(f"Broken regular files: {total_broken}")

csv_path = INVENTORY_DIR / "PRODUCT_FOLDER_HDF5_INSPECTION.csv"
with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['folder', 'filename', 'full_path', 'size_bytes', 'is_symlink',
                  'h5py_open', 'h5py_error', 'top_level_items', 'status']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in all_files:
        writer.writerow(r)

print(f"\nOutput: {csv_path}")
