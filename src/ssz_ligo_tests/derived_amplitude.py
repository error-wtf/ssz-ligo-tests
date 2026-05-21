"""Derived SSZ amplitude correction deltaA_SSZ(f).

FORMULA_STATUS: DERIVED_V0_PROXY
SOURCE:
  P_GW_SSZ / P_GW_GR = D(r)^2 / s(r)^2  (SSZ Book Ch.31, ssz_inspiral.py)
  Amplitude scales as sqrt(power): A_SSZ/A_GR = D(r)/s(r)
  => deltaA_SSZ(r) = D(r)/s(r) - 1 = D(r)^2 - 1  (since s=1/D)
     Wait: D/s = D * D = D^2 (since s=1/D)
     deltaA = D^2 - 1  (negative: amplitude suppressed in strong field)

DERIVATION:
  P_SSZ = P_GR * (D/s)^2 = P_GR * D^4   (since D=1/s)
  Wait: D^2/s^2 = D^2 * D^2 = D^4
  A_SSZ/A_GR = sqrt(P_SSZ/P_GR) = D^2
  deltaA = D^2 - 1

DIMENSIONAL CHECK:
  D = 1/(1+Xi) in (0,1] => D^2 in (0,1] => deltaA in [-1,0] (suppression)

SIGN: deltaA < 0 means amplitude is suppressed relative to GR (D < 1 in strong field).
      In LIGO band (weak field), Xi ~ rs/(2r) << 1, D ~ 1, deltaA ~ -Xi^2 ~ tiny.

ASSUMPTIONS: circular orbit, leading-order, no fit.
READY_FOR_REAL_CLAIM: NO
"""
import numpy as np
from typing import Tuple
from .constants import G, C
from .ssz_core import get_xi

FORMULA_STATUS = "DERIVED_V1"
READY_FOR_REAL_CLAIM = "NO"


def _r_orbit(f_hz: float, M_kg: float) -> float:
    return (G * M_kg / (np.pi * f_hz) ** 2) ** (1.0 / 3.0)


def _rs(M_kg: float) -> float:
    return 2.0 * G * M_kg / C ** 2


def delta_a_ssz_v0(
    freqs: np.ndarray,
    M_total_kg: float,
    branch: str = "g2_decay",
) -> Tuple[np.ndarray, dict]:
    """Derived SSZ V0 amplitude correction deltaA_SSZ(f).

    deltaA(f) = D(r(f))^2 - 1

    FORMULA_STATUS: DERIVED_V0_PROXY
    READY_FOR_REAL_CLAIM: NO

    Args:
        freqs: frequency array [Hz], must be positive
        M_total_kg: total binary mass [kg]
        branch: Xi_strong branch label (informational, g2_decay operative)

    Returns:
        (deltaA, metadata)
        deltaA: amplitude correction array, dimensionless
    """
    freqs = np.asarray(freqs, dtype=float)
    if np.any(freqs <= 0):
        raise ValueError("All frequencies must be positive.")

    rs = _rs(M_total_kg)
    r_orb = np.array([_r_orbit(f, M_total_kg) for f in freqs])

    xi_vals = np.array([get_xi(r, rs) for r in r_orb])
    d_vals = 1.0 / (1.0 + xi_vals)
    delta_a = d_vals ** 2 - 1.0

    if not np.all(np.isfinite(delta_a)):
        raise RuntimeError("deltaA contains non-finite values.")

    meta = {
        "FORMULA_STATUS": FORMULA_STATUS,
        "READY_FOR_REAL_CLAIM": READY_FOR_REAL_CLAIM,
        "branch": branch,
        "rs_m": rs,
        "r_over_rs_min": float(r_orb.min() / rs),
        "r_over_rs_max": float(r_orb.max() / rs),
        "deltaA_min": float(delta_a.min()),
        "deltaA_max": float(delta_a.max()),
        "deltaA_median": float(np.median(delta_a)),
        "D_at_f_max": float(d_vals[np.argmax(freqs)]),
        "D_at_f_min": float(d_vals[np.argmin(freqs)]),
        "source_equation": "deltaA = D(r)^2 - 1, D=1/(1+Xi)",
    }
    return delta_a, meta
