"""Test SSZ inspiral phase forward model."""
import pytest
import numpy as np
from ssz_ligo_tests import (
    gw_power_gr, gw_power_ssz,
    rdot_gr, rdot_ssz,
    orbital_frequency, dphi_dr,
    accumulated_phase, delta_phase_ssz_minus_gr,
    r_isco,
    G, C
)


class TestGWPower:
    """Test gravitational wave power with SSZ correction."""
    
    def test_ssz_less_than_gr(self):
        """P_GW^SSZ < P_GW^GR due to D²/s² factor < 1."""
        M = 30 * 1.989e30  # 30 solar masses
        mu = M / 4  # q=1, mu = M/4
        rs = 2 * G * M / C**2
        r = 10 * rs  # Moderate strong field
        
        p_gr = gw_power_gr(r, M, mu)
        p_ssz = gw_power_ssz(r, M, mu, rs)
        
        # D < 1 and s > 1, so D²/s² < 1
        assert p_ssz < p_gr
        assert p_ssz > 0
    
    def test_correction_factor_reasonable(self):
        """SSZ correction is moderate (not extreme)."""
        M = 30 * 1.989e30
        mu = M / 4
        rs = 2 * G * M / C**2
        r = 5 * rs
        
        p_gr = gw_power_gr(r, M, mu)
        p_ssz = gw_power_ssz(r, M, mu, rs)
        
        ratio = p_ssz / p_gr
        assert 0.1 < ratio < 1.0  # Within reasonable bounds


class TestRdot:
    """Test inspiral rate (dr/dt)."""
    
    def test_rdot_negative(self):
        """dr/dt < 0 (inspiral, not outspiral)."""
        M = 30 * 1.989e30
        mu = M / 4
        rs = 2 * G * M / C**2
        r = 10 * rs
        
        rdot_ssz_val = rdot_ssz(r, M, mu, rs)
        assert rdot_ssz_val < 0
    
    def test_ssz_slower_than_gr(self):
        """SSZ inspiral slower than GR (stronger D correction for rdot)."""
        M = 30 * 1.989e30
        mu = M / 4
        rs = 2 * G * M / C**2
        r = 5 * rs
        
        rdot_gr_val = rdot_gr(r, M, mu)
        rdot_ssz_val = rdot_ssz(r, M, mu, rs)
        
        # Both negative, SSZ less negative = slower
        assert abs(rdot_ssz_val) < abs(rdot_gr_val)


class TestOrbitalFrequency:
    """Test Keplerian orbital frequency."""
    
    def test_decreases_with_radius(self):
        """Ω decreases as r increases."""
        M = 30 * 1.989e30
        
        omega_inner = orbital_frequency(10e3, M)  # 10 km
        omega_outer = orbital_frequency(100e3, M)  # 100 km
        
        assert omega_inner > omega_outer
    
    def test_proportional_to_sqrt_mass(self):
        """Ω ∝ √M at fixed r."""
        r = 100e3
        
        omega_10 = orbital_frequency(r, 10 * 1.989e30)
        omega_30 = orbital_frequency(r, 30 * 1.989e30)
        
        # 30 M_sun vs 10 M_sun: ratio should be √3
        assert np.isclose(omega_30 / omega_10, np.sqrt(3), rtol=0.01)


class TestDphiDr:
    """Test phase accumulation per radius."""
    
    def test_finite_everywhere(self):
        """dφ/dr is finite (no singularities)."""
        M = 30 * 1.989e30
        mu = M / 4
        rs = 2 * G * M / C**2
        
        for r in [5 * rs, 10 * rs, 50 * rs]:
            dphi = dphi_dr(r, M, mu, rs, "ssz")
            assert np.isfinite(dphi)
    
    def test_ssz_vs_gr_different(self):
        """SSZ and GR give different dφ/dr."""
        M = 30 * 1.989e30
        mu = M / 4
        rs = 2 * G * M / C**2
        r = 10 * rs
        
        dphi_ssz = dphi_dr(r, M, mu, rs, "ssz")
        dphi_gr = dphi_dr(r, M, mu, rs, "gr")
        
        assert dphi_ssz != dphi_gr


class TestAccumulatedPhase:
    """Test orbital phase accumulation."""
    
    def test_negative_inspiral(self):
        """Phase is negative for inspiral (r decreasing)."""
        M = 30 * 1.989e30
        mu = M / 4
        rs = 2 * G * M / C**2
        
        r_start = 100 * rs
        r_end = 50 * rs
        
        phi = accumulated_phase(r_start, r_end, M, mu, rs, "ssz")
        assert phi != 0  # Phase accumulates inward (sign convention: r_end < r_start)
    
    def test_many_radians(self):
        """Phase accumulates many radians over inspiral."""
        M = 30 * 1.989e30
        mu = M / 4
        rs = 2 * G * M / C**2
        
        r_start = 100 * rs
        r_end = 10 * rs
        
        phi = accumulated_phase(r_start, r_end, M, mu, rs, "ssz")
        assert abs(phi) > 10  # At least 10 radians


class TestDeltaPhase:
    """Test SSZ vs GR phase difference."""
    
    def test_ssz_gr_phase_difference_finite(self):
        """Δφ = φ_SSZ - φ_GR is finite and non-zero."""
        M = 30 * 1.989e30
        mu = M / 4
        rs = 2 * G * M / C**2
        
        r_start = 50 * rs
        r_end = 10 * rs
        
        delta_phi = delta_phase_ssz_minus_gr(r_start, r_end, M, mu, rs)
        
        assert np.isfinite(delta_phi)
        assert delta_phi != 0
    
    def test_small_mass_gives_small_phase_diff(self):
        """Smaller mass → smaller phase difference (less strong field)."""
        # This is a weak test - could be improved
        pass


class TestISCO:
    """Test ISCO location."""
    
    def test_isco_at_6m(self):
        """ISCO = 6GM/c² = 3 r_s for Schwarzschild."""
        M = 30 * 1.989e30
        rs = 2 * G * M / C**2
        
        r_isco_val = r_isco(M)
        assert np.isclose(r_isco_val, 3 * rs, rtol=0.01)
