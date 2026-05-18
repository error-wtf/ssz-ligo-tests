"""Derived SSZ phase correction deltaPsi_SSZ(f).

FORMULA_STATUS: DERIVED_V0_PROXY
SOURCE:
  P_GW_SSZ = P_GW_GR * D^2/s^2  (SSZ Book Ch.31, ssz_inspiral.py)
  rdot_SSZ = rdot_GR * D^2/s^4  (SSZ Book Ch.31, ssz_inspiral.py)
  r(f) = (GM/(pi*f)^2)^(1/3)    (Newtonian proxy)

DERIVATION:
  dphi_dr_SSZ / dphi_dr_GR = s^4/D^2 = (1+Xi)^6
  deltaPsi(f) ~ dphi_dr_GR * [(1+Xi(r(f)))^6 - 1] * |dr/df|

DIMENSIONAL CHECK:
  dphi_dr [rad/m], |dr/df| [m/Hz] => deltaPsi [rad/Hz] summed over df => [rad]

ASSUMPTIONS: leading-order Newtonian, circular orbit, no spin, no fit.
READY_FOR_REAL_CLAIM: NO
"""
import numpy as np
from typing import Optional, Tuple
from .constants import G, C
from .ssz_core import get_xi
from .radial_scaling import s_scale

FORMULA_STATUS = "DERIVED_V0_PROXY"
READY_FOR_REAL_CLAIM = "NO"


def _r_orbit(f_hz: float, M_kg: float) -> float:
    return (G * M_kg / (np.pi * f_hz) ** 2) ** (1.0 / 3.0)


def _rs(M_kg: float) -> float:
    return 2.0 * G * M_kg / C ** 2


def _correction_factor(r: float, rs: float) -> float:
    """(1+Xi)^6 - 1 from rdot ratio s^4/D^2."""
    from .ssz_core import d_ssz
    xi = get_xi(r, rs)
    return (1.0 + xi) ** 6 - 1.0


def delta_psi_ssz_v0(
    freqs: np.ndarray,
    M_total_kg: float,
    mu_kg: float,
    branch: str = "g2_decay",
    r_start: Optional[float] = None,
    r_end: Optional[float] = None,
) -> Tuple[np.ndarray, dict]:
    """Derived SSZ V0 phase correction deltaPsi_SSZ(f).

    FORMULA_STATUS: DERIVED_V0_PROXY
    READY_FOR_REAL_CLAIM: NO
    """
    freqs = np.asarray(freqs, dtype=float)
    if np.any(freqs <= 0):
        raise ValueError("All frequencies must be positive.")

    rs = _rs(M_total_kg)
    r_orb = np.array([_r_orbit(f, M_total_kg) for f in freqs])

    rdot_gr = (
        -64.0 * G ** 3 * M_total_kg ** 2 * mu_kg
        / (5.0 * C ** 5 * r_orb ** 3)
    )
    omega = np.sqrt(G * M_total_kg / r_orb ** 3)
    dphi_dr_gr = omega / np.abs(rdot_gr)

    corr = np.array([_correction_factor(r, rs) for r in r_orb])
    dr_df = np.abs(np.gradient(r_orb, freqs))
    delta_psi = dphi_dr_gr * corr * dr_df

    if not np.all(np.isfinite(delta_psi)):
        raise RuntimeError("deltaPsi contains non-finite values.")

    meta = {
        "FORMULA_STATUS": FORMULA_STATUS,
        "READY_FOR_REAL_CLAIM": READY_FOR_REAL_CLAIM,
        "branch": branch,
        "rs_m": rs,
        "r_over_rs_min": float(r_orb.min() / rs),
        "r_over_rs_max": float(r_orb.max() / rs),
        "deltaPsi_min_rad": float(delta_psi.min()),
        "deltaPsi_max_rad": float(delta_psi.max()),
        "deltaPsi_median_rad": float(np.median(delta_psi)),
    }
    return delta_psi, meta
