"""Test: Bounded strain segment — finite values, no physics claim.

Reads a 4s window around trigger GPS from H1 strain.
Checks finite values only.
No SSZ interpretation.
"""
import pytest
import numpy as np
import h5py
from pathlib import Path

H1_STRAIN = Path(
    r"E:\clone\ligo-gw240925-gw250207-release\18600070"
    r"\GW240925-C00-Strain\GW240925-C00-Strain"
    r"\O4b4DiscC00_4KHZ_R1\STRAIN_HDF\H1\1410334720"
    r"\H-H1_GWOSC_O4b4DiscC00_4KHZ_R1-1411260416-4096.hdf5"
)

TRIGGER_GPS = 1411261107.984
WIN_S = 4.0

pytestmark = pytest.mark.skipif(
    not H1_STRAIN.exists(),
    reason="LIGO strain file not available"
)


def load_bounded_segment():
    with h5py.File(str(H1_STRAIN), 'r') as f:
        gps0 = float(f['meta/GPSstart'][()])
        dur = float(f['meta/Duration'][()])
        n_total = f['strain/Strain'].shape[0]
        fs = int(n_total / dur)
        t_ev = TRIGGER_GPS - gps0
        i0 = max(0, int((t_ev - WIN_S / 2) * fs))
        i1 = min(n_total, int((t_ev + WIN_S / 2) * fs))
        strain = f['strain/Strain'][i0:i1]
    return strain, fs


class TestBoundedStrainSegment:
    def test_segment_nonempty(self):
        strain, _ = load_bounded_segment()
        assert len(strain) > 0

    def test_segment_finite(self):
        strain, _ = load_bounded_segment()
        assert np.all(np.isfinite(strain)), "NaN or Inf in strain segment"

    def test_no_nan(self):
        strain, _ = load_bounded_segment()
        assert not np.any(np.isnan(strain))

    def test_no_inf(self):
        strain, _ = load_bounded_segment()
        assert not np.any(np.isinf(strain))

    def test_amplitude_order_of_magnitude(self):
        strain, _ = load_bounded_segment()
        rms = np.sqrt(np.mean(strain ** 2))
        assert 1e-25 < rms < 1e-17, (
            f"RMS {rms:.2e} outside expected LIGO strain range"
        )

    def test_sample_rate_reasonable(self):
        _, fs = load_bounded_segment()
        assert fs in (4096, 16384)

    def test_no_ssz_physics_claim(self):
        """Canary: this test must never make an SSZ claim."""
        assert True
