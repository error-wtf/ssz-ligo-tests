"""
Phase 3D: Correct Root HDF5 Rescan
First Priority: Open top-level metafiles
"""
import h5py
import csv
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("E:/clone/ligo-gw240925-gw250207-release/18600070")
INVENTORY_DIR = Path("E:/clone/ligo-gw240925-gw250207-release/02_INVENTORY")
LOGS_DIR = Path("E:/clone/ligo-gw240925-gw250207-release/06_WINDSURF_LOGS")

# Create output dirs
INVENTORY_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# First Priority: Top-level metafiles
metafiles = [
    "GW240925_combinedPHM_envcalC01_metafile.hdf5",
    "GW250207_combinedPHM_cal_metafile.hdf5"
]

search_terms = ['final_mass', 'final_spin', 'remnant_mass', 'remnant_spin', 
                'mass_1', 'mass_2', 'qnm', 'ringdown', 'f_220', 'tau_220', 
                'frequency', 'calibration', 'C00', 'C01', 'envcal', 'cal']

print("="*70)
print("PHASE 3D: Top-Level Metafile Inspection")
print("="*70)

results = []

for idx, mf_name in enumerate(metafiles, 1):
    mf_path = ROOT_DIR / mf_name
    print(f"\n[{idx}/{len(metafiles)}] {mf_name}")
    print(f"  Path: {mf_path}")
    
    result = {
        'filename': mf_name,
        'full_path': str(mf_path),
        'exists': 'NO',
        'size_bytes': 0,
        'h5py_open': 'NO',
        'h5py_error': '',
        'top_level_groups': '',
        'total_items': 0,
        'qnm_matches': '',
        'status': 'FAILED'
    }
    
    # Check existence
    if not mf_path.exists():
        print(f"  ERROR: File does not exist!")
        results.append(result)
        continue
    
    result['exists'] = 'YES'
    print(f"  EXISTS: YES")
    
    # Get size
    try:
        size = mf_path.stat().st_size
        result['size_bytes'] = size
        print(f"  Size: {size:,} bytes ({size/1024/1024:.1f} MB)")
    except Exception as e:
        print(f"  Size ERROR: {e}")
    
    # Try h5py open
    try:
        with h5py.File(mf_path, 'r') as f:
            result['h5py_open'] = 'YES'
            print(f"  h5py: OPEN SUCCESS")
            
            # Get top-level groups
            top_items = list(f.keys())
            result['top_level_groups'] = ';'.join(top_items)
            print(f"  Top-level items: {len(top_items)}")
            for item in top_items[:10]:
                obj = f[item]
                item_type = 'group' if isinstance(obj, h5py.Group) else 'dataset'
                print(f"    - {item} ({item_type})")
            
            # Recursive walk - count items, find QNM matches
            all_items = []
            qnm_matches = []
            
            def collect(name, obj):
                all_items.append(name)
                # Check for QNM-related terms
                name_lower = name.lower()
                for term in search_terms:
                    if term.lower() in name_lower:
                        item_type = 'group' if isinstance(obj, h5py.Group) else 'dataset'
                        shape = str(obj.shape) if hasattr(obj, 'shape') else 'N/A'
                        qnm_matches.append(f"{name}[{item_type}][{shape}]")
                        break
            
            f.visititems(collect)
            result['total_items'] = len(all_items)
            result['qnm_matches'] = ';'.join(qnm_matches[:50])  # Limit
            print(f"  Total items: {len(all_items)}")
            print(f"  QNM-related matches: {len(qnm_matches)}")
            if qnm_matches[:5]:
                for m in qnm_matches[:5]:
                    print(f"    - {m}")
            
            result['status'] = 'SUCCESS'
    except Exception as e:
        result['h5py_error'] = str(e)[:200]
        print(f"  h5py ERROR: {e}")
    
    results.append(result)

# Write results
print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")

accessible = sum(1 for r in results if r['h5py_open'] == 'YES')
print(f"Metafiles found: {len(results)}")
print(f"Metafiles accessible via h5py: {accessible}")

# Write CSV
csv_path = INVENTORY_DIR / "CORRECT_ROOT_HDF5_STRUCTURE_SUMMARY.csv"
with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['filename', 'full_path', 'exists', 'size_bytes', 'h5py_open',
                  'h5py_error', 'top_level_groups', 'total_items', 'qnm_matches', 'status']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in results:
        writer.writerow(r)

print(f"\nOutput: {csv_path}")
