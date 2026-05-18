"""Test: Regime boundary continuity.

Verifies:
- BLEND_START=1.8, BLEND_END=2.2 are used (named constants, not hardcoded)
- Xi is continuous at blend boundaries
- D is continuous at blend boundaries
- deltaPsi proxy has no jumps
- regime_label uses correct boundaries

Source: docs/REGIME_BOUNDARY_LOCK.md
        formula_compendium.md §B.2
"""
import numpy as np
from ssz_ligo_tests.ssz_core import (
    xi_weak, xi_strong_saturation, get_xi, d_ssz, regime_label
)
from ssz_ligo_tests.constants import BLEND_START, BLEND_END, PHI, XI_MAX


RS = 1.0  # reference Schwarzschild radius


class TestBoundaryConstants:
    def test_blend_start_value(self):
        assert BLEND_START == 1.8

    def test_blend_end_value(self):
        assert BLEND_END == 2.2

    def test_blend_start_less_than_blend_end(self):
        assert BLEND_START < BLEND_END

    def test_regime_label_uses_blend_end(self):
        r_above = BLEND_END * RS + 0.01 * RS
        assert regime_label(r_above, RS) == "WEAK"

    def test_regime_label_uses_blend_start(self):
        r_below = BLEND_START * RS - 0.01 * RS
        assert regime_label(r_below, RS) == "STRONG"

    def test_regime_label_blend_zone(self):
        r_mid = ((BLEND_START + BLEND_END) / 2) * RS
        assert regime_label(r_mid, RS) == "BLEND"


class TestXiContinuityAtBoundaries:
    """Xi must be continuous (no jumps) at blend boundaries."""

    def test_xi_continuous_at_blend_end(self):
        eps = 1e-4
        r_just_above = (BLEND_END + eps) * RS
        r_just_below = (BLEND_END - eps) * RS
        xi_above = get_xi(r_just_above, RS)
        xi_below = get_xi(r_just_below, RS)
        assert abs(xi_above - xi_below) < 0.05, (
            f"Xi jump at BLEND_END: above={xi_above:.4f} below={xi_below:.4f}"
        )

    def test_xi_continuous_at_blend_start(self):
        eps = 1e-4
        r_just_above = (BLEND_START + eps) * RS
        r_just_below = (BLEND_START - eps) * RS
        xi_above = get_xi(r_just_above, RS)
        xi_below = get_xi(r_just_below, RS)
        assert abs(xi_above - xi_below) < 0.05, (
            f"Xi jump at BLEND_START: above={xi_above:.4f} below={xi_below:.4f}"
        )

    def test_xi_monotone_through_blend(self):
        r_vals = np.linspace(BLEND_START * RS, BLEND_END * RS, 30)
        xi_vals = np.array([get_xi(r, RS) for r in r_vals])
        diffs = np.diff(xi_vals)
        assert np.all(diffs <= 0.01), "Xi is not monotone through blend zone"


class TestDContinuityAtBoundaries:
    """D = 1/(1+Xi) must be continuous at blend boundaries."""

    def test_d_continuous_at_blend_end(self):
        eps = 1e-4
        xi_above = get_xi((BLEND_END + eps) * RS, RS)
        xi_below = get_xi((BLEND_END - eps) * RS, RS)
        d_above = d_ssz(xi_above)
        d_below = d_ssz(xi_below)
        assert abs(d_above - d_below) < 0.05, (
            f"D jump at BLEND_END: above={d_above:.4f} below={d_below:.4f}"
        )

    def test_d_continuous_at_blend_start(self):
        eps = 1e-4
        xi_above = get_xi((BLEND_START + eps) * RS, RS)
        xi_below = get_xi((BLEND_START - eps) * RS, RS)
        d_above = d_ssz(xi_above)
        d_below = d_ssz(xi_below)
        assert abs(d_above - d_below) < 0.05, (
            f"D jump at BLEND_START: above={d_above:.4f} below={d_below:.4f}"
        )


class TestDeltaPsiNoContinuityJump:
    """deltaPsi V0 proxy must have no discontinuous jump at boundaries."""

    def _dpsi(self, r, rs, kappa=1.0):
        xi = get_xi(r, rs)
        return kappa * (1.0 - d_ssz(xi))

    def test_dpsi_no_jump_at_blend_end(self):
        eps = 1e-4
        dp_above = self._dpsi((BLEND_END + eps) * RS, RS)
        dp_below = self._dpsi((BLEND_END - eps) * RS, RS)
        assert abs(dp_above - dp_below) < 0.05

    def test_dpsi_no_jump_at_blend_start(self):
        eps = 1e-4
        dp_above = self._dpsi((BLEND_START + eps) * RS, RS)
        dp_below = self._dpsi((BLEND_START - eps) * RS, RS)
        assert abs(dp_above - dp_below) < 0.05
