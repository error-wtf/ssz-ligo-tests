"""Test 03: SSZ core equations validation."""
import pytest
import numpy as np
from ssz_ligo_tests import (
    xi_weak, xi_strong, d_ssz, d_gr_schwarzschild,
    get_xi, regime_label, schwarzschild_radius,
    PHI, XI_MAX, D_MIN
)


class TestSchwarzschildRadius:
    """Test r_s = 2GM/c²."""
    
    def test_sun_schwarzschild_radius(self):
        """Sun: r_s ≈ 2953 m."""
        M_sun = 1.989e30
        rs = schwarzschild_radius(M_sun)
        assert np.isclose(rs, 2953, rtol=0.01)
    
    def test_30_solar_masses(self):
        """30 M_sun: r_s ≈ 88.6 km."""
        M = 30 * 1.989e30
        rs = schwarzschild_radius(M)
        assert np.isclose(rs, 88600, rtol=0.01)


class TestXiWeak:
    """Test weak field formula."""
    
    def test_at_10_rs(self):
        """At r = 10r_s: Ξ = 0.05."""
        xi = xi_weak(10.0, 1.0)
        assert np.isclose(xi, 0.05)
    
    def test_at_100_rs(self):
        """At r = 100r_s: Ξ = 0.005."""
        xi = xi_weak(100.0, 1.0)
        assert np.isclose(xi, 0.005)
    
    def test_asymptotic_to_zero(self):
        """As r → ∞: Ξ → 0."""
        xi_100 = xi_weak(100.0, 1.0)
        xi_1000 = xi_weak(1000.0, 1.0)
        assert xi_100 > xi_1000  # Decreasing
        assert xi_1000 < 0.001


class TestXiStrong:
    """Test strong field formula with saturation."""
    
    def test_at_horizon(self):
        """At r = r_s: Ξ = Ξ_max."""
        xi = xi_strong(1.0, 1.0)
        assert np.isclose(xi, XI_MAX, rtol=1e-6)
    
    def test_finite_at_horizon(self):
        """Ξ is finite (not infinite like GR)."""
        xi = xi_strong(1.0, 1.0)
        assert np.isfinite(xi)
        assert xi < 1.0
    
    def test_saturates_at_xi_max(self):
        """Ξ never exceeds Ξ_max."""
        # Test at various radii
        for r in [0.5, 1.0, 1.5, 2.0]:
            xi = xi_strong(r, 1.0)
            assert xi <= XI_MAX * 1.0001


class TestDSSZ:
    """Test SSZ time dilation."""
    
    def test_at_horizon(self):
        """At r = r_s: D = D_min ≈ 0.555."""
        d = d_ssz(XI_MAX)
        assert np.isclose(d, D_MIN, rtol=1e-6)
    
    def test_finite_at_horizon(self):
        """D_SSZ(r_s) = 0.555 > 0 (not 0 like GR)."""
        d = d_ssz(XI_MAX)
        assert d > 0.5
        assert d < 0.6
    
    def test_approaches_1_at_infinity(self):
        """As Ξ → 0: D → 1."""
        d = d_ssz(0.001)
        assert np.isclose(d, 1.0, rtol=0.01)


class TestDGR:
    """Test GR time dilation."""
    
    def test_zero_at_horizon(self):
        """GR: D_GR(r_s) = 0."""
        d = d_gr_schwarzschild(1.0, 1.0)
        assert d == 0.0
    
    def test_ssz_vs_gr_difference(self):
        """Critical: SSZ and GR differ at horizon."""
        # SSZ at horizon
        d_ssz_h = d_ssz(XI_MAX)
        # GR at horizon
        d_gr_h = d_gr_schwarzschild(1.0, 1.0)
        
        assert d_ssz_h > 0.5  # SSZ finite
        assert d_gr_h == 0.0  # GR zero
        assert d_ssz_h != d_gr_h  # They differ!


class TestRegimeDetection:
    """Test automatic regime detection."""
    
    def test_weak_regime(self):
        """r/r_s = 10: WEAK."""
        label = regime_label(10.0, 1.0)
        assert label == "WEAK"
    
    def test_strong_regime(self):
        """r/r_s = 0.5: STRONG."""
        label = regime_label(0.5, 1.0)
        assert label == "STRONG"
    
    def test_blend_regime(self):
        """r/r_s = 2.0: BLEND (BLEND_START=1.8, BLEND_END=2.2)."""
        label = regime_label(2.0, 1.0)
        assert label == "BLEND"


class TestGetXi:
    """Test automatic Ξ(r) selection."""
    
    def test_uses_weak_far_out(self):
        """Far out: uses weak formula."""
        xi = get_xi(10.0, 1.0)
        expected = xi_weak(10.0, 1.0)
        assert np.isclose(xi, expected)
    
    def test_uses_strong_near_horizon(self):
        """Near horizon: uses strong formula."""
        xi = get_xi(1.0, 1.0)
        expected = xi_strong(1.0, 1.0)
        assert np.isclose(xi, expected)
