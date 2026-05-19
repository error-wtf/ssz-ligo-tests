"""
Archive Symlink Inspection
"""
import tarfile
import os
from pathlib import Path

BASE_DIR = Path("E:/clone/ligo-gw240925-gw250207-release")

archives = [
    BASE_DIR / "18600070" / "combined_samples.tar.gz",
    BASE_DIR / "18600070" / "fti.tar.gz",
    BASE_DIR / "18600070" / "ringdown.tar.gz",
    BASE_DIR / "18600070" / "qnmrf.tar.gz"
]

results = []

for arc_name in archives:
    arc_path = BASE_DIR / arc_name
    if not arc_path.exists():
        print(f"MISSING: {arc_name}")
        continue
    
    print(f"\n=== {arc_name} ===")
    try:
        with tarfile.open(arc_path, 'r:gz') as tar:
            members = tar.getmembers()
            total = len(members)
            regular = sum(1 for m in members if m.isreg())
            symlinks = sum(1 for m in members if m.issym())
            hardlinks = sum(1 for m in members if m.islnk())
            dirs = sum(1 for m in members if m.isdir())
            
            print(f"Total members: {total}")
            print(f"Regular files: {regular}")
            print(f"Symlinks: {symlinks}")
            print(f"Hardlinks: {hardlinks}")
            print(f"Directories: {dirs}")
            
            # List HDF5 symlinks
            h5_symlinks = [m for m in members if m.issym() and (m.name.endswith('.hdf5') or m.name.endswith('.h5'))]
            print(f"\nHDF5/H5 symlinks: {len(h5_symlinks)}")
            for s in h5_symlinks[:10]:
                print(f"  {s.name} -> {s.linkname}")
            
            results.append({
                'archive': arc_name,
                'total': total,
                'regular': regular,
                'symlinks': symlinks,
                'hardlinks': hardlinks,
                'h5_symlinks': len(h5_symlinks)
            })
    except Exception as e:
        print(f"ERROR: {e}")

print("\n=== SUMMARY ===")
for r in results:
    print(f"{r['archive']}: {r['symlinks']} symlinks, {r['h5_symlinks']} H5 symlinks")
