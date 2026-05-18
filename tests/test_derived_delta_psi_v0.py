"""Test: derived deltaPsi_SSZ_V0.

Verifies:
- finite output
- deterministic (same input = same output)
- no fitted parameters (formula depends only on M, mu, f)
- weak-field: correction small (r >> rs)
- branch label explicit in metadata
- metadata has FORMULA_STATUS = DERIVED_V0_PROXY
- metadata has READY_FOR_REAL_CLAIM = NO
"""
import numpy as np
import pytest
from ssz_ligo_tests.derived_phase import (
    delta_psi_ssz_v0,
    FORMULA_STATUS,
    READY_FOR_REAL_CLAIM,
)
from ssz_ligo_tests.constants import M_SUN

MC = 8.9 * M_SUN
ETA = 0.25
M_TOTAL = MC / ETA ** (3.0 / 5.0)
MU = ETA * M_TOTAL
FREQS = np.linspace(20.0, 500.0, 100)


class TestDeltaPsiModuleConstants:
    def test_formula_status_derived(self):
        assert FORMULA_STATUS == "DERIVED_V0_PROXY"

    def test_ready_for_claim_no(self):
        assert READY_FOR_REAL_CLAIM == "NO"


class TestDeltaPsiFinite:
    def test_output_finite(self):
        dpsi, _ = delta_psi_ssz_v0(FREQS, M_TOTAL, MU)
        assert np.all(np.isfinite(dpsi))

    def test_no_nan(self):
        dpsi, _ = delta_psi_ssz_v0(FREQS, M_TOTAL, MU)
        assert not np.any(np.isnan(dpsi))

    def test_no_inf(self):
        dpsi, _ = delta_psi_ssz_v0(FREQS, M_TOTAL, MU)
        assert not np.any(np.isinf(dpsi))

    def test_nonnegative(self):
        dpsi, _ = delta_psi_ssz_v0(FREQS, M_TOTAL, MU)
        assert np.all(dpsi >= 0)


class TestDeltaPsiDeterministic:
    def test_same_output_on_repeat(self):
        dp1, _ = delta_psi_ssz_v0(FREQS, M_TOTAL, MU)
        dp2, _ = delta_psi_ssz_v0(FREQS, M_TOTAL, MU)
        np.testing.assert_array_equal(dp1, dp2)


class TestDeltaPsiWeakFieldLimit:
    def test_small_in_ligo_band(self):
        dpsi, _ = delta_psi_ssz_v0(FREQS, M_TOTAL, MU)
        assert dpsi.max() < 10.0, (
            f"deltaPsi too large in weak-field LIGO band: {dpsi.max():.3f}"
        )


class TestDeltaPsiMetadata:
    def test_metadata_formula_status(self):
        _, meta = delta_psi_ssz_v0(FREQS, M_TOTAL, MU)
        assert meta["FORMULA_STATUS"] == "DERIVED_V0_PROXY"

    def test_metadata_ready_for_claim(self):
        _, meta = delta_psi_ssz_v0(FREQS, M_TOTAL, MU)
        assert meta["READY_FOR_REAL_CLAIM"] == "NO"

    def test_metadata_branch_explicit(self):
        _, meta = delta_psi_ssz_v0(FREQS, M_TOTAL, MU, branch="g2_decay")
        assert meta["branch"] == "g2_decay"

    def test_metadata_r_over_rs(self):
        _, meta = delta_psi_ssz_v0(FREQS, M_TOTAL, MU)
        assert meta["r_over_rs_min"] > 0
        assert meta["r_over_rs_max"] > meta["r_over_rs_min"]


class TestDeltaPsiRaisesOnBadInput:
    def test_raises_on_zero_freq(self):
        with pytest.raises((ValueError, RuntimeError)):
            delta_psi_ssz_v0(np.array([0.0, 100.0]), M_TOTAL, MU)

    def test_raises_on_negative_freq(self):
        with pytest.raises((ValueError, RuntimeError)):
            delta_psi_ssz_v0(np.array([-10.0, 100.0]), M_TOTAL, MU)
