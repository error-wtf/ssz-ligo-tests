"""SSZ-LIGO Forward Model v0.1

Forward model from SSZ theory to detector strain h(t).

Source: SSZ_BOOK_DE_CLEAN.md (Ch.1, Ch.30)
Anti-circularity: This module does NOT use posterior fields.
"""
import numpy as np
from typing import Optional
from .ssz_core import D_ssz, D_gr, xi_strong


class SSZForwardModel:
    """SSZ forward model for LIGO strain."""

    def __init__(self):
        # These MUST be locked from SSZ corpus before use
        self.epsilon_220: Optional[float] = None
        self.eta_220: Optional[float] = None
        self.kappa_phase: Optional[float] = None
        self.kappa_amp: Optional[float] = None

    def lock_epsilon_220(self, value: float, source: str):
        """Lock ε_220 from SSZ corpus source."""
        self.epsilon_220 = value
        self._epsilon_source = source

    def lock_eta_220(self, value: float, source: str):
        """Lock η_220 from SSZ corpus source."""
        self.eta_220 = value
        self._eta_source = source

    def lock_kappa_phase(self, value: float, source: str):
        """Lock κ_Ψ from SSZ corpus source."""
        self.kappa_phase = value
        self._kappa_phase_source = source

    def lock_kappa_amp(self, value: float, source: str):
        """Lock κ_A from SSZ corpus source."""
        self.kappa_amp = value
        self._kappa_amp_source = source

    def frequency_to_radius_proxy(self, f: np.ndarray,
                                   M: float) -> np.ndarray:
        """Newtonian proxy: r(f) for inspiral frequencies.
        
        Formula: r = (GM/(πf)^2)^(1/3)
        This is ONLY a proxy - true SSZ relation needs full orbital calc.
        """
        G = 6.67430e-11
        return (G * M / (np.pi * f)**2) ** (1/3)

    def ssz_phase_deformation(self, freqs: np.ndarray,
                              M: float,
                              rs: float) -> np.ndarray:
        """SSZ phase correction δΨ_SSZ(f).
        
        Formula: δΨ = κ_Ψ × W(f) × (D_SSZ - D_GR)
        
        Raises:
            ValueError: if kappa_phase not locked from corpus
        """
        if self.kappa_phase is None:
            raise ValueError(
                "kappa_phase not locked from SSZ corpus. "
                "Use lock_kappa_phase() with canonical source."
            )

        r = self.frequency_to_radius_proxy(freqs, M)
        # Window function: active only in strong field
        W = np.where(r < 3 * rs, 1.0, 0.0)  # Simple step

        delta_D = D_ssz(xi_strong(r, rs)) - D_gr(r, rs)
        return self.kappa_phase * W * delta_D

    def ssz_amplitude_deformation(self, freqs: np.ndarray,
                                   M: float,
                                   rs: float) -> np.ndarray:
        """SSZ amplitude correction δA_SSZ(f).
        
        Raises:
            ValueError: if kappa_amp not locked from corpus
        """
        if self.kappa_amp is None:
            raise ValueError(
                "kappa_amp not locked from SSZ corpus. "
                "Use lock_kappa_amp() with canonical source."
            )

        r = self.frequency_to_radius_proxy(freqs, M)
        W = np.where(r < 3 * rs, 1.0, 0.0)

        delta_D = D_ssz(xi_strong(r, rs)) - D_gr(r, rs)
        return self.kappa_amp * W * delta_D

    def ssz_ringdown_frequency_shift(self, f_gr: float) -> float:
        """SSZ QNM frequency shift.
        
        Formula: f_SSZ = f_GR × (1 + ε_220)
        
        Book Ch.30 mentions: ~3% but D_min² ≈ 31%
        This ambiguity MUST be resolved before use.
        """
        if self.epsilon_220 is None:
            raise ValueError(
                "epsilon_220 not locked from SSZ corpus. "
                "Book Ch.30 mentions ~3% but D_min²≈31%. "
                "Use lock_epsilon_220() with unambiguous source."
            )
        return f_gr * (1 + self.epsilon_220)

    def ssz_ringdown_tau_shift(self, tau_gr: float) -> float:
        """SSZ QNM damping time shift.
        
        Formula: τ_SSZ = τ_GR × (1 + η_220)
        """
        if self.eta_220 is None:
            raise ValueError(
                "eta_220 not locked from SSZ corpus. "
                "Use lock_eta_220() with canonical source."
            )
        return tau_gr * (1 + self.eta_220)

    def detector_response(self,
                          h_plus: np.ndarray,
                          h_cross: np.ndarray,
                          F_plus: float,
                          F_cross: float) -> np.ndarray:
        """Detector antenna response.
        
        Formula: h_I = F⁺ h_+ + F^× h_×
        """
        return F_plus * h_plus + F_cross * h_cross

    def residual(self,
                 data: np.ndarray,
                 model: np.ndarray) -> np.ndarray:
        """Compute residual: r = d - h"""
        return data - model

    def noise_weighted_inner_product(self,
                                      a: np.ndarray,
                                      b: np.ndarray,
                                      psd: np.ndarray,
                                      freqs: np.ndarray) -> float:
        """Noise-weighted inner product ⟨a|b⟩.
        
        Formula: 4 Re ∫ a*(f) b(f) / S_n(f) df
        """
        integrand = np.conjugate(a) * b / psd
        return 4 * np.real(np.trapz(integrand, freqs))

    def log_likelihood(self,
                       data: np.ndarray,
                       model: np.ndarray,
                       psd: np.ndarray,
                       freqs: np.ndarray) -> float:
        """Log-likelihood for strain data.
        
        Formula: ln L = -½ ⟨d - h | d - h⟩
        """
        r = self.residual(data, model)
        return -0.5 * self.noise_weighted_inner_product(r, r, psd, freqs)
