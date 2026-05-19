#!/usr/bin/env python3
"""
Phase 3E: FULL RECURSIVE RELEASE SCAN - ALL SUBFOLDERS
Task ID: LIGO_PHASE_3E_FULL_RECURSIVE_RELEASE_SCAN_ALL_SUBFOLDERS
"""
import os
import csv
import h5py
import tarfile
from pathlib import Path
from datetime import datetime

# KONFIGURATION
PRIMARY_ROOT = Path("E:/clone/ligo-gw240925-gw250207-release/18600070")
OUTPUT_DIR = Path("E:/clone/ligo-gw240925-gw250207-release/02_INVENTORY")
LOGS_DIR = Path("E:/clone/ligo-gw240925-gw250207-release/06_WINDSURF_LOGS")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

START_TIME = datetime.now()

def classify_file(path, ext):
    """Klassifiziere Datei nach Typ"""
    name_lower = path.name.lower()
    path_str = str(path).lower()
    
    if ext in ['.hdf5', '.h5', '.hdf']:
        return 'HDF5/H5 data'
    elif ext in ['.tar', '.gz', '.tgz', '.zip']:
        return 'archive'
    elif ext == '.ipynb':
        return 'notebook'
    elif ext == '.py':
        return 'Python script'
    elif ext in ['.sh', '.bash']:
        return 'shell script'
    elif ext in ['.json', '.yaml', '.yml', '.ini', '.cfg']:
        return 'config'
    elif ext in ['.txt', '.md', '.rst']:
        return 'documentation'
    elif ext in ['.pdf', '.png', '.svg', '.jpg', '.jpeg']:
        return 'figure/plot'
    elif 'gwosc' in path_str or 'strain' in path_str:
        return 'strain/GWOSC'
    elif 'calibrat' in path_str:
        return 'calibration'
    elif 'posterior' in path_str or 'samples' in path_str:
        return 'posterior sample'
    elif 'ringdown' in path_str or 'qnm' in path_str:
        return 'ringdown/QNM'
    elif 'pca' in path_str:
        return 'PCA'
    elif 'pseobnr' in path_str:
        return 'PSEOBNR'
    elif 'fti' in path_str:
        return 'FTI'
    elif 'tiger' in path_str:
        return 'TIGER'
    elif 'residual' in path_str:
        return 'residual'
    elif 'skymap' in path_str:
        return 'skymap'
    else:
        return 'unknown'

print("="*80)
print("PHASE 3E: FULL RECURSIVE RELEASE SCAN")
print("="*80)
print(f"Start: {START_TIME}")
print(f"Root: {PRIMARY_ROOT}")
print()

# ============================================================================
# PHASE A: FULL FILESYSTEM WALK
# ============================================================================
print("[PHASE A] Full filesystem walk...")

all_entries = []
entry_count = 0
dir_count = 0
file_count = 0

for root, dirs, files in os.walk(PRIMARY_ROOT):
    root_path = Path(root)
    
    # Verzeichnisse
    for d in dirs:
        full_path = root_path / d
        rel_path = full_path.relative_to(PRIMARY_ROOT)
        try:
            stat = full_path.stat()
            all_entries.append({
                'full_path': str(full_path),
                'relative_path': str(rel_path),
                'parent': str(rel_path.parent) if str(rel_path.parent) != '.' else '',
                'filename': d,
                'extension': '',
                'entry_type': 'directory',
                'size_bytes': 0,
                'size_mb': 0,
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'attributes': '',
                'link_target': '',
                'link_target_exists': '',
                'byte_open_ok': '',
                'byte_open_error': '',
                'category': 'directory',
                'notes': ''
            })
            dir_count += 1
            entry_count += 1
        except Exception as e:
            all_entries.append({
                'full_path': str(full_path),
                'relative_path': str(rel_path),
                'parent': str(rel_path.parent) if str(rel_path.parent) != '.' else '',
                'filename': d,
                'extension': '',
                'entry_type': 'directory',
                'size_bytes': 0,
                'size_mb': 0,
                'modified_time': '',
                'attributes': '',
                'link_target': '',
                'link_target_exists': '',
                'byte_open_ok': 'NO',
                'byte_open_error': str(e)[:100],
                'category': 'directory',
                'notes': 'stat_error'
            })
            dir_count += 1
            entry_count += 1
    
    # Dateien
    for f in files:
        full_path = root_path / f
        rel_path = full_path.relative_to(PRIMARY_ROOT)
        
        # Extension
        ext = full_path.suffix.lower()
        
        # Entry type detection
        entry_type = 'regular_file'
        link_target = ''
        link_target_exists = ''
        
        try:
            if full_path.is_symlink():
                entry_type = 'symlink'
                try:
                    link_target = str(full_path.readlink())
                    # Check if target exists
                    if os.path.isabs(link_target):
                        link_target_exists = os.path.exists(link_target)
                    else:
                        target_full = (full_path.parent / link_target).resolve()
                        link_target_exists = target_full.exists()
                except:
                    link_target = 'UNREADABLE'
        except:
            pass
        
        # Size und modified
        try:
            stat = full_path.stat()
            size_bytes = stat.st_size
            size_mb = round(size_bytes / 1024 / 1024, 2)
            mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()
        except Exception as e:
            size_bytes = -1
            size_mb = -1
            mtime = ''
        
        # Byte-open test
        byte_open_ok = ''
        byte_open_error = ''
        if entry_type == 'regular_file':
            try:
                with open(full_path, 'rb') as bf:
                    header = bf.read(16)
                    byte_open_ok = 'YES'
            except Exception as e:
                byte_open_ok = 'NO'
                byte_open_error = str(e)[:100]
        
        # Kategorie
        category = classify_file(full_path, ext)
        
        all_entries.append({
            'full_path': str(full_path),
            'relative_path': str(rel_path),
            'parent': str(rel_path.parent) if str(rel_path.parent) != '.' else '',
            'filename': f,
            'extension': ext,
            'entry_type': entry_type,
            'size_bytes': size_bytes,
            'size_mb': size_mb,
            'modified_time': mtime,
            'attributes': '',
            'link_target': link_target,
            'link_target_exists': str(link_target_exists),
            'byte_open_ok': byte_open_ok,
            'byte_open_error': byte_open_error,
            'category': category,
            'notes': ''
        })
        file_count += 1
        entry_count += 1
    
    if entry_count % 1000 == 0:
        print(f"  ... {entry_count} entries scanned")

print(f"[A] Complete: {dir_count} directories, {file_count} files, {entry_count} total")

# Speichere Phase A
print("[A] Saving file inventory...")
with open(OUTPUT_DIR / "FULL_RECURSIVE_RELEASE_FILE_INVENTORY.csv", 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['full_path', 'relative_path', 'parent', 'filename', 'extension', 
                  'entry_type', 'size_bytes', 'size_mb', 'modified_time', 'attributes',
                  'link_target', 'link_target_exists', 'byte_open_ok', 'byte_open_error',
                  'category', 'notes']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for e in all_entries:
        writer.writerow({k: e.get(k, '') for k in fieldnames})

print(f"  Saved: {OUTPUT_DIR / 'FULL_RECURSIVE_RELEASE_FILE_INVENTORY.csv'}")

# ============================================================================
# PHASE C: HDF5 ACCESS CHECK
# ============================================================================
print("\n[PHASE C] HDF5 access check for ALL HDF5 files...")

hdf5_entries = [e for e in all_entries if e['category'] == 'HDF5/H5 data']
print(f"[C] Found {len(hdf5_entries)} HDF5-like entries")

hdf5_results = []
hdf5_accessible = 0
hdf5_inaccessible = 0
symlink_count = 0

for idx, h5 in enumerate(hdf5_entries, 1):
    full_path = Path(h5['full_path'])
    rel_path = h5['relative_path']
    
    if idx <= 10 or idx % 50 == 0 or idx == len(hdf5_entries):
        print(f"  [{idx}/{len(hdf5_entries)}] {rel_path[:60]}")
    
    result = {
        'full_path': str(full_path),
        'relative_path': rel_path,
        'entry_type': h5['entry_type'],
        'link_target': h5['link_target'],
        'h5py_open_ok': False,
        'h5py_error': '',
        'top_level_groups': '',
        'object_count': 0,
        'dataset_count': 0,
        'group_count': 0,
        'classification': '',
        'basename_matches_elsewhere': '',
        'resolved_target_path': '',
        'notes': ''
    }
    
    # Skip symlinks
    if h5['entry_type'] == 'symlink':
        result['classification'] = 'SYMLINK'
        hdf5_results.append(result)
        hdf5_inaccessible += 1
        symlink_count += 1
        continue
    
    # Try h5py
    try:
        with h5py.File(full_path, 'r') as f:
            result['h5py_open_ok'] = True
            hdf5_accessible += 1
            
            # Top-level
            top = list(f.keys())
            result['top_level_groups'] = ';'.join(top[:20])
            
            # Count
            datasets = []
            groups = []
            def count_objects(name, obj):
                if isinstance(obj, h5py.Dataset):
                    datasets.append(name)
                elif isinstance(obj, h5py.Group):
                    groups.append(name)
            f.visititems(count_objects)
            
            result['dataset_count'] = len(datasets)
            result['group_count'] = len(groups)
            result['object_count'] = len(datasets) + len(groups)
            result['classification'] = 'REAL_HDF5_OK'
            
    except Exception as e:
        result['h5py_error'] = str(e)[:200]
        result['classification'] = 'HDF5_ERROR'
        hdf5_inaccessible += 1
    
    hdf5_results.append(result)

print(f"[C] Results: {hdf5_accessible} accessible, {hdf5_inaccessible} inaccessible ({symlink_count} symlinks)")

# Speichere Phase C
print("[C] Saving HDF5 access report...")
with open(OUTPUT_DIR / "FULL_RECURSIVE_HDF5_ACCESS_REPORT.csv", 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['full_path', 'relative_path', 'entry_type', 'link_target', 'h5py_open_ok',
                  'h5py_error', 'top_level_groups', 'object_count', 'dataset_count', 'group_count',
                  'classification', 'basename_matches_elsewhere', 'resolved_target_path', 'notes']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in hdf5_results:
        writer.writerow({k: r.get(k, '') for k in fieldnames})

print(f"  Saved: {OUTPUT_DIR / 'FULL_RECURSIVE_HDF5_ACCESS_REPORT.csv'}")

# ============================================================================
# PHASE F: PRODUCT COMPLETENESS MAP (vereinfacht)
# ============================================================================
print("\n[PHASE F] Product completeness map...")

# Finde alle Top-Level Ordner
top_folders = [e for e in all_entries 
               if e['entry_type'] == 'directory' and e['parent'] == '']

product_summary = []
for folder in top_folders:
    folder_name = folder['filename']
    folder_entries = [e for e in all_entries if e['parent'].startswith(folder_name) or e['parent'] == folder_name]
    
    files_in_folder = [e for e in folder_entries if e['entry_type'] != 'directory']
    hdf5_in_folder = [e for e in files_in_folder if e['category'] == 'HDF5/H5 data']
    accessible_hdf5 = sum(1 for e in hdf5_in_folder if e['entry_type'] != 'symlink')
    
    product_summary.append({
        'folder': folder_name,
        'total_entries': len(folder_entries),
        'total_files': len(files_in_folder),
        'hdf5_files': len(hdf5_in_folder),
        'accessible_hdf5': accessible_hdf5,
        'status': 'OK' if accessible_hdf5 > 0 else 'CHECK'
    })

# Speichere als Markdown
with open(OUTPUT_DIR / "FULL_PRODUCT_COMPLETENESS_MAP.md", 'w', encoding='utf-8') as f:
    f.write("# Product Completeness Map\n\n")
    f.write(f"Generated: {datetime.now().isoformat()}\n\n")
    f.write("| Product Folder | Total Files | HDF5 Files | Accessible | Status |\n")
    f.write("|----------------|-------------|------------|--------------|--------|\n")
    for p in sorted(product_summary, key=lambda x: -x['accessible_hdf5']):
        f.write(f"| {p['folder']:<20} | {p['total_files']:>11} | {p['hdf5_files']:>10} | {p['accessible_hdf5']:>12} | {p['status']:<6} |\n")

print(f"  Saved: {OUTPUT_DIR / 'FULL_PRODUCT_COMPLETENESS_MAP.md'}")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
END_TIME = datetime.now()
duration = (END_TIME - START_TIME).total_seconds()

print("\n" + "="*80)
print("PHASE 3E COMPLETE")
print("="*80)
print(f"Duration: {duration:.1f} seconds")
print(f"Total directories: {dir_count}")
print(f"Total files: {file_count}")
print(f"Total entries: {entry_count}")
print(f"\nHDF5 files found: {len(hdf5_entries)}")
print(f"  - Accessible: {hdf5_accessible}")
print(f"  - Inaccessible: {hdf5_inaccessible}")
print(f"  - Symlinks: {symlink_count}")

print(f"\nProducts with accessible HDF5:")
for p in sorted(product_summary, key=lambda x: -x['accessible_hdf5']):
    if p['accessible_hdf5'] > 0:
        print(f"  {p['folder']}: {p['accessible_hdf5']} files")

print("\n" + "="*80)
print("OUTPUTS:")
print(f"  1. {OUTPUT_DIR / 'FULL_RECURSIVE_RELEASE_FILE_INVENTORY.csv'}")
print(f"  2. {OUTPUT_DIR / 'FULL_RECURSIVE_HDF5_ACCESS_REPORT.csv'}")
print(f"  3. {OUTPUT_DIR / 'FULL_PRODUCT_COMPLETENESS_MAP.md'}")
print("="*80)
