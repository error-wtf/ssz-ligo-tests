"""Test: Xi_strong branch lock.

Verifies:
- canonical saturation form is xi_strong() default
- decay form exists as explicit DIDACTIC_COMPLEMENTARY function
- both agree at r = rs
- they differ at r != rs
- deprecated form is never silently used
- branch labels are present

Source: docs/XI_STRONG_BRANCH_LOCK.md
"""
import numpy as np
import pytest
from ssz_ligo_tests.ssz_core import (
    xi_strong,
    xi_strong_saturation,
    xi_strong_decay,
    XI_STRONG_CANONICAL,
    XI_STRONG_DIDACTIC,
    XI_STRONG_DEPRECATED,
)
from ssz_ligo_tests.constants import PHI, XI_MAX


class TestBranchLabelsPresent:
    def test_canonical_label_exists(self):
        assert XI_STRONG_CANONICAL == "CANONICAL_OPERATIONAL"

    def test_didactic_label_exists(self):
        assert XI_STRONG_DIDACTIC == "DIDACTIC_COMPLEMENTARY"

    def test_deprecated_label_exists(self):
        assert XI_STRONG_DEPRECATED == "INVALID_DEPRECATED"


class TestCanonicalSaturation:
    """xi_strong_saturation: 1 - exp(-phi * r/rs), capped at XI_MAX."""

    def test_at_rs_equals_xi_max(self):
        rs = 1.0
        xi = xi_strong_saturation(rs, rs)
        expected = min(1 - np.exp(-PHI), XI_MAX)
        assert np.isclose(xi, expected, rtol=1e-10)
        assert np.isclose(xi, XI_MAX, rtol=1e-6)

    def test_r_zero_approaches_zero(self):
        rs = 1.0
        xi = xi_strong_saturation(0.001 * rs, rs)
        assert xi < 0.01

    def test_r_infinity_saturates_at_xi_max(self):
        rs = 1.0
        xi = xi_strong_saturation(1000 * rs, rs)
        assert np.isclose(xi, XI_MAX, rtol=1e-3)

    def test_monotonically_increasing(self):
        rs = 1.0
        r_vals = np.linspace(0.1 * rs, 5 * rs, 20)
        xi_vals = xi_strong_saturation(r_vals, rs)
        assert np.all(np.diff(xi_vals) >= 0)

    def test_never_exceeds_xi_max(self):
        rs = 1.0
        r_vals = np.logspace(-2, 3, 100) * rs
        xi_vals = xi_strong_saturation(r_vals, rs)
        assert np.all(xi_vals <= XI_MAX + 1e-12)


class TestDecayDidactic:
    """xi_strong_decay: 1 - exp(-phi * rs/r) — DIDACTIC only."""

    def test_at_rs_equals_xi_max(self):
        rs = 1.0
        xi = xi_strong_decay(rs, rs)
        expected = min(1 - np.exp(-PHI), XI_MAX)
        assert np.isclose(xi, expected, rtol=1e-10)

    def test_r_infinity_decays_to_zero(self):
        rs = 1.0
        xi = xi_strong_decay(1e6 * rs, rs)
        assert xi < 1e-3

    def test_r_small_saturates_at_xi_max(self):
        rs = 1.0
        xi = xi_strong_decay(0.001 * rs, rs)
        assert np.isclose(xi, XI_MAX, rtol=1e-6)

    def test_monotonically_decreasing(self):
        rs = 1.0
        r_vals = np.linspace(0.5 * rs, 10 * rs, 20)
        xi_vals = xi_strong_decay(r_vals, rs)
        assert np.all(np.diff(xi_vals) <= 0)


class TestBranchDifference:
    """Saturation and decay agree at r=rs, differ elsewhere."""

    def test_agree_at_rs(self):
        rs = 1.0
        xi_sat = xi_strong_saturation(rs, rs)
        xi_dec = xi_strong_decay(rs, rs)
        assert np.isclose(xi_sat, xi_dec, rtol=1e-10)

    def test_differ_at_r_neq_rs(self):
        rs = 1.0
        for r_ratio in [0.3, 2.0, 5.0]:
            r = r_ratio * rs
            xi_sat = xi_strong_saturation(r, rs)
            xi_dec = xi_strong_decay(r, rs)
            assert not np.isclose(xi_sat, xi_dec, rtol=0.01), (
                f"At r/rs={r_ratio}: saturation={xi_sat:.4f} "
                f"decay={xi_dec:.4f} unexpectedly equal"
            )

    def test_xi_strong_delegates_to_canonical(self):
        rs = 1.0
        for r_ratio in [0.3, 0.5, 1.0, 1.5]:
            r = r_ratio * rs
            xi_default = xi_strong(r, rs)
            xi_sat = xi_strong_saturation(r, rs)
            assert np.isclose(xi_default, xi_sat, rtol=1e-12), (
                f"xi_strong() does not delegate to saturation at r/rs={r_ratio}"
            )
