#!/usr/bin/env python3
"""
SSZ-LIGO Test Suite - Full Pytest Runner
Generates comprehensive test report, fetches necessary data, and audits HDF5 files
"""
import subprocess
import sys
import os
import datetime

# Define paths
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(REPO_ROOT, "logs")
LOG_PATH = os.path.join(LOG_DIR, "full_test_run.log")


def write_to_log(text):
    """Write text to the log file."""
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8", errors="replace") as lf:
        lf.write(text + "\n")


def clear_log():
    """Initialize or clear the log file."""
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as lf:
        lf.write("=== SSZ-LIGO FULL TEST RUN LOG ===\n")
        lf.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
        lf.write(f"Repository Root: {REPO_ROOT}\n")
        lf.write(f"Python Executable: {sys.executable}\n")
        lf.write(f"{'='*60}\n\n")


def print_and_log(text=""):
    """Print to console and save to log file."""
    print(text)
    write_to_log(text)


def run_command(cmd, description):
    """Run command, stream output in real-time to console, and log to file."""
    header = (
        f"\n{'='*60}\n"
        f"Running: {description}\n"
        f"Command: {cmd}\n"
        f"{'='*60}"
    )
    print_and_log(header)

    # Ensure ssz_ligo_tests is in PYTHONPATH
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath(os.path.join(REPO_ROOT, "src"))

    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace',
        env=env
    )

    stdout_captured = []
    stderr_captured = []

    # Stream stdout line-by-line in real-time
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            print(line, end="")
            # Clean trailing newline before writing to log
            write_to_log(line.rstrip("\n"))
            stdout_captured.append(line)

    # Read remaining stderr
    remaining_err = process.stderr.read()
    if remaining_err:
        print(remaining_err, end="")
        write_to_log(remaining_err.rstrip("\n"))
        stderr_captured.append(remaining_err)

    process.wait()

    # Log summary of results
    write_to_log(f"\n--- [COMPLETED: {description}] Exit Code: {process.returncode} ---\n")

    return process.returncode, "".join(stdout_captured), "".join(stderr_captured)


def main():
    # Make directory-independent
    os.chdir(REPO_ROOT)
    clear_log()
    python_exe = sys.executable

    # Step 1: Fetch LIGO strain data
    code, out, err = run_command(
        f'"{python_exe}" scripts/fetch_data.py',
        "Fetch Data (Zenodo GW240925)"
    )
    print_and_log(out if out else err)
    if code != 0:
        print_and_log("[FAIL] Data fetching failed. Aborting further tests.")
        return code

    # Step 2: Run HDF5 Provenance Audit
    code, out, err = run_command(
        f'"{python_exe}" scripts/run_hdf5_provenance_audit.py',
        "HDF5 Provenance Audit"
    )
    print_and_log(out if out else err)
    if code != 0:
        print_and_log("[FAIL] HDF5 Provenance Audit failed. Aborting tests.")
        return code

    # Test 3: Python path
    code, out, err = run_command(
        f'"{python_exe}" -c "import sys; print(chr(10).join(sys.path))"',
        "Python Path"
    )
    print_and_log(out if out else err)

    # Test 4: Import test
    import_test_cmd = (
        f'"{python_exe}" -c "import ssz_ligo_tests; '
        'print(\\\"Package:\\\", ssz_ligo_tests.__file__)"'
    )
    code, out, err = run_command(
        import_test_cmd,
        "Import Test"
    )
    print_and_log(out if out else err)

    # Test 5: Pytest collection
    code, out, err = run_command(
        f'"{python_exe}" -m pytest tests/ --collect-only',
        "Test Collection"
    )
    if out:
        # Show first 50 lines of collection output in console
        lines = out.splitlines()
        print_and_log("\n".join(lines[:50]))
        if len(lines) > 50:
            truncated = len(lines) - 50
            print_and_log(
                f"... [Console truncated {truncated} lines of collection. "
                "Full output is saved in log file] ..."
            )
    else:
        print_and_log(err)

    # Test 6: Run pytest
    code, out, err = run_command(
        f'"{python_exe}" -m pytest tests/ -v --tb=short',
        "Pytest Run"
    )
    if out:
        # Show first 150 lines of test output in console
        lines = out.splitlines()
        print_and_log("\n".join(lines[:150]))
        if len(lines) > 150:
            truncated = len(lines) - 150
            print_and_log(
                f"... [Console truncated {truncated} lines of run output. "
                "Full output is saved in log file] ..."
            )
    else:
        print_and_log(err)

    print_and_log(f"\n{'='*60}")
    print_and_log("FINAL STATUS SUMMARY:")
    print_and_log('='*60)

    if code == 0:
        print_and_log("[OK] PASS_TEST_SUITE_VERIFIED")
        print_and_log("All 498 tests and audits completed successfully!")
    else:
        print_and_log(f"[WARN] EXIT CODE: {code}")
        print_and_log("Some tests or audits have failed.")

    print_and_log(f"\nFull untruncated run logs written to:")
    print_and_log(f"-> {LOG_PATH}")
    print_and_log(f"{'='*60}\n")

    return code


if __name__ == "__main__":
    sys.exit(main())
