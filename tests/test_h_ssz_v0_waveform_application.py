"""Test: h_SSZ V0 waveform application.

Verifies:
- h_ssz same shape as h_gr
- deltaPsi finite
- deltaA finite
- metadata: FORMULA_STATUS = DERIVED_V0_PROXY
- metadata: READY_FOR_REAL_CLAIM = NO
- no physics claim made
"""
import numpy as np
from ssz_ligo_tests.derived_waveform import (
    apply_ssz_v0_to_frequency_waveform,
    FORMULA_STATUS,
    READY_FOR_REAL_CLAIM,
)
from ssz_ligo_tests.constants import M_SUN

MC = 8.9 * M_SUN
ETA = 0.25
M_TOTAL = MC / ETA ** (3.0 / 5.0)
MU = ETA * M_TOTAL
FREQS = np.linspace(20.0, 500.0, 100)
H_GR = np.ones(len(FREQS), dtype=complex) * 1e-23


class TestWaveformModuleConstants:
    def test_formula_status(self):
        assert FORMULA_STATUS == "DERIVED_V0_PROXY"

    def test_ready_for_claim_no(self):
        assert READY_FOR_REAL_CLAIM == "NO"


class TestWaveformShape:
    def test_h_ssz_same_shape(self):
        h_ssz, _, _, _ = apply_ssz_v0_to_frequency_waveform(
            H_GR, FREQS, M_TOTAL, MU
        )
        assert h_ssz.shape == H_GR.shape

    def test_h_ssz_complex(self):
        h_ssz, _, _, _ = apply_ssz_v0_to_frequency_waveform(
            H_GR, FREQS, M_TOTAL, MU
        )
        assert h_ssz.dtype == complex or np.iscomplexobj(h_ssz)


class TestWaveformFinite:
    def test_h_ssz_finite(self):
        h_ssz, _, _, _ = apply_ssz_v0_to_frequency_waveform(
            H_GR, FREQS, M_TOTAL, MU
        )
        assert np.all(np.isfinite(np.abs(h_ssz)))

    def test_delta_psi_finite(self):
        _, dp, _, _ = apply_ssz_v0_to_frequency_waveform(
            H_GR, FREQS, M_TOTAL, MU
        )
        assert np.all(np.isfinite(dp))

    def test_delta_a_finite(self):
        _, _, da, _ = apply_ssz_v0_to_frequency_waveform(
            H_GR, FREQS, M_TOTAL, MU
        )
        assert np.all(np.isfinite(da))


class TestWaveformMetadata:
    def test_formula_status_in_meta(self):
        _, _, _, meta = apply_ssz_v0_to_frequency_waveform(
            H_GR, FREQS, M_TOTAL, MU
        )
        assert meta["FORMULA_STATUS"] == "DERIVED_V0_PROXY"

    def test_ready_for_claim_in_meta(self):
        _, _, _, meta = apply_ssz_v0_to_frequency_waveform(
            H_GR, FREQS, M_TOTAL, MU
        )
        assert meta["READY_FOR_REAL_CLAIM"] == "NO"

    def test_support_claim_not_made(self):
        _, _, _, meta = apply_ssz_v0_to_frequency_waveform(
            H_GR, FREQS, M_TOTAL, MU
        )
        assert meta["SSZ_SUPPORT_CLAIM_MADE"] == "NO"

    def test_falsification_claim_not_made(self):
        _, _, _, meta = apply_ssz_v0_to_frequency_waveform(
            H_GR, FREQS, M_TOTAL, MU
        )
        assert meta["SSZ_FALSIFICATION_CLAIM_MADE"] == "NO"

    def test_branch_explicit(self):
        _, _, _, meta = apply_ssz_v0_to_frequency_waveform(
            H_GR, FREQS, M_TOTAL, MU, branch="g2_decay"
        )
        assert meta["branch"] == "g2_decay"
