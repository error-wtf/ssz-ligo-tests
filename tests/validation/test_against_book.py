"""Validation tests against SSZ canonical sources.

Tests that implementation matches SSZ_BOOK_DE_CLEAN.md
"""
import numpy as np
import pytest
from ssz_ligo_tests import (
    PHI, XI_MAX, D_MIN,
    xi_weak, xi_strong, d_ssz, d_gr
)


class TestAgainstSSZBook:
    """Validate against SSZ_BOOK_DE_CLEAN.md values."""
    
    def test_phi_matches_book(self):
        """φ = (1 + √5)/2 ≈ 1.618 (Book Ch.1)"""
        assert np.isclose(PHI, 1.618033988749895, rtol=1e-10)
    
    def test_xi_max_matches_book(self):
        """Ξ_max = 1 - exp(-φ) ≈ 0.802 (Book Ch.1)"""
        # From Book: Xi_max = 1 - exp(-phi)
        assert np.isclose(XI_MAX, 0.802, rtol=0.01)
    
    def test_d_min_matches_book(self):
        """D_min = 0.555 (Book Ch.1)"""
        # From Book: D_min = 1/(1 + Xi_max)
        assert np.isclose(D_MIN, 0.555, rtol=0.01)
    
    def test_xi_at_horizon_from_book(self):
        """At r = r_s: Ξ = Ξ_max (Book Ch.1)"""
        rs = 1.0
        xi = xi_strong(rs, rs)
        assert np.isclose(xi, XI_MAX, rtol=1e-6)
    
    def test_d_at_horizon_from_book(self):
        """At r = r_s: D = D_min ≈ 0.555 (Book Ch.1)"""
        xi_horizon = XI_MAX
        d = d_ssz(xi_horizon)
        assert np.isclose(d, 0.555, rtol=0.01)
    
    def test_gr_d_zero_at_horizon(self):
        """GR: D_GR(r_s) = 0 (Book Ch.1 contrast)"""
        rs = 1.0
        val = d_gr(rs, rs)
        assert val == 0.0
        # This is the KEY difference!


class TestKeySSZPredictions:
    """Test key predictions from SSZ Book Ch.30."""
    
    def test_d_min_universal(self):
        """D_min is mass-independent (Book Ch.30)"""
        # D_min should be the same for any mass
        for M in [10, 30, 100]:  # Solar masses
            rs = 2 * 6.674e-11 * M * 1.989e30 / (3e8)**2
            xi = xi_strong(rs, rs)
            d = d_ssz(xi)
            assert np.isclose(d, D_MIN, rtol=1e-6)
    
    def test_weak_field_gr_agreement(self):
        """SSZ ≈ GR for r/r_s > 10 (Book Ch.1)"""
        rs = 1.0
        r = 10.0  # 10 × r_s

        xi = xi_weak(r, rs)
        val_ssz = d_ssz(xi)
        val_gr = d_gr(r, rs)

        # Should be close (within ~1%)
        assert np.abs(val_ssz - val_gr) < 0.01
    
    def test_strong_field_divergence(self):
        """SSZ ≠ GR for r/r_s = 1 (at horizon, Book Ch.1)"""
        rs = 1.0
        r = rs  # At horizon: D_ssz = 0.555, D_gr = 0

        xi = xi_strong(r, rs)
        val_ssz = d_ssz(xi)
        val_gr = d_gr(r, rs)

        # D_ssz ~ 0.555, D_gr = 0 → large difference
        assert np.abs(val_ssz - val_gr) > 0.1
    
    def test_finite_vs_infinite_redshift(self):
        """SSZ finite (z=0.80) vs GR infinite at horizon"""
        rs = 1.0
        
        # SSZ at horizon
        xi_h = XI_MAX
        z_ssz = xi_h  # z = Ξ for SSZ
        
        # GR at horizon
        z_gr = np.inf  # Infinite redshift
        
        # SSZ is finite
        assert np.isfinite(z_ssz)
        assert np.isclose(z_ssz, 0.80, rtol=0.05)
        
        # GR is infinite
        assert z_gr == np.inf


class TestRingdownAmbiguity:
    """Document the ε_220 ambiguity from Book Ch.30."""
    
    def test_d_min_squared_vs_3_percent(self):
        """Document ambiguity: D_min² ≈ 0.31 vs 'ca. 3%'"""
        d_min_squared = D_MIN ** 2
        
        # Book says "proportional to D_min²" and "ca. 3%"
        # These are INCONSISTENT!
        assert np.isclose(d_min_squared, 0.308, rtol=0.01)
        
        # 3% would be:
        three_percent = 0.03
        
        # They differ by factor of ~10
        ratio = d_min_squared / three_percent
        assert ratio > 5  # Significant discrepancy
        
        # This must be resolved before numerical test!
        pytest.xfail("ε_220 ambiguity: 31% vs 3% must be resolved")


class TestGuardrails:
    """Test SSZ guardrails from memory."""
    
    def test_regime_detection_critical(self):
        """Using wrong regime formula = wrong results."""
        rs = 1.0
        
        # At neutron star surface (r/r_s ~ 3)
        # MUST use strong field formula
        r_ns = 3.0
        
        xi_weak_val = xi_weak(r_ns, rs)
        xi_strong_val = xi_strong(r_ns, rs)
        
        # They differ!
        assert xi_weak_val != xi_strong_val
        
        # Weak formula gives: 1/6 ≈ 0.167
        # Strong formula: 1 - exp(-phi * rs / r_ns) with r_ns = 3
        assert np.isclose(xi_weak_val, 1/6, rtol=0.01)
        assert xi_strong_val != xi_weak_val  # They differ!
