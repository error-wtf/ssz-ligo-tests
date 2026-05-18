"""SSZ Forward Model - anti-circularity enforcing wrapper."""
import numpy as np
from .ssz_ringdown import ssz_ringdown_frequency_shift, ssz_ringdown_tau_shift
from .ssz_phase import frequency_to_radius_proxy
from .ssz_core import xi_weak, d_ssz


class SSZForwardModel:
    """Unified SSZ forward model with parameter locking (anti-circularity)."""

    def __init__(self):
        self.epsilon_220 = None
        self.eta_220 = None
        self.kappa_phase = None
        self.kappa_amp = None
        self._lock_sources = {}

    def lock_epsilon_220(self, value: float, source: str):
        self.epsilon_220 = value
        self._lock_sources["epsilon_220"] = source

    def lock_eta_220(self, value: float, source: str):
        self.eta_220 = value
        self._lock_sources["eta_220"] = source

    def lock_kappa_phase(self, value: float, source: str):
        self.kappa_phase = value
        self._lock_sources["kappa_phase"] = source

    def lock_kappa_amp(self, value: float, source: str):
        self.kappa_amp = value
        self._lock_sources["kappa_amp"] = source

    def ssz_ringdown_frequency_shift(self, f_gr: float) -> float:
        """Compute SSZ ringdown frequency shift. Requires epsilon_220 locked."""
        if self.epsilon_220 is None:
            raise ValueError(
                "epsilon_220 not locked: call lock_epsilon_220() first."
            )
        return ssz_ringdown_frequency_shift(f_gr, epsilon_220=self.epsilon_220)

    def ssz_ringdown_tau_shift(self, tau_gr: float) -> float:
        """Compute SSZ ringdown damping shift. Requires eta_220 locked."""
        if self.eta_220 is None:
            raise ValueError(
                "eta_220 not locked: call lock_eta_220() first."
            )
        return ssz_ringdown_tau_shift(tau_gr, eta_220=self.eta_220)

    def ssz_phase_deformation(self,
                              freqs: np.ndarray,
                              M: float,
                              rs: float) -> np.ndarray:
        """Phase deformation delta_psi per frequency. Requires kappa_phase."""
        if self.kappa_phase is None:
            raise ValueError(
                "kappa_phase not locked: call lock_kappa_phase() first."
            )
        radii = np.array([frequency_to_radius_proxy(f, M) for f in freqs])
        xi_vals = np.array([xi_weak(r, rs) for r in radii])
        d_vals = np.array([d_ssz(xi) for xi in xi_vals])
        return self.kappa_phase * (1 - d_vals)

    def ssz_amplitude_deformation(self,
                                  freqs: np.ndarray,
                                  M: float,
                                  rs: float) -> np.ndarray:
        """Amplitude deformation delta_amp per frequency. Requires kappa_amp."""
        if self.kappa_amp is None:
            raise ValueError(
                "kappa_amp not locked: call lock_kappa_amp() first."
            )
        radii = np.array([frequency_to_radius_proxy(f, M) for f in freqs])
        xi_vals = np.array([xi_weak(r, rs) for r in radii])
        d_vals = np.array([d_ssz(xi) for xi in xi_vals])
        return self.kappa_amp * (1 - d_vals)

    @staticmethod
    def detector_response(h_plus: np.ndarray,
                          h_cross: np.ndarray,
                          F_plus: float,
                          F_cross: float) -> np.ndarray:
        """Project polarizations to detector strain: h = F+ h+ + Fx hx."""
        return F_plus * h_plus + F_cross * h_cross

    @staticmethod
    def residual(data: np.ndarray, model_vec: np.ndarray) -> np.ndarray:
        """Strain residual: r = data - model."""
        return data - model_vec

    @staticmethod
    def noise_weighted_inner_product(a: np.ndarray,
                                     b: np.ndarray,
                                     psd: np.ndarray,
                                     freqs: np.ndarray) -> float:
        """Real noise-weighted inner product <a|b> = Re(sum a* b / S_n) df."""
        df = freqs[1] - freqs[0] if len(freqs) > 1 else 1.0
        ip = np.sum(np.conj(a) * b / psd).real * df
        return float(ip)

    def log_likelihood(self,
                       data: np.ndarray,
                       model_vec: np.ndarray,
                       psd: np.ndarray,
                       freqs: np.ndarray) -> float:
        """Gaussian log-likelihood: -0.5 <r|r>."""
        r = self.residual(data, model_vec)
        return -0.5 * self.noise_weighted_inner_product(r, r, psd, freqs)
