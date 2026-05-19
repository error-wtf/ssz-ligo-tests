"""
PART B: Build Full Archive Member Index
Task: LIGO_PHASE_3C_SYMLINK_TARGET_RESOLUTION_AUDIT
"""
import tarfile
import csv
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("E:/clone/ligo-gw240925-gw250207-release/18600070")
INVENTORY_DIR = Path("E:/clone/ligo-gw240925-gw250207-release/02_INVENTORY")

archives = [
    "combined_samples.tar.gz",
    "fti.tar.gz", 
    "tiger.tar.gz",
    "ringdown.tar.gz",
    "qnmrf.tar.gz",
    "pca.tar.gz",
    "pseobnr.tar.gz",
    "residuals.tar.gz",
    "skymaps.tar.gz",
    "calibration.tar.gz",
    "cal_env.tar.gz",
    "notebook.tar.gz",
    "GW240925-C00-Strain.tar"
]

results = []

for arc_name in archives:
    arc_path = BASE_DIR / arc_name
    print(f"\n{'='*60}")
    print(f"Processing: {arc_name}")
    
    if not arc_path.exists():
        print(f"  MISSING: {arc_path}")
        results.append({
            'archive_name': arc_name,
            'member_path': 'ARCHIVE_NOT_FOUND',
            'member_type': 'N/A',
            'size': -1,
            'link_target': '',
            'basename': '',
            'extension': '',
            'normalized_basename': ''
        })
        continue
    
    try:
        # Handle .tar vs .tar.gz
        if arc_name.endswith('.tar.gz'):
            mode = 'r:gz'
        elif arc_name.endswith('.tar'):
            mode = 'r'
        else:
            mode = 'r'  # Try anyway
        
        with tarfile.open(arc_path, mode) as tar:
            members = tar.getmembers()
            print(f"  Total members: {len(members)}")
            
            for member in members:
                # Determine type
                if member.issym():
                    mtype = 'symlink'
                elif member.islnk():
                    mtype = 'hardlink'
                elif member.isdir():
                    mtype = 'directory'
                elif member.isfile():
                    mtype = 'regular'
                else:
                    mtype = 'other'
                
                # Get link target if applicable
                link_target = member.linkname if (member.issym() or member.islnk()) else ''
                
                # Get basename and extension
                basename = Path(member.name).name
                ext = Path(member.name).suffix.lower()
                
                # Normalized basename (for matching)
                norm_basename = basename.lower().replace('.hdf5', '').replace('.h5', '')
                
                results.append({
                    'archive_name': arc_name,
                    'member_path': member.name,
                    'member_type': mtype,
                    'size': member.size,
                    'link_target': link_target,
                    'basename': basename,
                    'extension': ext,
                    'normalized_basename': norm_basename
                })
            
            # Summary for this archive
            types = {}
            for r in results:
                if r['archive_name'] == arc_name:
                    t = r['member_type']
                    types[t] = types.get(t, 0) + 1
            
            print(f"  Types: {types}")
            
            # Count HDF5 files
            h5_count = sum(1 for r in results 
                          if r['archive_name'] == arc_name 
                          and r['extension'] in ['.hdf5', '.h5'])
            print(f"  HDF5/H5 files: {h5_count}")
            
    except Exception as e:
        print(f"  ERROR opening {arc_name}: {e}")
        results.append({
            'archive_name': arc_name,
            'member_path': f'ERROR: {e}',
            'member_type': 'ERROR',
            'size': -1,
            'link_target': '',
            'basename': '',
            'extension': '',
            'normalized_basename': ''
        })

# Write CSV
output_csv = INVENTORY_DIR / "ARCHIVE_MEMBER_INDEX.csv"
with open(output_csv, 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['archive_name', 'member_path', 'member_type', 'size', 
                  'link_target', 'basename', 'extension', 'normalized_basename']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in results:
        writer.writerow(r)

print(f"\n{'='*60}")
print(f"Archive member index complete: {output_csv}")
print(f"Total entries: {len(results)}")
