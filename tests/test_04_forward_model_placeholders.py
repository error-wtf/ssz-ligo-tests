"""Test 04: Forward model placeholders must raise errors."""
import pytest
import numpy as np
from ssz_ligo_tests import (
    delta_psi_ssz, delta_amp_ssz,
    ssz_ringdown_frequency_shift, ssz_ringdown_tau_shift
)


class TestPhaseDeformationBlocked:
    """δΨ_SSZ(f) must raise NotImplementedError."""
    
    def test_delta_psi_raises_not_implemented(self):
        """Formula not locked → NotImplementedError."""
        freqs = np.linspace(20, 500, 100)
        M = 30 * 1.989e30
        rs = 1.0
        
        with pytest.raises(NotImplementedError) as exc_info:
            delta_psi_ssz(freqs, M, rs)
        
        assert "not locked" in str(exc_info.value).lower()


class TestAmplitudeDeformationBlocked:
    """δA_SSZ(f) must raise NotImplementedError."""
    
    def test_delta_amp_raises_not_implemented(self):
        """Formula not locked → NotImplementedError."""
        freqs = np.linspace(20, 500, 100)
        M = 30 * 1.989e30
        rs = 1.0
        
        with pytest.raises(NotImplementedError) as exc_info:
            delta_amp_ssz(freqs, M, rs)
        
        assert "not locked" in str(exc_info.value).lower()


class TestRingdownFrequencyShiftBlocked:
    """f_SSZ must raise ValueError if epsilon not locked."""
    
    def test_raises_when_epsilon_none(self):
        """ε_220 = None → ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ssz_ringdown_frequency_shift(250.0, epsilon_220=None)
        
        assert "not locked" in str(exc_info.value).lower()
    
    def test_ambiguity_mentioned(self):
        """Error should mention 3% vs 31% ambiguity."""
        with pytest.raises(ValueError) as exc_info:
            ssz_ringdown_frequency_shift(250.0)
        
        # Should mention the ambiguity
        error_str = str(exc_info.value)
        assert "3%" in error_str or "31%" in error_str or "ambiguous" in error_str.lower()
    
    def test_works_when_epsilon_locked(self):
        """Works if ε_220 explicitly provided."""
        f_ssz = ssz_ringdown_frequency_shift(250.0, epsilon_220=0.03)
        assert f_ssz == 250.0 * 1.03


class TestRingdownTauShiftBlocked:
    """τ_SSZ must raise ValueError if eta not locked."""
    
    def test_raises_when_eta_none(self):
        """η_220 = None → ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ssz_ringdown_tau_shift(0.01, eta_220=None)
        
        assert "not locked" in str(exc_info.value).lower()
    
    def test_works_when_eta_locked(self):
        """Works if η_220 explicitly provided."""
        tau_ssz = ssz_ringdown_tau_shift(0.01, eta_220=0.05)
        assert tau_ssz == 0.01 * 1.05
