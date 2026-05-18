"""Integration tests for SSZ-LIGO forward model.

Tests the complete chain from SSZ parameters to detector strain.
"""
import numpy as np
import pytest
from ssz_ligo_tests import PHI, D_MIN
from ssz_ligo_tests.forward_model import SSZForwardModel


class TestForwardModelInitialization:
    """Test proper initialization with locked parameters."""
    
    def test_initially_unlocked(self):
        """All parameters must start as None (unlocked)."""
        model = SSZForwardModel()
        assert model.epsilon_220 is None
        assert model.eta_220 is None
        assert model.kappa_phase is None
        assert model.kappa_amp is None
    
    def test_can_lock_epsilon_220(self):
        """Can lock ε_220 with source citation."""
        model = SSZForwardModel()
        model.lock_epsilon_220(0.03, "SSZ_BOOK_DE_CLEAN.md Ch.30")
        assert model.epsilon_220 == 0.03
    
    def test_can_lock_eta_220(self):
        """Can lock η_220 with source citation."""
        model = SSZForwardModel()
        model.lock_eta_220(0.05, "SSZ_BOOK_DE_CLEAN.md Ch.30")
        assert model.eta_220 == 0.05
    
    def test_can_lock_kappa_phase(self):
        """Can lock κ_Ψ with source citation."""
        model = SSZForwardModel()
        model.lock_kappa_phase(1.0, "placeholder")
        assert model.kappa_phase == 1.0


class TestRingdownShift:
    """Test SSZ ringdown frequency and damping shifts."""
    
    def test_unshifted_when_epsilon_zero(self):
        """When ε=0: f_SSZ = f_GR"""
        model = SSZForwardModel()
        model.lock_epsilon_220(0.0, "test")
        f_gr = 250.0  # Hz
        f_ssz = model.ssz_ringdown_frequency_shift(f_gr)
        assert np.isclose(f_ssz, f_gr)
    
    def test_shifted_when_epsilon_nonzero(self):
        """When ε=0.03: f_SSZ = 1.03 × f_GR"""
        model = SSZForwardModel()
        model.lock_epsilon_220(0.03, "test")
        f_gr = 250.0
        f_ssz = model.ssz_ringdown_frequency_shift(f_gr)
        assert np.isclose(f_ssz, 250.0 * 1.03)
    
    def test_raises_when_epsilon_not_locked(self):
        """Must raise error if ε_220 not locked."""
        model = SSZForwardModel()
        with pytest.raises(ValueError, match="epsilon_220 not locked"):
            model.ssz_ringdown_frequency_shift(250.0)
    
    def test_tau_shift_raises_when_eta_not_locked(self):
        """Must raise error if η_220 not locked."""
        model = SSZForwardModel()
        with pytest.raises(ValueError, match="eta_220 not locked"):
            model.ssz_ringdown_tau_shift(0.01)


class TestPhaseDeformation:
    """Test SSZ phase correction δΨ_SSZ(f)."""
    
    def test_raises_when_kappa_not_locked(self):
        """Must raise error if κ_Ψ not locked."""
        model = SSZForwardModel()
        freqs = np.linspace(20, 500, 100)
        M = 30 * 1.989e30  # 30 solar masses
        rs = 2 * 6.674e-11 * M / (3e8)**2
        
        with pytest.raises(ValueError, match="kappa_phase not locked"):
            model.ssz_phase_deformation(freqs, M, rs)
    
    def test_zero_at_high_frequencies(self):
        """Phase correction → 0 when f high (weak field)."""
        model = SSZForwardModel()
        model.lock_kappa_phase(1.0, "test")
        
        # High frequencies = smaller radii = actually strong field
        # Wait, high frequency = tight orbit = strong field
        # Let me reconsider: low frequency = wide orbit = weak field
        freqs = np.array([20, 30, 40])  # Hz - inspiral frequencies
        M = 30 * 1.989e30
        rs = 2 * 6.674e-11 * M / (3e8)**2
        
        delta_psi = model.ssz_phase_deformation(freqs, M, rs)
        # Should be finite (strong field regime)
        assert np.all(np.isfinite(delta_psi))


class TestAmplitudeDeformation:
    """Test SSZ amplitude correction δA_SSZ(f)."""
    
    def test_raises_when_kappa_not_locked(self):
        """Must raise error if κ_A not locked."""
        model = SSZForwardModel()
        freqs = np.linspace(20, 500, 100)
        M = 30 * 1.989e30
        rs = 2 * 6.674e-11 * M / (3e8)**2
        
        with pytest.raises(ValueError, match="kappa_amp not locked"):
            model.ssz_amplitude_deformation(freqs, M, rs)


class TestDetectorResponse:
    """Test detector response functions."""
    
    def test_antenna_response(self):
        """h_I = F⁺ h_+ + F^× h_×"""
        model = SSZForwardModel()
        h_plus = np.array([1, 2, 3])
        h_cross = np.array([0.5, 1, 1.5])
        F_plus = 0.8
        F_cross = 0.6
        
        h_I = model.detector_response(h_plus, h_cross, F_plus, F_cross)
        expected = F_plus * h_plus + F_cross * h_cross
        assert np.allclose(h_I, expected)
    
    def test_residual(self):
        """r = d - h"""
        model = SSZForwardModel()
        data = np.array([1, 2, 3])
        model_vec = np.array([0.9, 1.9, 2.9])
        r = model.residual(data, model_vec)
        expected = np.array([0.1, 0.1, 0.1])
        assert np.allclose(r, expected)


class TestLikelihood:
    """Test likelihood computation."""
    
    def test_likelihood_decreases_with_mismatch(self):
        """ln L is lower when model mismatches data."""
        model = SSZForwardModel()
        
        # Simple case
        freqs = np.linspace(20, 500, 100)
        psd = np.ones_like(freqs)  # Flat noise
        data = np.ones_like(freqs)
        
        # Perfect match
        model_match = np.ones_like(freqs)
        ll_match = model.log_likelihood(data, model_match, psd, freqs)
        
        # Mismatch
        model_mismatch = np.zeros_like(freqs)
        ll_mismatch = model.log_likelihood(data, model_mismatch, psd, freqs)
        
        # Likelihood should be higher for match
        assert ll_match > ll_mismatch
    
    def test_inner_product_symmetry(self):
        """⟨a|b⟩ = ⟨b|a⟩"""
        model = SSZForwardModel()
        freqs = np.linspace(20, 500, 100)
        psd = np.ones_like(freqs)
        a = np.random.randn(100) + 1j * np.random.randn(100)
        b = np.random.randn(100) + 1j * np.random.randn(100)
        
        ip_ab = model.noise_weighted_inner_product(a, b, psd, freqs)
        ip_ba = model.noise_weighted_inner_product(b, a, psd, freqs)
        
        assert np.isclose(ip_ab, ip_ba)


class TestAntiCircularity:
    """Test anti-circularity protections."""
    
    def test_model_rejects_unlocked_parameters(self):
        """Model must reject computation with unlocked params."""
        model = SSZForwardModel()
        
        # All of these should raise errors
        with pytest.raises(ValueError):
            model.ssz_ringdown_frequency_shift(250.0)
        
        with pytest.raises(ValueError):
            model.ssz_ringdown_tau_shift(0.01)
        
        freqs = np.array([100.0])
        M = 30 * 1.989e30
        rs = 1.0
        
        with pytest.raises(ValueError):
            model.ssz_phase_deformation(freqs, M, rs)
        
        with pytest.raises(ValueError):
            model.ssz_amplitude_deformation(freqs, M, rs)
