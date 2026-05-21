"""Test: derived deltaA_SSZ_V0.

Verifies:
- finite output
- D/s relation: deltaA = D^2 - 1 in (-1, 0]
- in weak field (LIGO band): |deltaA| << 1
- branch explicit in metadata
"""
import numpy as np
from ssz_ligo_tests.derived_amplitude import (
    delta_a_ssz_v0,
    FORMULA_STATUS,
    READY_FOR_REAL_CLAIM,
)
from ssz_ligo_tests.constants import M_SUN

MC = 8.9 * M_SUN
ETA = 0.25
M_TOTAL = MC / ETA ** (3.0 / 5.0)
FREQS = np.linspace(20.0, 500.0, 100)


class TestDeltaAModuleConstants:
    def test_formula_status(self):
        assert FORMULA_STATUS == "DERIVED_V1"

    def test_ready_for_claim_no(self):
        assert READY_FOR_REAL_CLAIM == "NO"


class TestDeltaAFinite:
    def test_output_finite(self):
        da, _ = delta_a_ssz_v0(FREQS, M_TOTAL)
        assert np.all(np.isfinite(da))

    def test_no_nan(self):
        da, _ = delta_a_ssz_v0(FREQS, M_TOTAL)
        assert not np.any(np.isnan(da))


class TestDeltaAPhysical:
    def test_negative_in_strong_field(self):
        da, _ = delta_a_ssz_v0(FREQS, M_TOTAL)
        assert np.all(da <= 0), "deltaA should be <=0 (amplitude suppressed)"

    def test_above_minus_one(self):
        da, _ = delta_a_ssz_v0(FREQS, M_TOTAL)
        assert np.all(da > -1.0), "D^2-1 should be > -1 for D in (0,1]"

    def test_bounded_in_ligo_band(self):
        da, _ = delta_a_ssz_v0(FREQS, M_TOTAL)
        assert np.all(np.abs(da) < 1.0), (
            "|deltaA| = D^2-1, D in (0,1] => |deltaA| < 1 by construction"
        )

    def test_low_freq_correction_smaller_than_high_freq(self):
        da, _ = delta_a_ssz_v0(FREQS, M_TOTAL)
        assert abs(da[0]) < abs(da[-1]), (
            "Low-freq (large r, weak field) should have smaller correction"
        )

    def test_d_values_physical(self):
        _, meta = delta_a_ssz_v0(FREQS, M_TOTAL)
        assert 0.0 < meta["D_at_f_min"] <= 1.0
        assert 0.0 < meta["D_at_f_max"] <= 1.0


class TestDeltaAMetadata:
    def test_metadata_formula_status(self):
        _, meta = delta_a_ssz_v0(FREQS, M_TOTAL)
        assert meta["FORMULA_STATUS"] == "DERIVED_V1"

    def test_metadata_ready_for_claim(self):
        _, meta = delta_a_ssz_v0(FREQS, M_TOTAL)
        assert meta["READY_FOR_REAL_CLAIM"] == "NO"

    def test_metadata_branch_explicit(self):
        _, meta = delta_a_ssz_v0(FREQS, M_TOTAL, branch="g2_decay")
        assert meta["branch"] == "g2_decay"

    def test_source_equation_recorded(self):
        _, meta = delta_a_ssz_v0(FREQS, M_TOTAL)
        assert "D(r)^2 - 1" in meta["source_equation"]
