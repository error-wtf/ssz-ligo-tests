#!/usr/bin/env python3
import sys, h5py
from pathlib import Path
BASE = Path(r'E:\clone\ssz-ligo-tests')
LIGO = Path(r'E:\clone\ligo-gw240925-gw250207-release\18600070')

# A. Environment
sys.path.insert(0, str(BASE / 'src'))
import ssz_ligo_tests as slt
print(f"IMPORT_OK: {slt.__file__}")
print(f"PHI={slt.PHI}")

# B. Pytest
import pytest
exit_code = pytest.main(['-ra', '-v', '--tb=short', 'tests/'])
print(f"PYTEST_EXIT={exit_code}")

# C. Real HDF5
files = [
    LIGO / 'GW240925_combinedPHM_envcalC01_metafile.hdf5',
    LIGO / 'GW250207_combinedPHM_cal_metafile.hdf5'
]
for f in files:
    if f.exists():
        with h5py.File(f, 'r') as h:
            print(f"OPEN_OK: {f.name}")
            print(f"GROUPS: {list(h.keys())}")
