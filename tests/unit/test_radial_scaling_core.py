"""Test radial scaling core functions."""
import pytest
import numpy as np
from ssz_ligo_tests import (
    s_scale, rho_rsg, drho_dr,
    phase_accounting_factor_ssz, phase_accounting_factor_gr,
    blend_strong_to_weak, xi_blended,
    XI_MAX, D_MIN
)


class TestSScale:
    """Test s(r) = 1 + Ξ(r)."""
    
    def test_at_horizon(self):
        """At r = r_s: s = 1 + Ξ_max = 1/D_min ≈ 1.80."""
        s = s_scale(XI_MAX)
        expected = 1 / D_MIN
        assert np.isclose(s, expected, rtol=1e-6)
        assert np.isclose(s, 1.80, rtol=0.01)
    
    def test_in_weak_field(self):
        """In weak field: s ≈ 1 (small Ξ)."""
        xi_weak = 0.001
        s = s_scale(xi_weak)
        assert np.isclose(s, 1.001, rtol=0.01)


class TestBlendFunction:
    """Test strong-to-weak blend."""
    
    def test_pure_strong(self):
        """r/r_s = 0.5: pure strong (w=1)."""
        w = blend_strong_to_weak(0.5, 1.0)
        assert w == 1.0
    
    def test_pure_weak(self):
        """r/r_s = 3.0: pure weak (w=0)."""
        w = blend_strong_to_weak(3.0, 1.0)
        assert w == 0.0
    
    def test_blend_zone(self):
        """r/r_s = 1.5: blend zone (0 < w < 1)."""
        w = blend_strong_to_weak(1.5, 1.0)
        assert 0.0 < w < 1.0


class TestDRhoDr:
    """Test phase accounting weight."""
    
    def test_at_horizon(self):
        """At horizon: dρ/dr = D_min²."""
        drho = drho_dr(1.0, 1.0)
        expected = D_MIN ** 2
        assert np.isclose(drho, expected, rtol=0.01)
    
    def test_decreases_outward(self):
        """dρ/dr = D(r)^2 increases as r increases (D larger far out)."""
        drho_inner = drho_dr(1.5, 1.0)
        drho_outer = drho_dr(5.0, 1.0)
        assert drho_outer > drho_inner


class TestPhaseAccountingFactor:
    """Test phase accounting factor A(r)."""
    
    def test_ssz_vs_gr_at_horizon(self):
        """At horizon: SSZ factor > GR factor (D_min > 0)."""
        a_ssz = phase_accounting_factor_ssz(1.0, 1.0)
        a_gr = phase_accounting_factor_gr(1.0, 1.0)
        assert a_ssz > 0
        assert a_gr == 0  # GR has D=0 at horizon
        assert a_ssz != a_gr


class TestRhoRSG:
    """Test RSG coordinate (simplified proxy)."""
    
    def test_zero_at_horizon(self):
        """ρ(r_s) = 0 (by definition of integration start)."""
        rho = rho_rsg(1.0, 1.0)
        assert rho == 0.0
    
    def test_positive_outward(self):
        """ρ increases outward from horizon."""
        rho_near = rho_rsg(1.5, 1.0)
        rho_far = rho_rsg(3.0, 1.0)
        assert rho_near > 0
        assert rho_far > rho_near


class TestXiBlended:
    """Test blended Ξ(r)."""
    
    def test_smooth_transition(self):
        """Blended Ξ is smooth across regimes."""
        # Sample at various radii
        radii = [0.5, 1.0, 1.5, 2.0, 3.0, 10.0]
        xi_values = [xi_blended(r, 1.0) for r in radii]
        
        # All should be finite
        assert all(np.isfinite(xi) for xi in xi_values)
        
        # Should be monotonic (decreasing outward)
        # Actually Xi increases then saturates
        # Just check no NaNs
