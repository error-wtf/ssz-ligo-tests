"""SSZ waveform - forward model to h(t) with placeholder functions."""
import numpy as np
from typing import Optional


def apply_phase_deformation(h_gr_f: np.ndarray,
                          freqs: np.ndarray,
                          delta_psi: np.ndarray) -> np.ndarray:
    """Apply phase deformation to GR waveform in frequency domain.
    
    Formula: h_SSZ(f) = h_GR(f) × exp(i × delta_psi(f))
    """
    return h_gr_f * np.exp(1j * delta_psi)


def apply_amplitude_deformation(h_gr_f: np.ndarray,
                                delta_amp: np.ndarray) -> np.ndarray:
    """Apply amplitude deformation to GR waveform.
    
    Formula: h_SSZ(f) = h_GR(f) × (1 + delta_amp(f))
    """
    return h_gr_f * (1 + delta_amp)


def h_ssz_from_gr(h_gr_f: np.ndarray,
                  freqs: np.ndarray,
                  delta_psi: Optional[np.ndarray] = None,
                  delta_amp: Optional[np.ndarray] = None) -> np.ndarray:
    """Construct SSZ waveform from GR waveform.
    
    Args:
        h_gr_f: GR waveform in frequency domain
        freqs: frequency array
        delta_psi: phase correction (optional)
        delta_amp: amplitude correction (optional)
    
    Returns:
        SSZ waveform in frequency domain
    """
    if delta_psi is None:
        delta_psi = np.zeros_like(freqs)
    if delta_amp is None:
        delta_amp = np.zeros_like(freqs)

    h = apply_amplitude_deformation(h_gr_f, delta_amp)
    h = apply_phase_deformation(h, freqs, delta_psi)
    return h


def delta_psi_ssz(freqs: np.ndarray,
                  M: float,
                  rs: float,
                  kappa: Optional[float] = None) -> np.ndarray:
    """SSZ phase correction δΨ_SSZ(f).
    
    Source: NOT_IN_CORPUS - Missing equation.
    
    Raises:
        NotImplementedError: Formula not locked from SSZ corpus.
    """
    raise NotImplementedError(
        "SSZ phase correction formula δΨ_SSZ(f) not locked from source corpus. "
        "See SSZ_FORWARD_MODEL_EQUATION_GAPS.md: MISSING_FORWARD_EQUATION."
    )


def delta_amp_ssz(freqs: np.ndarray,
                  M: float,
                  rs: float,
                  kappa: Optional[float] = None) -> np.ndarray:
    """SSZ amplitude correction δA_SSZ(f).

    Source: NOT_IN_CORPUS - Missing equation.

    Raises:
        NotImplementedError: Formula not locked from SSZ corpus.
    """
    raise NotImplementedError(
        "SSZ amplitude correction formula δA_SSZ(f) not locked from source corpus. "
        "See SSZ_FORWARD_MODEL_EQUATION_GAPS.md: MISSING_FORWARD_EQUATION."
    )


def h_plus_h_cross_ssz(freqs, M, rs, **kwargs):
    """Placeholder: h+/hx SSZ. Not yet implemented."""
    raise NotImplementedError("h_plus_h_cross_ssz: not yet locked from corpus.")


def waveform_transform_ssz(h_gr_f, freqs, M, rs, **kwargs):
    """Placeholder: full SSZ waveform transform."""
    raise NotImplementedError("waveform_transform_ssz: not yet locked from corpus.")


def h_ssz_frequency_domain(freqs, M, rs, **kwargs):
    """Placeholder: h_SSZ(f) frequency domain."""
    raise NotImplementedError("h_ssz_frequency_domain: not yet locked from corpus.")


def strain_from_detector_response(h_ssz_f, detector, **kwargs):
    """Placeholder: project SSZ waveform through detector response."""
    raise NotImplementedError("strain_from_detector_response: not yet locked from corpus.")


def h_ssz_real_domain_or_placeholder(freqs, M, rs, **kwargs):
    """Placeholder: real-domain SSZ strain."""
    raise NotImplementedError("h_ssz_real_domain_or_placeholder: not yet locked from corpus.")
