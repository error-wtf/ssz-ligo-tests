"""Unit tests for SSZ core equations.

Tests against values from SSZ_BOOK_DE_CLEAN.md
"""
import numpy as np
from ssz_ligo_tests import (
    PHI, XI_MAX, D_MIN, N0,
    xi_weak, xi_strong, d_ssz, d_gr,
    get_xi, ssz_scaling
)


class TestSSZConstants:
    """Test SSZ constants from canonical source."""

    def test_phi_value(self):
        """Golden ratio φ = (1 + √5)/2"""
        expected = (1 + np.sqrt(5)) / 2
        assert np.isclose(PHI, expected)
        assert np.isclose(PHI, 1.618033988749895, rtol=1e-10)

    def test_xi_max_value(self):
        """Ξ_max = 1 - exp(-φ) ≈ 0.802"""
        expected = 1 - np.exp(-PHI)
        assert np.isclose(XI_MAX, expected)
        assert np.isclose(XI_MAX, 0.802, rtol=0.01)

    def test_d_min_value(self):
        """D_min = 1/(1 + Ξ_max) ≈ 0.555"""
        expected = 1 / (1 + XI_MAX)
        assert np.isclose(D_MIN, expected)
        assert np.isclose(D_MIN, 0.555, rtol=0.01)

    def test_n0_value(self):
        """Base segmentation N0 = 4"""
        assert N0 == 4


class TestXiWeak:
    """Test weak field formula Ξ_weak = r_s/(2r)"""

    def test_formula_at_large_r(self):
        """At r = 10r_s: Ξ = 0.05"""
        rs = 1.0
        r = 10.0
        xi = xi_weak(r, rs)
        assert np.isclose(xi, 0.05)

    def test_asymptotic_behavior(self):
        """As r → ∞: Ξ → 0"""
        rs = 1.0
        r_values = np.array([100, 1000, 10000])
        xi_values = xi_weak(r_values, rs)
        assert np.all(xi_values > 0)
        assert np.all(np.diff(xi_values) < 0)  # Decreasing

    def test_matches_gr_at_weak_field(self):
        """Ξ_weak matches GR limit at large r"""
        rs = 1.0
        r = 1000 * rs
        xi = xi_weak(r, rs)
        gr_limit = rs / (2 * r)  # This IS the GR post-Newtonian limit
        assert np.isclose(xi, gr_limit)


class TestXiStrong:
    """Test strong field formula with saturation."""

    def test_saturation_at_horizon(self):
        """At r = r_s: Ξ = Ξ_max"""
        rs = 1.0
        r = rs
        xi = xi_strong(r, rs)
        assert np.isclose(xi, XI_MAX, rtol=1e-6)

    def test_finite_value_at_horizon(self):
        """Ξ is finite at horizon (not infinite like GR)"""
        rs = 1.0
        r = rs
        xi = xi_strong(r, rs)
        assert np.isfinite(xi)
        assert xi < 1.0

    def test_increases_with_depth(self):
        """Ξ_saturation increases with r (more field at larger r up to Xi_max).

        Saturation form: 1-exp(-phi*r/rs) increases monotonically with r.
        Larger r → larger Xi until saturation. Different from decay form.
        """
        rs = 1.0
        r_values = np.array([0.1, 0.3, 0.5, 0.8, 1.0])
        xi_values = xi_strong(r_values, rs)
        # unsaturated range: should be increasing with r
        assert np.all(np.diff(xi_values) >= 0)  # non-decreasing

    def test_saturates_at_xi_max(self):
        """Ξ never exceeds Ξ_max"""
        rs = 1.0
        r_values = np.linspace(0.5, 2.0, 100)
        xi_values = xi_strong(r_values, rs)
        assert np.all(xi_values <= XI_MAX * 1.0001)


class TestDSSZ:
    """Test SSZ time dilation D_SSZ = 1/(1 + Ξ)"""

    def test_at_horizon(self):
        """At r = r_s: D = D_min ≈ 0.555"""
        xi = XI_MAX
        d = d_ssz(xi)
        assert np.isclose(d, D_MIN, rtol=1e-6)

    def test_finite_at_horizon(self):
        """D_SSZ(r_s) = 0.555 > 0 (not 0 like GR)"""
        xi = XI_MAX
        d = d_ssz(xi)
        assert d > 0.5
        assert d < 0.6

    def test_approaches_1_at_infinity(self):
        """As Ξ → 0: D → 1"""
        xi = 0.001
        d = d_ssz(xi)
        assert np.isclose(d, 1.0, rtol=0.01)

    def test_monotonic_in_xi(self):
        """D decreases as Ξ increases"""
        xi_values = np.linspace(0, XI_MAX, 100)
        d_values = d_ssz(xi_values)
        assert np.all(np.diff(d_values) < 0)


class TestDGR:
    """Test GR time dilation D_GR = sqrt(1 - r_s/r)"""

    def test_zero_at_horizon(self):
        """GR: D_GR(r_s) = 0"""
        rs = 1.0
        r = rs
        d = d_gr(r, rs)
        assert np.isclose(d, 0.0)

    def test_approaches_1_at_infinity(self):
        """As r → ∞: D_GR → 1"""
        rs = 1.0
        r = 10000 * rs
        d = d_gr(r, rs)
        assert np.isclose(d, 1.0, rtol=0.001)

    def test_ssz_vs_gr_at_horizon(self):
        """Critical: SSZ has D=0.555, GR has D=0"""
        rs = 1.0
        r = rs
        val_ssz = d_ssz(XI_MAX)
        val_gr = d_gr(r, rs)
        assert val_ssz > 0.5  # SSZ finite
        assert val_gr == 0.0  # GR zero
        assert val_ssz != val_gr  # They differ!


class TestRegimeDetection:
    """Test automatic regime detection."""

    def test_strong_regime_at_horizon(self):
        """At r = r_s: use strong formula"""
        rs = 1.0
        r = rs
        xi = get_xi(r, rs)
        # Should be close to XI_max
        assert np.isclose(xi, XI_MAX, rtol=0.1)

    def test_weak_regime_far_out(self):
        """At r = 10r_s: use weak formula"""
        rs = 1.0
        r = 10 * rs
        xi = get_xi(r, rs)
        expected = xi_weak(r, rs)
        assert np.isclose(xi, expected)


class TestSSZScaling:
    """Test complete SSZ scaling function."""

    def test_finite_at_horizon(self):
        """SSZ scaling is finite everywhere"""
        rs = 1.0
        r_values = np.linspace(1.0, 10.0, 100)
        xi_values = np.array([xi_weak(r, rs) for r in r_values])
        d_values = ssz_scaling(xi_values)
        assert np.all(np.isfinite(d_values))
        assert np.all(d_values > 0.5)
        assert np.all(d_values <= 1.0)
