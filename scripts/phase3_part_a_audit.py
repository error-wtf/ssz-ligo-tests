#!/usr/bin/env python3
"""
PHASE 3 FORENSIC RECOVERY - PART A: AUDIT
Investigate why Phase 3 failed and what the actual state is
"""

import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path("E:/clone/ligo-gw240925-gw250207-release")
INVENTORY_DIR = ROOT / "02_INVENTORY"
LOGS_DIR = ROOT / "06_WINDSURF_LOGS"

LOGS_DIR.mkdir(parents=True, exist_ok=True)

audit_lines = []
def audit(msg):
    print(msg)
    audit_lines.append(f"{datetime.now().isoformat()} - {msg}")

audit("=" * 70)
audit("PHASE 3 FORENSIC AUDIT - PART A")
audit("=" * 70)

# 1. Check for running Python processes
audit("\n--- 1. RUNNING PROCESSES CHECK ---")
try:
    result = subprocess.run(
        ['powershell', '-Command',
         'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "phase3|hdf5|h5py|python" } | Select-Object ProcessId,Name,CommandLine | Format-Table -AutoSize'],
        capture_output=True, text=True, timeout=30
    )
    if result.stdout:
        audit("Running Python/Phase3 related processes:")
        for line in result.stdout.split('\n')[:20]:
            if line.strip():
                audit(f"  {line}")
    else:
        audit("  No phase3/hdf5 related Python processes found")
except Exception as e:
    audit(f"  Process check failed: {e}")

# 2. Locate Phase 3 scripts
audit("\n--- 2. PHASE 3 SCRIPTS SEARCH ---")
scripts_found = []
for pattern in ['phase3*.py', '*hdf5*.py', '*qnm*.py', '*readiness*.py']:
    for script in ROOT.glob(pattern):
        if script.is_file():
            stat = script.stat()
            size_kb = stat.st_size / 1024
            mod_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            # Check content
            try:
                with open(script, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()[:5000]
                    has_h5py = 'h5py' in content
                    has_output = 'HDF5_STRUCTURE_REPORT' in content
                    has_exception = 'try:' in content and 'except' in content
                    has_wrong_path = '01_EXTRACTED' in content and '18600070' not in content.replace('18600070', '')
            except:
                has_h5py = has_output = has_exception = has_wrong_path = False
            
            scripts_found.append({
                'path': script,
                'size_kb': size_kb,
                'mod_time': mod_time,
                'has_h5py': has_h5py,
                'has_output': has_output,
                'has_exception': has_exception,
                'has_wrong_path': has_wrong_path
            })
            
            audit(f"  {script.name}")
            audit(f"    Size: {size_kb:.1f} KB, Modified: {mod_time}")
            audit(f"    h5py import: {'YES' if has_h5py else 'NO'}")
            audit(f"    Output files: {'YES' if has_output else 'NO'}")
            audit(f"    Exception handling: {'YES' if has_exception else 'NO'}")
            if has_wrong_path:
                audit(f"    ⚠️  WARNING: May use wrong base path!")

if not scripts_found:
    audit("  No Phase 3 scripts found!")

# 3. Inspect stale/missing outputs
audit("\n--- 3. OUTPUT FILES INSPECTION ---")
expected_outputs = [
    (INVENTORY_DIR / "HDF5_STRUCTURE_REPORT.md", "HDF5 structure report"),
    (INVENTORY_DIR / "HDF5_STRUCTURE_SUMMARY.csv", "HDF5 CSV summary"),
    (INVENTORY_DIR / "QNM_RF_TEST_READINESS_REPORT.md", "QNM readiness report"),
    (LOGS_DIR / "PHASE_3_HDF5_QNM_READINESS_LOG.md", "Phase 3 log"),
]

for path, desc in expected_outputs:
    exists = path.exists()
    if exists:
        stat = path.stat()
        size_bytes = stat.st_size
        mod_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
        
        # Check if content is real or placeholder
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1000)
                is_placeholder = len(content) < 500 or 'generated' not in content.lower()
        except:
            is_placeholder = True
        
        status = "STALE/EMPTY" if is_placeholder else "OK"
        audit(f"  {desc}:")
        audit(f"    Path: {path}")
        audit(f"    Size: {size_bytes} bytes")
        audit(f"    Modified: {mod_time}")
        audit(f"    Status: {status}")
    else:
        audit(f"  {desc}: MISSING")
        audit(f"    Path: {path}")
        audit(f"    Status: NOT FOUND")

# 4. Check extraction roots
audit("\n--- 4. EXTRACTION ROOTS INSPECTION ---")
possible_roots = [
    ROOT / "01_EXTRACTED",
    ROOT / "01_EXTRACTED" / "1860070",
    ROOT / "01_EXTRACTED" / "18600070",
    ROOT / "01_EXTRACTED" / "nested",
    ROOT / "1860070",
    ROOT / "18600070",
]

found_roots = []
for root in possible_roots:
    exists = root.exists()
    if exists:
        try:
            items = list(root.iterdir())
            dirs = [d for d in items if d.is_dir()]
            files = [f for f in items if f.is_file()]
            
            # Check for archives
            tar_files = [f for f in files if f.suffix in ['.tar', '.gz'] or 'tar' in f.name]
            hdf5_files = list(root.rglob("*.hdf5")) if root.is_dir() else []
            
            found_roots.append({
                'path': root,
                'dirs': len(dirs),
                'files': len(files),
                'tar_files': len(tar_files),
                'hdf5_files': len(hdf5_files)
            })
            
            audit(f"  {root}")
            audit(f"    EXISTS: YES")
            audit(f"    Dirs: {len(dirs)}, Files: {len(files)}")
            audit(f"    Archive files: {len(tar_files)}")
            audit(f"    HDF5 files (recursive): {len(hdf5_files)}")
        except Exception as e:
            audit(f"  {root}: EXISTS but ERROR: {e}")
    else:
        audit(f"  {root}: DOES NOT EXIST")

if not found_roots:
    audit("  ⚠️  CRITICAL: No extraction roots found!")

# 5. Check Python environment
audit("\n--- 5. PYTHON ENVIRONMENT CHECK ---")
audit(f"  Python version: {sys.version}")
audit(f"  Python executable: {sys.executable}")

try:
    import h5py
    audit(f"  ✅ h5py: {h5py.__version__}")
    h5py_available = True
except ImportError:
    audit(f"  ❌ h5py: NOT INSTALLED")
    h5py_available = False

try:
    import numpy as np
    audit(f"  ✅ numpy: {np.__version__}")
except ImportError:
    audit(f"  ❌ numpy: NOT INSTALLED")

try:
    import pandas as pd
    audit(f"  ✅ pandas: {pd.__version__}")
except ImportError:
    audit(f"  ⚠️  pandas: NOT INSTALLED (CSV writing may be manual)")

# 6. Determine actual extraction location
audit("\n--- 6. ACTUAL EXTRACTION LOCATION ---")
if found_roots:
    # Pick the root with the most HDF5 files
    best_root = max(found_roots, key=lambda x: x['hdf5_files'])
    audit(f"  Best candidate: {best_root['path']}")
    audit(f"  HDF5 files found: {best_root['hdf5_files']}")
    actual_root = best_root['path']
else:
    audit("  No valid extraction root found!")
    actual_root = None

# 7. Root cause analysis
audit("\n--- 7. ROOT CAUSE ANALYSIS ---")

issues_found = []

if not h5py_available:
    issues_found.append("h5py not installed - HDF5 inspection BLOCKED")

if scripts_found:
    for script in scripts_found:
        if script['has_wrong_path']:
            issues_found.append(f"{script['path'].name} may use wrong base path")
        if not script['has_h5py']:
            issues_found.append(f"{script['path'].name} doesn't import h5py")

if not found_roots:
    issues_found.append("No extraction roots found - extraction may be incomplete")

# Check specific script
specific_script = ROOT / "phase3_verify_and_inspect.py"
if specific_script.exists():
    try:
        with open(specific_script, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Check for common issues
            if 'EXTRACTED_DIR = ROOT / "18600070"' in content:
                audit("  Script uses: EXTRACTED_DIR = ROOT / '18600070'")
                audit("  This looks CORRECT (user said files are here)")
            elif '01_EXTRACTED' in content and '18600070' not in content:
                audit("  ⚠️  Script may use wrong path: 01_EXTRACTED without 18600070")
                issues_found.append("Script path mismatch with actual extraction")
            
            if 'h5py' not in content:
                issues_found.append("Script doesn't use h5py - cannot inspect HDF5")
    except:
        pass

if issues_found:
    audit("\n  Issues identified:")
    for issue in issues_found:
        audit(f"    - {issue}")
else:
    audit("  No obvious issues found in scripts")

# 8. Can we proceed?
audit("\n--- 8. PROCEED ASSESSMENT ---")

can_proceed = True
blockers = []

if not h5py_available:
    blockers.append("h5py not installed")
    can_proceed = False

if not found_roots:
    blockers.append("No extraction roots found")
    can_proceed = False

if not actual_root:
    blockers.append("Cannot determine actual extraction location")
    can_proceed = False

if blockers:
    audit("  ❌ CANNOT PROCEED TO FULL PHASE 3:")
    for b in blockers:
        audit(f"    - {b}")
else:
    audit("  ✅ CAN PROCEED TO FULL PHASE 3")
    audit(f"  Using extraction root: {actual_root}")

# Write forensic audit report
audit_path = LOGS_DIR / "PHASE_3_FORENSIC_AUDIT_REPORT.md"
with open(audit_path, 'w', encoding='utf-8') as f:
    f.write("# Phase 3 Forensic Audit Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    
    f.write("## Summary\n\n")
    if can_proceed:
        f.write("✅ **CAN PROCEED** to full Phase 3 HDF5 inspection\n\n")
    else:
        f.write("❌ **BLOCKED** - Issues must be resolved first\n\n")
    
    f.write("## Findings\n\n")
    for line in audit_lines[1:]:  # Skip header
        if line.startswith('---'):
            f.write(f"\n### {line.strip('- ')}\n\n")
        elif line.startswith('  '):
            f.write(f"- {line.strip()}\n")
        else:
            f.write(f"{line}\n")
    
    f.write("\n## Conclusion\n\n")
    if can_proceed:
        f.write(f"Ready for full Phase 3 with extraction root: {actual_root}\n")
    else:
        f.write("Blocked. Resolve issues above before proceeding.\n")

audit(f"\n✅ Forensic Audit Report: {audit_path}")

audit("\n" + "=" * 70)
audit("PART A COMPLETE")
audit("=" * 70)

if can_proceed and actual_root:
    print(f"\n🔄 Proceeding to Part B: Full HDF5 Discovery")
    print(f"   Using root: {actual_root}")
    # Continue to Part B
    sys.exit(0)  # Success, can continue
else:
    print(f"\n⛔ STOPPED - Cannot proceed to Part B")
    print(f"   Resolve blockers first")
    sys.exit(1)  # Blocked
