"""Test: Real LIGO HDF5 files open read-only.

Proves file path, groups, object count.
No physics interpretation — data access only.
"""
import pytest
import h5py
from pathlib import Path

H1_STRAIN = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW240925-C00-Strain\GW240925-C00-Strain"
    r"\O4b4DiscC00_4KHZ_R1\STRAIN_HDF\H1\1410334720"
    r"\H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
)

META_FILE = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW240925_combinedPHM_envcalC01_metafile.hdf5"
)

LIGO_ROOT = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
)

pytestmark = pytest.mark.skipif(
    not H1_STRAIN.exists(),
    reason="LIGO data not available at expected path"
)


class TestH1StrainFileAccess:
    def test_file_exists(self):
        assert H1_STRAIN.exists(), f"File not found: {H1_STRAIN}"

    def test_file_opens_readonly(self):
        with h5py.File(str(H1_STRAIN), 'r') as f:
            assert f is not None

    def test_strain_dataset_present(self):
        with h5py.File(str(H1_STRAIN), 'r') as f:
            assert "strain/Strain" in f

    def test_meta_gps_start_present(self):
        with h5py.File(str(H1_STRAIN), 'r') as f:
            assert "meta/GPSstart" in f

    def test_meta_duration_present(self):
        with h5py.File(str(H1_STRAIN), 'r') as f:
            assert "meta/Duration" in f

    def test_strain_dataset_nonzero(self):
        with h5py.File(str(H1_STRAIN), 'r') as f:
            n = f["strain/Strain"].shape[0]
        assert n > 0

    def test_group_count_reasonable(self):
        with h5py.File(str(H1_STRAIN), 'r') as f:
            groups = list(f.keys())
        assert len(groups) >= 2

    def test_gps_start_in_range(self):
        with h5py.File(str(H1_STRAIN), 'r') as f:
            gps0 = float(f["meta/GPSstart"][()])
        assert 1e9 < gps0 < 2e9

    def test_sample_rate_recoverable(self):
        with h5py.File(str(H1_STRAIN), 'r') as f:
            n = f["strain/Strain"].shape[0]
            dur = float(f["meta/Duration"][()])
        fs = int(n / dur)
        assert fs in (4096, 16384)


@pytest.mark.skipif(
    not META_FILE.exists(),
    reason="Metafile not available"
)
class TestMetaFileAccess:
    def test_metafile_opens_readonly(self):
        with h5py.File(str(META_FILE), 'r') as f:
            assert f is not None

    def test_metafile_has_groups(self):
        with h5py.File(str(META_FILE), 'r') as f:
            groups = list(f.keys())
        assert len(groups) >= 1
