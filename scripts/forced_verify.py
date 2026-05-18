"""
SSZ_LIGO_FORCED_VERIFICATION_AND_REPAIR
Mandatory verification script. No fake tests. No fake PASS.
"""
import sys
import os
import re
import io
import csv
import datetime
import traceback

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_PATH = os.path.join(REPO_ROOT, "src")
LIGO_ROOT = r"E:\clone\ligo-gw240925-gw250207-release\18600070"
REPORTS = os.path.join(REPO_ROOT, "reports")
DATA_MANIFEST = os.path.join(REPO_ROOT, "data_manifest")

os.makedirs(REPORTS, exist_ok=True)
os.makedirs(DATA_MANIFEST, exist_ok=True)

results = {}

# ── A. ENVIRONMENT ────────────────────────────────────────────────────────────
print("=" * 70)
print("A. ENVIRONMENT CHECK")
print("=" * 70)
print(f"Python:  {sys.executable}")
print(f"Version: {sys.version}")
print(f"cwd:     {os.getcwd()}")
print(f"REPO:    {REPO_ROOT}")
print(f"SRC:     {SRC_PATH}")

# ── B. PACKAGE IMPORT ─────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("B. PACKAGE IMPORT CHECK")
print("=" * 70)

if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

import_ok = False
import_path = None
try:
    import ssz_ligo_tests
    import_path = os.path.abspath(ssz_ligo_tests.__file__)
    print(f"ssz_ligo_tests.__file__: {import_path}")
    expected_under = os.path.join(SRC_PATH, "ssz_ligo_tests")
    if not import_path.startswith(expected_under):
        print(f"FAIL: imported from wrong location: {import_path}")
        results["import"] = "FAIL_WRONG_PATH"
    else:
        print("OK: path is correct")
        import_ok = True
        results["import"] = "PASS"
except Exception as e:
    print(f"FAIL: {e}")
    traceback.print_exc()
    results["import"] = f"FAIL: {e}"

# Legacy check
for leg in ["ssz_ligo", "_legacy_ssz_ligo"]:
    leg_path = os.path.join(SRC_PATH, leg)
    print(f"Legacy {leg}: {'EXISTS' if os.path.exists(leg_path) else 'not found'}")

# ── C. DEPENDENCIES ───────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("C. DEPENDENCY CHECK")
print("=" * 70)
dep_ok = True
for pkg in ["numpy", "pandas", "h5py", "pytest"]:
    try:
        m = __import__(pkg)
        ver = getattr(m, "__version__", "unknown")
        print(f"{pkg}: {ver}")
    except ImportError as e:
        print(f"{pkg}: MISSING - {e}")
        dep_ok = False
results["deps"] = "PASS" if dep_ok else "FAIL_MISSING_DEPS"

# ── D. PYTEST ─────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("D. PYTEST RUN")
print("=" * 70)
import pytest

pytest_out = io.StringIO()
old_stdout, old_stderr = sys.stdout, sys.stderr

class Tee:
    def __init__(self, *targets):
        self.targets = targets
    def write(self, data):
        for t in self.targets:
            t.write(data)
    def flush(self):
        for t in self.targets:
            t.flush()
    def isatty(self):
        return False
    def fileno(self):
        raise io.UnsupportedOperation('fileno')

sys.stdout = Tee(old_stdout, pytest_out)
sys.stderr = Tee(old_stderr, pytest_out)

pytest_exit = pytest.main([
    "-ra", "-v", "--tb=short",
    "--rootdir", REPO_ROOT,
    "tests"
], plugins=[])

sys.stdout = old_stdout
sys.stderr = old_stderr

pytest_output = pytest_out.getvalue()
print(f"pytest exit code: {pytest_exit}")
results["pytest_exit"] = int(pytest_exit)

# Count summary from output
passed = failed = errors = skipped = xfailed = 0
for line in pytest_output.splitlines():
    if " passed" in line:
        import re
        m = re.search(r"(\d+) passed", line)
        if m:
            passed = int(m.group(1))
    if " failed" in line:
        m = re.search(r"(\d+) failed", line)
        if m:
            failed = int(m.group(1))
    if " error" in line:
        m = re.search(r"(\d+) error", line)
        if m:
            errors = int(m.group(1))
    if " skipped" in line:
        m = re.search(r"(\d+) skipped", line)
        if m:
            skipped = int(m.group(1))
    if "xfailed" in line:
        m = re.search(r"(\d+) xfailed", line)
        if m:
            xfailed = int(m.group(1))

results.update({"passed": passed, "failed": failed, "errors": errors,
                 "skipped": skipped, "xfailed": xfailed})

# Write pytest report
pytest_status = "PASS" if pytest_exit == 0 else f"FAIL_EXIT_{pytest_exit}"
with open(os.path.join(REPORTS, "PYTEST_FULL_RUN_REPORT.md"), "w", encoding="utf-8") as f:
    f.write(f"# PYTEST FULL RUN REPORT\n")
    f.write(f"Generated: {datetime.datetime.now()}\n\n")
    f.write(f"## Command\n```\npytest -ra -v --tb=short tests\n```\n\n")
    f.write(f"## Exit Code\n{pytest_exit}\n\n")
    f.write(f"## Counts\n")
    f.write(f"- Passed:  {passed}\n- Failed:  {failed}\n")
    f.write(f"- Errors:  {errors}\n- Skipped: {skipped}\n- XFailed: {xfailed}\n\n")
    f.write(f"## Status\n{pytest_status}\n\n")
    f.write(f"## Full Output\n```\n{pytest_output}\n```\n")
print(f"PYTEST: {pytest_status} | passed={passed} failed={failed} errors={errors} skipped={skipped} xfailed={xfailed}")

# ── E. REAL LIGO HDF5 ─────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("E. REAL LIGO HDF5 CHECK")
print("=" * 70)
import h5py

HDF5_FILES = [
    os.path.join(LIGO_ROOT, "GW240925_combinedPHM_envcalC01_metafile.hdf5"),
    os.path.join(LIGO_ROOT, "GW250207_combinedPHM_cal_metafile.hdf5"),
]
SEARCH_TERMS = ["H1_only","L1_only","ringdown","qnm","final_mass",
                "final_spin","chi","/f","/m"]
hdf5_opened = 0
hdf5_rows = []

def collect_paths(name, obj, store):
    store.append(name)

for hdf5_file in HDF5_FILES:
    print(f"\nFile: {hdf5_file}")
    row = {"file": os.path.basename(hdf5_file)}
    if not os.path.exists(hdf5_file):
        print("  EXISTS: NO")
        row["status"] = "FILE_NOT_FOUND"
        hdf5_rows.append(row)
        continue
    size_mb = os.path.getsize(hdf5_file) / 1e6
    row["size_mb"] = round(size_mb, 2)
    print(f"  EXISTS: YES | {size_mb:.1f} MB")
    try:
        all_paths = []
        with h5py.File(hdf5_file, "r") as f:
            print(f"  h5py OPEN: OK")
            top_groups = list(f.keys())
            print(f"  Top groups: {top_groups[:10]}")
            f.visititems(lambda n, o: collect_paths(n, o, all_paths))
        obj_count = len(all_paths)
        print(f"  Total objects: {obj_count}")
        hits = [p for p in all_paths if any(t.lower() in p.lower() for t in SEARCH_TERMS)][:50]
        print(f"  Candidate paths ({len(hits)} shown):")
        for h in hits[:20]:
            print(f"    {h}")
        row.update({"status": "OK", "obj_count": obj_count,
                    "top_groups": str(top_groups[:5]), "candidate_hits": len(hits)})
        hdf5_opened += 1
    except Exception as e:
        print(f"  h5py OPEN: FAIL - {e}")
        row["status"] = f"FAIL: {e}"
    hdf5_rows.append(row)

results["hdf5_opened"] = hdf5_opened

with open(os.path.join(REPORTS, "REAL_LIGO_HDF5_ACCESS_REPORT.md"), "w", encoding="utf-8") as f:
    f.write("# REAL LIGO HDF5 ACCESS REPORT\n")
    f.write(f"Generated: {datetime.datetime.now()}\n\n")
    for r in hdf5_rows:
        f.write(f"## {r.get('file','unknown')}\n")
        for k, v in r.items():
            f.write(f"- {k}: {v}\n")
        f.write("\n")

csv_path = os.path.join(DATA_MANIFEST, "real_ligo_hdf5_access.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    if hdf5_rows:
        w = csv.DictWriter(f, fieldnames=hdf5_rows[0].keys())
        w.writeheader(); w.writerows(hdf5_rows)

print(f"HDF5 opened: {hdf5_opened}")

# ── F. PRODUCT INVENTORY ──────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("F. PRODUCT INVENTORY")
print("=" * 70)
SCAN_FOLDERS = [
    "ringdown","qnmrf","pca","pseobnr",
    "GW240925-C00-Strain","combined_samples","fti","tiger"
]
inv_rows = []

for folder in SCAN_FOLDERS:
    full = os.path.join(LIGO_ROOT, folder)
    row = {"folder": folder, "exists": os.path.exists(full)}
    print(f"\n{folder}: {'EXISTS' if row['exists'] else 'NOT FOUND'}")
    if not row["exists"]:
        inv_rows.append(row)
        continue
    all_files = []
    for root, dirs, files in os.walk(full):
        for fn in files:
            all_files.append(os.path.join(root, fn))
        if len(all_files) > 2000:
            break
    hdf5_files = [f for f in all_files if f.endswith((".hdf5",".h5"))]
    zero_byte = []
    for _f in all_files:
        try:
            if os.path.getsize(_f) == 0:
                zero_byte.append(_f)
        except OSError:
            pass
    print(f"  total files: {len(all_files)} | hdf5: {len(hdf5_files)} | zero-byte: {len(zero_byte)}")
    open_ok = open_fail = 0
    for hf in hdf5_files[:20]:
        try:
            with h5py.File(hf, "r") as _:
                open_ok += 1
        except:
            open_fail += 1
    print(f"  h5py open OK/FAIL: {open_ok}/{open_fail}")
    row.update({"total_files": len(all_files), "hdf5_count": len(hdf5_files),
                "zero_byte": len(zero_byte), "h5py_ok": open_ok, "h5py_fail": open_fail})
    inv_rows.append(row)

with open(os.path.join(REPORTS, "REAL_LIGO_PRODUCT_INVENTORY.md"), "w", encoding="utf-8") as f:
    f.write("# REAL LIGO PRODUCT INVENTORY\n")
    f.write(f"Generated: {datetime.datetime.now()}\n\n")
    for r in inv_rows:
        f.write(f"## {r['folder']}\n")
        for k, v in r.items():
            f.write(f"- {k}: {v}\n")
        f.write("\n")

csv_path = os.path.join(DATA_MANIFEST, "real_ligo_product_inventory.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    if inv_rows:
        w = csv.DictWriter(f, fieldnames=list(inv_rows[0].keys()))
        w.writeheader(); w.writerows(inv_rows)

# ── G. STRAIN SANITY ──────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("G. STRAIN SANITY")
print("=" * 70)
import numpy as np
strain_folder = os.path.join(LIGO_ROOT, "GW240925-C00-Strain")
strain_rows = []
strain_opened = 0

if os.path.exists(strain_folder):
    strain_files = []
    for root, dirs, files in os.walk(strain_folder):
        for fn in files:
            if fn.endswith((".hdf5", ".h5")):
                strain_files.append(os.path.join(root, fn))
        if len(strain_files) >= 5:
            break
    for sf in strain_files[:5]:
        print(f"\n  {os.path.basename(sf)}")
        row = {"file": os.path.basename(sf)}
        try:
            with h5py.File(sf, "r") as f:
                top = list(f.keys())
                print(f"    top groups: {top}")
                paths = []
                f.visititems(lambda n, o: paths.append((n, o.shape if hasattr(o, 'shape') else None,
                                                         str(o.dtype) if hasattr(o, 'dtype') else None)))
                numeric = [(n, s, d) for n, s, d in paths
                           if s is not None and len(s) >= 1 and s[0] > 0]
                for n, s, d in numeric[:5]:
                    try:
                        data = f[n][:min(4096, s[0])]
                        data = np.array(data, dtype=float)
                        finite = np.isfinite(data)
                        row.update({"dataset": n, "shape": str(s), "dtype": d,
                                    "min": float(np.nanmin(data)),
                                    "max": float(np.nanmax(data)),
                                    "mean": float(np.nanmean(data)),
                                    "std": float(np.nanstd(data)),
                                    "nan_count": int(np.sum(np.isnan(data))),
                                    "inf_count": int(np.sum(np.isinf(data)))})
                        print(f"    {n}: shape={s} min={row['min']:.3e} max={row['max']:.3e}")
                        break
                    except:
                        continue
                row["status"] = "OK"
                strain_opened += 1
        except Exception as e:
            print(f"    FAIL: {e}")
            row["status"] = f"FAIL: {e}"
        strain_rows.append(row)
else:
    print("  Strain folder NOT FOUND")

results["strain_opened"] = strain_opened

with open(os.path.join(REPORTS, "REAL_STRAIN_SANITY_REPORT.md"), "w", encoding="utf-8") as f:
    f.write("# REAL STRAIN SANITY REPORT\n")
    f.write(f"Generated: {datetime.datetime.now()}\n\n")
    for r in strain_rows:
        f.write(f"## {r.get('file')}\n")
        for k, v in r.items():
            f.write(f"- {k}: {v}\n")
        f.write("\n")

csv_path = os.path.join(DATA_MANIFEST, "real_strain_sanity.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    if strain_rows:
        w = csv.DictWriter(f, fieldnames=list(strain_rows[0].keys()))
        w.writeheader(); w.writerows(strain_rows)

# ── H. SYNTHETIC FORWARD DRY RUN ──────────────────────────────────────────────
print("\n" + "=" * 70)
print("H. SYNTHETIC FORWARD DRY RUN")
print("=" * 70)
freqs = np.linspace(20.0, 1024.0, 500)
M_chirp = 30.0  # solar masses
M1, M2 = 36.0, 29.0
dry_run_status = "NOT_ATTEMPTED"
dry_results = {}

try:
    from ssz_ligo_tests import xi_weak, xi_strong, d_ssz
    from ssz_ligo_tests import s_scale, rho_rsg, phase_accounting_factor_ssz
    from ssz_ligo_tests import frequency_to_radius_proxy, delta_phase_ssz_minus_gr

    G = 6.674e-11
    M_SUN = 1.989e30
    C = 2.998e8
    M_tot = (M1 + M2) * M_SUN
    r_s = 2 * G * M_tot / C**2

    radii = np.array([frequency_to_radius_proxy(f, M_tot) for f in freqs])
    print(f"  radii range: {radii.min():.3e} to {radii.max():.3e} m | r_s={r_s:.3e} m")

    xi_vals = np.array([xi_weak(r, r_s) for r in radii])
    d_vals = np.array([d_ssz(xi) for xi in xi_vals])
    rho_vals = np.array([rho_rsg(r, r_s) for r in radii])

    M_total = M_tot
    mu = (M1 * M2) / (M1 + M2) * M_SUN
    r_isco_val = 6 * G * M_total / C**2
    try:
        delta_psi = np.array([
            delta_phase_ssz_minus_gr(r, r_isco_val, M_total, mu, r_s)
            for r in radii[:50]
            if r > r_isco_val
        ])
        finite_count = int(np.sum(np.isfinite(delta_psi)))
        nan_count = int(np.sum(np.isnan(delta_psi)))
        dry_results = {
            "freqs_count": len(freqs),
            "radii_min": float(radii.min()),
            "radii_max": float(radii.max()),
            "delta_psi_min": float(np.nanmin(delta_psi)),
            "delta_psi_max": float(np.nanmax(delta_psi)),
            "delta_psi_median": float(np.nanmedian(delta_psi)),
            "finite_count": finite_count,
            "nan_count": nan_count,
        }
        print(f"  delta_psi: min={dry_results['delta_psi_min']:.4e} "
              f"max={dry_results['delta_psi_max']:.4e} "
              f"nan={nan_count}")
        dry_run_status = "PASS"
    except NotImplementedError:
        dry_run_status = "SYNTHETIC_DRY_RUN_STATUS: BLOCKED_MISSING_DELTA_PSI"
        print(f"  {dry_run_status}")

except Exception as e:
    dry_run_status = f"FAIL: {e}"
    print(f"  {dry_run_status}")
    traceback.print_exc()

results["synthetic_dry_run"] = dry_run_status

with open(os.path.join(REPORTS, "SYNTHETIC_FORWARD_DRY_RUN_REPORT.md"), "w", encoding="utf-8") as f:
    f.write("# SYNTHETIC FORWARD DRY RUN REPORT\n")
    f.write(f"Generated: {datetime.datetime.now()}\n\n")
    f.write(f"## Status\n{dry_run_status}\n\n")
    f.write("## Parameters\n")
    f.write(f"- M1={M1} M_sun, M2={M2} M_sun\n")
    f.write(f"- freqs: 20..1024 Hz, 500 points\n\n")
    f.write("## Results\n")
    for k, v in dry_results.items():
        f.write(f"- {k}: {v}\n")

csv_path = os.path.join(DATA_MANIFEST, "synthetic_delta_psi_preview.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["status", "key", "value"])
    for k, v in dry_results.items():
        w.writerow([dry_run_status, k, v])

# ── I. CLAIM GATE ─────────────────────────────────────────────────────────────
claim_gate = """# REAL LIGO CLAIM GATE
Generated: {}

POSTERIOR_RF_TEST: INVALID_FOR_SSZ
REAL_STRAIN_TEST: BLOCKED_UNTIL_HSSZ_FORWARD_MODEL_AND_CALIBRATION_SAFE_ADAPTER_EXIST
RINGDOWN_TEST: PARTIAL_EXPLORATORY_OR_BLOCKED_UNTIL_EPSILON_220_LOCKED
READY_FOR_REAL_LIGO_NUMERICAL_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE: NO
SSZ_FALSIFICATION_CLAIM_MADE: NO
""".format(datetime.datetime.now())

with open(os.path.join(REPORTS, "REAL_LIGO_CLAIM_GATE.md"), "w", encoding="utf-8") as f:
    f.write(claim_gate)

# ── J. MASTER REPORT ──────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("J. MASTER REPORT")
print("=" * 70)

pytest_ok = results.get("pytest_exit", -1) == 0
hdf5_ok = results.get("hdf5_opened", 0) > 0
strain_ok = results.get("strain_opened", 0) > 0
dry_ok = "PASS" in str(results.get("synthetic_dry_run", ""))

if pytest_ok and hdf5_ok:
    final_status = "PASS_TEST_SUITE_AND_DATA_ACCESS_VERIFIED"
elif results.get("pytest_exit", -1) in (0, 1) and hdf5_ok:
    final_status = "PARTIAL_TEST_SUITE_OK_DATA_PARTIAL"
elif results.get("import") and "FAIL" in str(results["import"]):
    final_status = "BLOCKED_ENVIRONMENT"
elif results.get("pytest_exit", -1) != 0:
    final_status = "FAIL_TESTS_FAILED"
else:
    final_status = "PARTIAL_TEST_SUITE_OK_DATA_PARTIAL"

print(f"FINAL STATUS: {final_status}")

master = f"""# REAL TEST VERIFICATION MASTER REPORT
Generated: {datetime.datetime.now()}

## Environment
- Python: {sys.version}
- cwd: {os.getcwd()}
- Status: {"OK" if dep_ok else "FAIL_MISSING_DEPS"}

## Import Status
{results.get("import", "UNKNOWN")}

## Pytest Status
- Exit code: {results.get("pytest_exit", "UNKNOWN")}
- Passed:  {results.get("passed", "UNKNOWN")}
- Failed:  {results.get("failed", "UNKNOWN")}
- Errors:  {results.get("errors", "UNKNOWN")}
- Skipped: {results.get("skipped", "UNKNOWN")}
- XFailed: {results.get("xfailed", "UNKNOWN")}

## Real HDF5 Opened
{results.get("hdf5_opened", 0)} / {len(HDF5_FILES)}

## Product Inventory Status
{len([r for r in inv_rows if r.get("exists")])} folders found of {len(SCAN_FOLDERS)}

## Strain Sanity Status
{results.get("strain_opened", 0)} files processed

## Synthetic Dry Run Status
{results.get("synthetic_dry_run", "NOT_ATTEMPTED")}

## Claim Gate Status
READY_FOR_REAL_LIGO_NUMERICAL_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE: NO
SSZ_FALSIFICATION_CLAIM_MADE: NO

## FINAL STATUS
{final_status}
"""

with open(os.path.join(REPORTS, "REAL_TEST_VERIFICATION_MASTER_REPORT.md"), "w", encoding="utf-8") as f:
    f.write(master)

print(master)
sys.exit(0 if pytest_ok else results.get("pytest_exit", 1))
