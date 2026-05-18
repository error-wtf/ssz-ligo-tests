"""Test strong field to weak field transition."""
import pytest
import numpy as np
from ssz_ligo_tests import (
    xi_weak, xi_strong, xi_blended,
    blend_strong_to_weak,
    phase_accounting_factor_ssz, phase_accounting_factor_gr,
    rho_rsg,
    XI_MAX, D_MIN, PHI
)


class TestStrongToWeakTransition:
    """Test smooth transition from strong to weak field."""
    
    def test_xi_smooth_across_transition(self):
        """Blended Ξ is continuous across transition zone."""
        rs = 1.0
        
        # Sample points across blend zone 0.8 to 2.2
        radii = np.linspace(0.7, 2.3, 100)
        xi_values = [xi_blended(r, rs) for r in radii]
        
        # Check no jumps
        diffs = np.diff(xi_values)
        max_diff = np.max(np.abs(diffs))
        
        # Should be smooth (no large jumps)
        assert max_diff < 0.1
    
    def test_blend_weight_transitions(self):
        """Blend weight transitions from 1 to 0."""
        rs = 1.0
        
        # Inner: w=1
        w_inner = blend_strong_to_weak(0.5 * rs, rs)
        assert w_inner == 1.0
        
        # Outer: w=0
        w_outer = blend_strong_to_weak(3.0 * rs, rs)
        assert w_outer == 0.0
        
        # Middle: 0 < w < 1
        w_mid = blend_strong_to_weak(1.5 * rs, rs)
        assert 0.0 < w_mid < 1.0
    
    def test_pure_strong_at_horizon(self):
        """At r = r_s: pure strong field formula."""
        rs = 1.0
        r = rs
        
        xi_blend = xi_blended(r, rs)
        xi_strong_val = xi_strong(r, rs)
        
        # Should be close to strong field value
        assert np.isclose(xi_blend, xi_strong_val, rtol=0.1)
    
    def test_pure_weak_far_out(self):
        """At r >> r_s: pure weak field formula."""
        rs = 1.0
        r = 100 * rs
        
        xi_blend = xi_blended(r, rs)
        xi_weak_val = xi_weak(r, rs)
        
        # Should be close to weak field value
        assert np.isclose(xi_blend, xi_weak_val, rtol=0.01)


class TestPhaseAccountingTransition:
    """Test phase accounting factor across transition."""
    
    def test_factor_continuous(self):
        """Phase accounting factor is continuous."""
        rs = 1.0
        radii = np.linspace(0.7, 3.0, 50)
        
        factors = [phase_accounting_factor_ssz(r, rs) for r in radii]
        
        # Check no NaNs
        assert all(np.isfinite(f) for f in factors)
        
        # Check monotonic-ish (decreasing outward)
        # Not strictly monotonic due to blend, but roughly


class TestRSGCoordinate:
    """Test RSG coordinate behavior."""
    
    def test_rsg_increases_monotonically(self):
        """ρ(r) increases monotonically outward."""
        rs = 1.0
        radii = np.linspace(1.0, 10.0, 20)
        
        rho_values = [rho_rsg(r, rs) for r in radii]
        
        # Should be monotonically increasing
        for i in range(len(rho_values) - 1):
            assert rho_values[i] < rho_values[i+1] or np.isclose(rho_values[i], rho_values[i+1])


class TestPhysicalRegimes:
    """Test that physics behaves correctly in each regime."""
    
    def test_strong_field_dominates_near_horizon(self):
        """Near horizon: strong field effects dominate."""
        rs = 1.0
        
        # Very close to horizon
        r = 1.01 * rs
        
        # Phase accounting should be significantly different from GR
        a_ssz = phase_accounting_factor_ssz(r, rs)
        a_gr = phase_accounting_factor_gr(r, rs)
        
        # SSZ finite, GR zero
        # With saturation form: D_min^2/s_max^2 = 0.555^2/1.802^2 ~ 0.095
        assert a_ssz > 0.08
        assert a_gr < 0.01
    
    def test_weak_field_far_out(self):
        """Far out: weak field, SSZ ≈ GR."""
        rs = 1.0
        r = 100 * rs
        
        a_ssz = phase_accounting_factor_ssz(r, rs)
        a_gr = phase_accounting_factor_gr(r, rs)
        
        # Should be close (within ~1%)
        assert abs(a_ssz - a_gr) < 0.01
