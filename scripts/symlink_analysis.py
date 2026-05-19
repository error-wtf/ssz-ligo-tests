"""
Symlink Forensics Analysis
Task ID: LIGO_PHASE_3B_BROKEN_SYMLINK_FORENSICS
"""
import csv
import os
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("E:/clone/ligo-gw240925-gw250207-release")
INVENTORY_DIR = BASE_DIR / "02_INVENTORY"
LOGS_DIR = BASE_DIR / "06_WINDSURF_LOGS"

def analyze_csv():
    csv_path = INVENTORY_DIR / "HDF5_SYMLINK_FORENSICS.csv"
    
    records = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    
    # Classify
    total = len(records)
    symlinks = [r for r in records if r.get('LinkType') == 'SymbolicLink']
    regular = [r for r in records if r.get('LinkType') != 'SymbolicLink']
    
    # Check symlink targets
    broken = []
    for link in symlinks:
        target = link.get('Target', '')
        # Check if target is Linux path
        is_linux_path = target.startswith('\\') or '/' in target
        link['is_linux_target'] = is_linux_path
        link['target_exists'] = 'UNKNOWN'
        broken.append(link)
    
    # Check accessible files
    accessible = []
    inaccessible = []
    for r in records:
        full_path = r.get('FullName', '')
        length_str = r.get('Length', '-1')
        try:
            length = int(length_str)
        except:
            length = -1
        
        # Check if file can be opened
        can_open = False
        error_msg = ""
        try:
            with open(full_path, 'rb') as f:
                f.read(1)
            can_open = True
        except Exception as e:
            error_msg = str(e)[:100]
        
        r['can_open'] = can_open
        r['open_error'] = error_msg
        
        if can_open and length > 0:
            accessible.append(r)
        else:
            inaccessible.append(r)
    
    return {
        'total': total,
        'symlinks': len(symlinks),
        'regular': len(regular),
        'accessible': len(accessible),
        'inaccessible': len(inaccessible),
        'broken_linux_links': len([b for b in broken if b.get('is_linux_target')]),
        'records': records
    }

if __name__ == "__main__":
    result = analyze_csv()
    print(f"Total HDF5-like paths: {result['total']}")
    print(f"Symlinks: {result['symlinks']}")
    print(f"Regular files: {result['regular']}")
    print(f"Accessible: {result['accessible']}")
    print(f"Inaccessible: {result['inaccessible']}")
    print(f"Broken Linux symlinks: {result['broken_linux_links']}")
