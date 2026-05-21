#!/usr/bin/env python3
"""
SSZ-LIGO Test Suite - Full Pytest Runner
Generates comprehensive test report, fetches necessary data, and audits HDF5 files
"""
import subprocess
import sys
import os


def run_command(cmd, description):
    """Run command and return output."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print('='*60)

    # Ensure ssz_ligo_tests is in PYTHONPATH
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath("src")

    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        env=env
    )

    return result.returncode, result.stdout, result.stderr


def main():
    os.chdir(r'E:\clone\ssz-ligo-tests')
    python_exe = sys.executable

    # Step 1: Fetch LIGO strain data
    code, out, err = run_command(
        f'"{python_exe}" scripts/fetch_data.py',
        "Fetch Data (Zenodo GW240925)"
    )
    print(out if out else err)
    if code != 0:
        print("[FAIL] Data fetching failed. Aborting further tests.")
        return code

    # Step 2: Run HDF5 Provenance Audit
    code, out, err = run_command(
        f'"{python_exe}" scripts/run_hdf5_provenance_audit.py',
        "HDF5 Provenance Audit"
    )
    print(out if out else err)
    if code != 0:
        print("[FAIL] HDF5 Provenance Audit failed. Aborting further tests.")
        return code

    # Test 3: Python path
    code, out, err = run_command(
        f'"{python_exe}" -c "import sys; print(chr(10).join(sys.path))"',
        "Python Path"
    )
    print(out if out else err)

    # Test 4: Import test
    import_test_cmd = (
        f'"{python_exe}" -c "import ssz_ligo_tests; '
        'print(\\\"Package:\\\", ssz_ligo_tests.__file__)"'
    )
    code, out, err = run_command(
        import_test_cmd,
        "Import Test"
    )
    print(out if out else err)

    # Test 5: Pytest collection
    code, out, err = run_command(
        f'"{python_exe}" -m pytest tests/ --collect-only',
        "Test Collection"
    )
    if out:
        # Show first 50 lines of collection output
        lines = out.splitlines()
        print("\n".join(lines[:50]))
        if len(lines) > 50:
            truncated = len(lines) - 50
            print(
                f"... [Truncated {truncated} lines of collection output] ..."
            )
    else:
        print(err)

    # Test 6: Run pytest
    code, out, err = run_command(
        f'"{python_exe}" -m pytest tests/ -v --tb=short',
        "Pytest Run"
    )
    if out:
        # Show first 150 lines of test output
        lines = out.splitlines()
        print("\n".join(lines[:150]))
        if len(lines) > 150:
            truncated = len(lines) - 150
            print(f"... [Truncated {truncated} lines of test run output] ...")
    else:
        print(err)

    print(f"\n{'='*60}")
    print("FINAL STATUS:")
    print('='*60)

    if code == 0:
        print("[OK] PASS_TEST_SUITE_VERIFIED")
    else:
        print(f"[WARN] EXIT CODE: {code}")

    return code


if __name__ == "__main__":
    sys.exit(main())
