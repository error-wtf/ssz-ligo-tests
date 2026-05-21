"""Derived SSZ V0 waveform: h_SSZ(f) = h_GR * (1+deltaA) * exp(i*deltaPsi).

FORMULA_STATUS: DERIVED_V0_PROXY
SOURCE:
  - derived_phase.py (deltaPsi)
  - derived_amplitude.py (deltaA)
  - formula_compendium.md §B.1, §B.7

CONSTRUCTION:
  h_SSZ(f) = h_GR_control(f) * [1 + deltaA_V0(f)] * exp(i * deltaPsi_V0(f))

  h_GR_control is an analytic template only, not a fitted PE waveform.

READY_FOR_REAL_CLAIM: NO
SSZ_SUPPORT_CLAIM_MADE: NO
SSZ_FALSIFICATION_CLAIM_MADE: NO
"""
import numpy as np
from typing import Tuple
from .derived_phase import delta_psi_ssz_v0
from .derived_amplitude import delta_a_ssz_v0

FORMULA_STATUS = "DERIVED_V1"
READY_FOR_REAL_CLAIM = "NO"


def apply_ssz_v0_to_frequency_waveform(
    h_gr_f: np.ndarray,
    freqs: np.ndarray,
    M_total_kg: float,
    mu_kg: float,
    branch: str = "g2_decay",
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Apply SSZ V0 correction to GR frequency-domain waveform.

    h_SSZ(f) = h_GR(f) * [1 + deltaA_V0(f)] * exp(i * deltaPsi_V0(f))

    FORMULA_STATUS: DERIVED_V0_PROXY
    READY_FOR_REAL_CLAIM: NO

    Args:
        h_gr_f: complex GR waveform array, frequency domain
        freqs: frequency array [Hz], same shape as h_gr_f
        M_total_kg: total binary mass [kg]
        mu_kg: reduced mass [kg]
        branch: Xi branch label

    Returns:
        (h_ssz_f, delta_psi, delta_a, metadata)
    """
    freqs = np.asarray(freqs, dtype=float)
    h_gr_f = np.asarray(h_gr_f, dtype=complex)

    if h_gr_f.shape != freqs.shape:
        raise ValueError("h_gr_f and freqs must have the same shape.")

    mask = freqs > 0
    delta_psi = np.zeros_like(freqs)
    delta_a = np.zeros_like(freqs)

    if np.any(mask):
        dp, meta_p = delta_psi_ssz_v0(
            freqs[mask], M_total_kg, mu_kg, branch=branch
        )
        delta_psi[mask] = dp

        da, meta_a = delta_a_ssz_v0(
            freqs[mask], M_total_kg, branch=branch
        )
        delta_a[mask] = da

    h_ssz_f = h_gr_f * (1.0 + delta_a) * np.exp(1j * delta_psi)

    if not np.all(np.isfinite(np.abs(h_ssz_f))):
        raise RuntimeError("h_ssz_f contains non-finite values.")

    metadata = {
        "FORMULA_STATUS": FORMULA_STATUS,
        "READY_FOR_REAL_CLAIM": READY_FOR_REAL_CLAIM,
        "SSZ_SUPPORT_CLAIM_MADE": "NO",
        "SSZ_FALSIFICATION_CLAIM_MADE": "NO",
        "branch": branch,
        "M_total_kg": M_total_kg,
        "mu_kg": mu_kg,
        "deltaPsi_min_rad": float(delta_psi.min()),
        "deltaPsi_max_rad": float(delta_psi.max()),
        "deltaA_min": float(delta_a.min()),
        "deltaA_max": float(delta_a.max()),
        "h_ssz_amplitude_ratio": float(
            np.mean(np.abs(h_ssz_f[mask]))
            / (np.mean(np.abs(h_gr_f[mask])) + 1e-40)
        ),
    }
    return h_ssz_f, delta_psi, delta_a, metadata
