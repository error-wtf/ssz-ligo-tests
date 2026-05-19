"""
PART C: Resolve Symlink Targets Against Archive Index
Task: LIGO_PHASE_3C_SYMLINK_TARGET_RESOLUTION_AUDIT
"""
import csv
from pathlib import Path
from datetime import datetime

INVENTORY_DIR = Path("E:/clone/ligo-gw240925-gw250207-release/02_INVENTORY")

# Read archive member index
archive_members = []
with open(INVENTORY_DIR / "ARCHIVE_MEMBER_INDEX.csv", 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        archive_members.append(row)

# Build lookup tables
# 1. By full member path
member_by_path = {r['member_path']: r for r in archive_members if r['member_path']}
# 2. By basename
members_by_basename = {}
for r in archive_members:
    bn = r['basename']
    if bn:
        if bn not in members_by_basename:
            members_by_basename[bn] = []
        members_by_basename[bn].append(r)
# 3. By normalized basename
members_by_norm = {}
for r in archive_members:
    nb = r['normalized_basename']
    if nb:
        if nb not in members_by_norm:
            members_by_norm[nb] = []
        members_by_norm[nb].append(r)

# Get all symlinks from archive
symlinks = [r for r in archive_members if r['member_type'] == 'symlink']
print(f"Total symlinks in archives: {len(symlinks)}")

# HDF5 symlinks only
h5_symlinks = [r for r in symlinks if r['extension'] in ['.hdf5', '.h5']]
print(f"HDF5/H5 symlinks: {len(h5_symlinks)}")

results = []

for idx, link in enumerate(h5_symlinks):
    source_path = link['member_path']
    target_path = link['link_target']
    archive = link['archive_name']
    
    print(f"\n[{idx+1}/{len(h5_symlinks)}] {source_path}")
    print(f"  Target: {target_path}")
    
    result = {
        'source_path': source_path,
        'source_archive': archive,
        'target_path': target_path,
        'target_basename': Path(target_path).name if target_path else '',
        'classification': 'UNKNOWN',
        'resolution_details': '',
        'target_in_release': 'UNKNOWN'
    }
    
    if not target_path:
        result['classification'] = 'NO_TARGET'
        result['resolution_details'] = 'Symlink has no target'
        results.append(result)
        print(f"  Classification: NO_TARGET")
        continue
    
    # Try exact match
    if target_path in member_by_path:
        target_member = member_by_path[target_path]
        result['classification'] = 'RESOLVED_EXACT'
        result['resolution_details'] = f"Exact match in {target_member['archive_name']}"
        result['target_in_release'] = 'YES'
        print(f"  Classification: RESOLVED_EXACT")
        results.append(result)
        continue
    
    # Try basename match
    target_basename = Path(target_path).name
    if target_basename in members_by_basename:
        candidates = members_by_basename[target_basename]
        if len(candidates) == 1:
            result['classification'] = 'RESOLVED_BASENAME_UNIQUE'
            result['resolution_details'] = f"Unique basename match: {candidates[0]['member_path']} in {candidates[0]['archive_name']}"
            result['target_in_release'] = 'YES'
            print(f"  Classification: RESOLVED_BASENAME_UNIQUE")
        else:
            result['classification'] = 'RESOLVED_BASENAME_AMBIGUOUS'
            paths = [c['member_path'] for c in candidates]
            result['resolution_details'] = f"Ambiguous: {len(candidates)} matches - {', '.join(paths[:3])}"
            result['target_in_release'] = 'MAYBE'
            print(f"  Classification: RESOLVED_BASENAME_AMBIGUOUS ({len(candidates)} candidates)")
        results.append(result)
        continue
    
    # Try normalized basename (without extension)
    norm_basename = target_basename.lower().replace('.hdf5', '').replace('.h5', '')
    if norm_basename in members_by_norm:
        candidates = members_by_norm[norm_basename]
        result['classification'] = 'RESOLVED_NORMALIZED'
        result['resolution_details'] = f"Normalized match: {len(candidates)} candidates"
        result['target_in_release'] = 'MAYBE'
        print(f"  Classification: RESOLVED_NORMALIZED ({len(candidates)} candidates)")
        results.append(result)
        continue
    
    # Check if target looks like external path
    if target_path.startswith('/home/') or target_path.startswith('/data/'):
        result['classification'] = 'TARGET_NOT_IN_RELEASE'
        result['resolution_details'] = f"Absolute external path: {target_path[:50]}..."
        result['target_in_release'] = 'NO'
        print(f"  Classification: TARGET_NOT_IN_RELEASE")
    else:
        result['classification'] = 'TARGET_UNRESOLVED'
        result['resolution_details'] = f"Cannot resolve: {target_path[:50]}..."
        result['target_in_release'] = 'UNKNOWN'
        print(f"  Classification: TARGET_UNRESOLVED")
    
    results.append(result)

# Write CSV
output_csv = INVENTORY_DIR / "HDF5_SYMLINK_TARGET_RESOLUTION.csv"
with open(output_csv, 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['source_path', 'source_archive', 'target_path', 'target_basename',
                  'classification', 'resolution_details', 'target_in_release']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in results:
        writer.writerow(r)

# Summary
print(f"\n{'='*60}")
print(f"SUMMARY:")
class_counts = {}
for r in results:
    c = r['classification']
    class_counts[c] = class_counts.get(c, 0) + 1

for cls, count in sorted(class_counts.items(), key=lambda x: -x[1]):
    print(f"  {cls}: {count}")

print(f"\nTotal resolved: {sum(1 for r in results if 'RESOLVED' in r['classification'])}")
print(f"Total not in release: {sum(1 for r in results if r['classification'] == 'TARGET_NOT_IN_RELEASE')}")
print(f"Output: {output_csv}")
