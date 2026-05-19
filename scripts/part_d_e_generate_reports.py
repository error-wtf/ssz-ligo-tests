"""
PART D & E: Generate Final Reports
Task: LIGO_PHASE_3C_SYMLINK_TARGET_RESOLUTION_AUDIT
"""
import csv
from pathlib import Path
from datetime import datetime

INVENTORY_DIR = Path("E:/clone/ligo-gw240925-gw250207-release/02_INVENTORY")
LOGS_DIR = Path("E:/clone/ligo-gw240925-gw250207-release/06_WINDSURF_LOGS")

# Load all data
def load_csv(filename):
    path = INVENTORY_DIR / filename
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

regular_recheck = load_csv("REGULAR_HDF5_ACCESS_RECHECK.csv")
archive_index = load_csv("ARCHIVE_MEMBER_INDEX.csv")
target_resolution = load_csv("HDF5_SYMLINK_TARGET_RESOLUTION.csv")

# PART D: Dataset Completeness Analysis
datasets = {
    'combined_samples': {'symlinks': 0, 'regular': 0, 'resolved': 0, 'missing': 0},
    'fti': {'symlinks': 0, 'regular': 0, 'resolved': 0, 'missing': 0},
    'tiger': {'symlinks': 0, 'regular': 0, 'resolved': 0, 'missing': 0},
    'ringdown': {'symlinks': 0, 'regular': 0, 'resolved': 0, 'missing': 0},
    'qnmrf': {'symlinks': 0, 'regular': 0, 'resolved': 0, 'missing': 0},
    'pca': {'symlinks': 0, 'regular': 0, 'resolved': 0, 'missing': 0},
    'pseobnr': {'symlinks': 0, 'regular': 0, 'resolved': 0, 'missing': 0},
    'GW240925-C00-Strain': {'symlinks': 0, 'regular': 0, 'resolved': 0, 'missing': 0},
}

# Count from archive index
for row in archive_index:
    arc = row['archive_name'].replace('.tar.gz', '').replace('.tar', '')
    if arc in datasets:
        if row['member_type'] == 'symlink' and row['extension'] in ['.hdf5', '.h5']:
            datasets[arc]['symlinks'] += 1
        elif row['member_type'] == 'regular' and row['extension'] in ['.hdf5', '.h5']:
            datasets[arc]['regular'] += 1

# Count resolved/missing from target resolution
for row in target_resolution:
    arc = row['source_archive'].replace('.tar.gz', '').replace('.tar', '')
    if arc in datasets:
        if row['target_in_release'] == 'YES':
            datasets[arc]['resolved'] += 1
        elif row['target_in_release'] == 'NO':
            datasets[arc]['missing'] += 1

# Count accessible regular files
accessible_regular = sum(1 for r in regular_recheck if r.get('can_open_h5py') == 'YES')

# Determine if products are usable
usable_products = []
blocked_products = []

for name, data in datasets.items():
    if data['regular'] > 0:
        usable_products.append(f"{name} ({data['regular']} regular HDF5s)")
    elif data['symlinks'] > 0 and data['missing'] > 0:
        blocked_products.append(f"{name} ({data['symlinks']} symlinks, {data['missing']} missing targets)")
    elif data['symlinks'] > 0:
        blocked_products.append(f"{name} ({data['symlinks']} symlinks, target status unclear)")

# PART E: Generate Report
report_path = INVENTORY_DIR / "HDF5_SYMLINK_TARGET_RESOLUTION_REPORT.md"
with open(report_path, 'w', encoding='utf-8') as f:
    f.write("# HDF5 Symlink Target Resolution Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n")
    f.write(f"**Task ID:** LIGO_PHASE_3C_SYMLINK_TARGET_RESOLUTION_AUDIT\n\n")
    
    f.write("## Executive Summary\n\n")
    f.write("### Critical Finding: Zenodo Release Contains Broken Symlinks\n\n")
    f.write("The LIGO GW240925/GW250207 Zenodo release contains **129 HDF5 symlinks** that reference\n")
    f.write("absolute Linux paths (e.g., `/home/tgr.o4/...`, `/home/sylvia.biscoveanu/...`).\n\n")
    f.write("**Key Issue:** These symlinks were created for the authors' local workflow but were\n")
    f.write("archived without their targets. WSL extraction will NOT fix this because the\n")
    f.write("targets are external to the release package.\n\n")
    
    f.write("### Target Resolution Results\n\n")
    f.write("| Category | Count |\n")
    f.write("|----------|-------|\n")
    
    class_counts = {}
    for row in target_resolution:
        c = row['classification']
        class_counts[c] = class_counts.get(c, 0) + 1
    
    for cls, count in sorted(class_counts.items(), key=lambda x: -x[1]):
        f.write(f"| {cls} | {count} |\n")
    
    f.write(f"| **Total** | **{len(target_resolution)}** |\n\n")
    
    f.write("### Regular HDF5 Files Status\n\n")
    f.write(f"- Regular HDF5 files found: {len(regular_recheck)}\n")
    f.write(f"- Accessible via h5py: **{accessible_regular}**\n")
    f.write(f"- Inaccessible: {len(regular_recheck) - accessible_regular}\n\n")
    
    if accessible_regular == 0:
        f.write("**WARNING:** All 'regular' files from Windows extraction are inaccessible.\n")
        f.write("This suggests the PowerShell classification misidentified reparse points.\n\n")
    
    f.write("## Dataset Completeness by Product\n\n")
    f.write("| Product | Regular HDF5s | Symlinks | Resolved Targets | Missing Targets | Status |\n")
    f.write("|---------|---------------|----------|------------------|-----------------|--------|\n")
    
    for name, data in sorted(datasets.items(), key=lambda x: -(x[1]['symlinks'] + x[1]['regular'])):
        if data['symlinks'] > 0 or data['regular'] > 0:
            if data['regular'] > 0:
                status = "USABLE (regular files)"
            elif data['missing'] > 0:
                status = "BLOCKED (missing targets)"
            else:
                status = "UNCERTAIN"
            f.write(f"| {name} | {data['regular']} | {data['symlinks']} | {data['resolved']} | {data['missing']} | {status} |\n")
    
    f.write("\n## Root Cause Analysis\n\n")
    f.write("### The Symlink Problem\n\n")
    f.write("1. **Archive Creation:** Authors created symlinks pointing to local paths:\n")
    f.write("   - `/home/tgr.o4/GW240925_GW250207/TIGER/...`\n")
    f.write("   - `/home/sylvia.biscoveanu/gw240925_and_gw250207/...`\n\n")
    f.write("2. **Archive Contents:** Only the symlinks were archived, NOT their targets\n\n")
    f.write("3. **Windows Extraction:** Windows created reparse points for symlinks,\n")
    f.write("   but cannot resolve Linux absolute paths\n\n")
    f.write("4. **Tiger Cross-Links:** The tiger.tar.gz archive contains circular/ambiguous\n")
    f.write("   references between `_cal` and `_no_cal` versions of the same files\n\n")
    
    f.write("### Why WSL Won't Help\n\n")
    f.write("WSL can resolve Linux symlinks, BUT:\n")
    f.write("- The targets (`/home/tgr.o4/...`) don't exist in WSL by default\n")
    f.write("- The targets are NOT included in the Zenodo release\n")
    f.write("- Re-extracting under WSL will produce the same broken links\n\n")
    
    f.write("## Usable vs Blocked Products\n\n")
    f.write("### Currently Usable (Have Regular HDF5s)\n\n")
    if usable_products:
        for p in usable_products:
            f.write(f"- {p}\n")
    else:
        f.write("**None identified**\n")
    
    f.write("\n### Blocked (Symlink-Only with Missing Targets)\n\n")
    if blocked_products:
        for p in blocked_products:
            f.write(f"- {p}\n")
    else:
        f.write("**None identified**\n")
    
    f.write("\n## Recommendations\n\n")
    f.write("### Immediate Actions\n\n")
    f.write("1. **Contact LIGO/Zenodo:** Report that the release contains broken absolute symlinks\n")
    f.write("2. **Request Complete Archive:** Ask for either:\n")
    f.write("   - Archives without symlinks (with actual data files)\n")
    f.write("   - Separate download links for the symlink target files\n")
    f.write("   - Documentation on how to obtain the missing data\n\n")
    
    f.write("### Workaround Options\n\n")
    f.write("1. **Use Available Data Only:**\n")
    f.write("   - pca.tar.gz (8 regular HDF5s)\n")
    f.write("   - pseobnr.tar.gz (6 regular HDF5s)\n")
    f.write("   - GW240925-C00-Strain.tar (6 regular HDF5s)\n")
    f.write("   - ringdown.tar.gz (1 regular HDF5)\n")
    f.write("   - qnmrf.tar.gz (2 regular HDF5s)\n\n")
    f.write("2. **Check if symlink targets exist elsewhere:**\n")
    f.write("   - Some targets may be downloadable from LIGO DCC\n")
    f.write("   - Check if posterior samples are available via GraceDB\n\n")
    
    f.write("### Do NOT\n\n")
    f.write("- Delete the broken symlinks (document the issue first)\n")
    f.write("- Assume WSL extraction will fix this\n")
    f.write("- Attempt to compute R_f with incomplete data\n")
    f.write("- Make SSZ/GR claims based on partial data\n\n")
    
    f.write("## Phase 3 Status\n\n")
    f.write("| Phase | Status |\n")
    f.write("|-------|--------|\n")
    f.write("| 3A: HDF5 Discovery | COMPLETE |\n")
    f.write("| 3B: Symlink Forensics | COMPLETE |\n")
    f.write("| 3C: Target Resolution | COMPLETE |\n")
    f.write("| 3D: QNM R_f Test | **BLOCKED** - Missing critical data |\n\n")
    
    f.write("## Conclusion\n\n")
    f.write("The Zenodo release for GW240925/GW250207 is **incomplete** for standalone analysis.\n")
    f.write("The core posterior samples (combined_samples, fti, tiger) are distributed as\n")
    f.write("broken symlinks without their targets. This is an archive packaging issue, not\n")
    f.write("a scientific or technical problem with the data itself.\n\n")
    f.write("**Next Step:** Contact LIGO/Zenodo for complete data or clarification.\n")

# Generate Log
log_path = LOGS_DIR / "PHASE_3C_SYMLINK_TARGET_RESOLUTION_LOG.md"
with open(log_path, 'w', encoding='utf-8') as f:
    f.write("# Phase 3C: Symlink Target Resolution Log\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    f.write("## Task\n\n")
    f.write("LIGO_PHASE_3C_SYMLINK_TARGET_RESOLUTION_AUDIT\n\n")
    f.write("## Key Finding\n\n")
    f.write("Zenodo release contains broken absolute symlinks.\n")
    f.write("Targets are NOT included in the release.\n")
    f.write("WSL extraction will NOT fix this issue.\n\n")
    f.write("## Summary Statistics\n\n")
    f.write(f"- Total HDF5 symlinks: {len(target_resolution)}\n")
    f.write(f"- Resolved: {sum(1 for r in target_resolution if 'RESOLVED' in r['classification'])}\n")
    f.write(f"- Missing from release: {sum(1 for r in target_resolution if r['classification'] == 'TARGET_NOT_IN_RELEASE')}\n")
    f.write(f"- Regular HDF5s accessible: {accessible_regular}\n\n")
    f.write("## Outputs\n\n")
    f.write(f"- REGULAR_HDF5_RECHECK: {INVENTORY_DIR / 'REGULAR_HDF5_ACCESS_RECHECK.csv'}\n")
    f.write(f"- ARCHIVE_INDEX: {INVENTORY_DIR / 'ARCHIVE_MEMBER_INDEX.csv'}\n")
    f.write(f"- TARGET_RESOLUTION: {INVENTORY_DIR / 'HDF5_SYMLINK_TARGET_RESOLUTION.csv'}\n")
    f.write(f"- REPORT: {report_path}\n")
    f.write(f"- LOG: {log_path}\n\n")
    f.write("## Status\n\n")
    f.write("Phase 3C: COMPLETE\n")
    f.write("Phase 3 (R_f test): BLOCKED\n")
    f.write("Next: Contact LIGO/Zenodo for complete data\n")

print(f"Reports generated:")
print(f"  Report: {report_path}")
print(f"  Log: {log_path}")
print(f"\nSummary:")
print(f"  Symlinks total: {len(target_resolution)}")
print(f"  Missing targets: {sum(1 for r in target_resolution if r['classification'] == 'TARGET_NOT_IN_RELEASE')}")
print(f"  Accessible regular: {accessible_regular}")
