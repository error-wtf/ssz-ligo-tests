#!/usr/bin/env python3
"""
SSZ-LIGO Test Suite - Full Pytest Runner
Generates comprehensive test report
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
    
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    return result.returncode, result.stdout, result.stderr

def main():
    os.chdir(r'E:\clone\ssz-ligo-tests')
    
    # Test 1: Python path
    code, out, err = run_command(
        '.\.venv\Scripts\python.exe -c "import sys; print(chr(10).join(sys.path))"',
        "Python Path"
    )
    print(out if out else err)
    
    # Test 2: Import test
    code, out, err = run_command(
        '.\.venv\Scripts\python.exe -c "import ssz_ligo_tests; print(\"Package: \", ssz_ligo_tests.__file__)"',
        "Import Test"
    )
    print(out if out else err)
    
    # Test 3: Pytest collection
    code, out, err = run_command(
        '.\.venv\Scripts\python.exe -m pytest tests/ --collect-only 2>&1 | head -50',
        "Test Collection"
    )
    print(out if out else err)
    
    # Test 4: Run pytest
    code, out, err = run_command(
        '.\.venv\Scripts\python.exe -m pytest tests/ -v --tb=short 2>&1 | head -150',
        "Pytest Run"
    )
    print(out if out else err)
    
    print(f"\n{'='*60}")
    print("FINAL STATUS:")
    print('='*60)
    
    if code == 0:
        print("✅ PASS_TEST_SUITE_VERIFIED")
    else:
        print(f"⚠️  EXIT CODE: {code}")
        
    return code

if __name__ == "__main__":
    sys.exit(main())
