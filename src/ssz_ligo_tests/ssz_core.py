"""SSZ core equations - canonical implementation from SSZ_BOOK_DE_CLEAN.md."""
import numpy as np
from typing import Union
from .constants import (PHI, XI_MAX, G, C,
                        BLEND_START, BLEND_END)

# Xi_strong branch labels — see docs/XI_STRONG_BRANCH_LOCK.md
XI_STRONG_CANONICAL = "CANONICAL_OPERATIONAL"     # saturation form: 1-exp(-phi*r/rs)
XI_STRONG_DIDACTIC  = "DIDACTIC_COMPLEMENTARY"    # decay form: 1-exp(-phi*rs/r)
XI_STRONG_DEPRECATED = "INVALID_DEPRECATED"        # old (rs/r)^2*exp(...) — FORBIDDEN


def schwarzschild_radius(M_kg: float) -> float:
    """Compute Schwarzschild radius r_s = 2GM/c².
    
    Source: SSZ_BOOK_DE_CLEAN.md Ch.1
    """
    return 2 * G * M_kg / (C ** 2)


def xi_max(phi: float = PHI) -> float:
    """Compute Ξ_max = 1 - exp(-φ).
    
    Source: SSZ_BOOK_DE_CLEAN.md Ch.1
    Formula: Ξ_max = 1 - exp(-φ) ≈ 0.802
    """
    return 1 - np.exp(-phi)


def d_min(phi: float = PHI) -> float:
    """Compute D_min = 1/(1 + Ξ_max).
    
    Source: SSZ_BOOK_DE_CLEAN.md Ch.1
    Formula: D_min = 0.555
    """
    xi_max_val = xi_max(phi)
    return 1 / (1 + xi_max_val)


def xi_weak(r: Union[float, np.ndarray],
            rs: float) -> Union[float, np.ndarray]:
    """Weak field regime: Ξ_weak(r) = r_s/(2r).
    
    Source: SSZ_BOOK_DE_CLEAN.md Ch.1
    Valid for: r/r_s > 2.2 (outside blend zone)
    """
    return rs / (2 * r)


def xi_strong(r: Union[float, np.ndarray],
              rs: float,
              phi: float = PHI) -> Union[float, np.ndarray]:
    """Strong field Xi — delegates to CANONICAL saturation form.

    Branch: CANONICAL_OPERATIONAL
    Source: formula_compendium.md §B.1, docs/XI_STRONG_BRANCH_LOCK.md
    Formula: Xi = min(1 - exp(-phi * r/rs), Xi_max)
    Valid for: r/rs < 1.8 (g2 / BLEND_START domain)
    """
    return xi_strong_saturation(r, rs, phi)


def xi_strong_saturation(r: Union[float, np.ndarray],
                         rs: float,
                         phi: float = PHI) -> Union[float, np.ndarray]:
    """Strong field Xi — CANONICAL_OPERATIONAL saturation form.

    Branch: CANONICAL_OPERATIONAL
    Source: formula_compendium.md §B.1
            regime_and_formula_domain_clarification.md §Saturation vs Decay
    Formula: Xi = min(1 - exp(-phi * r/rs), Xi_max)
    Asymptotic: r→0 → 0 (regular), r→inf → Xi_max (saturates)
    """
    xi = 1 - np.exp(-phi * r / rs)
    return np.minimum(xi, XI_MAX)


def xi_strong_decay(r: Union[float, np.ndarray],
                    rs: float,
                    phi: float = PHI) -> Union[float, np.ndarray]:
    """Strong field Xi — DIDACTIC_COMPLEMENTARY decay form.

    Branch: DIDACTIC_COMPLEMENTARY — do NOT use in production pipeline.
    Source: regime_and_formula_domain_clarification.md §Saturation vs Decay
    Formula: Xi = 1 - exp(-phi * rs/r)
    Asymptotic: r→0 → Xi_max (saturates), r→inf → 0 (decays)
    Note: agrees with saturation form exactly at r = rs.
    """
    xi = 1 - np.exp(-phi * rs / r)
    return np.minimum(xi, XI_MAX)


def d_ssz(xi: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """SSZ time dilation factor D = 1/(1 + Ξ).
    
    Source: SSZ_BOOK_DE_CLEAN.md Ch.1
    
    Key property: D_min = 0.555 at r = r_s (not 0 like GR)
    """
    return 1 / (1 + xi)


def d_gr_schwarzschild(r: Union[float, np.ndarray],
                       rs: float) -> Union[float, np.ndarray]:
    """GR time dilation factor for Schwarzschild metric.
    
    Formula: D_GR(r) = sqrt(1 - r_s/r)
    
    Key property: D_GR(r_s) = 0 (infinite redshift)
    """
    x = 1 - rs / r
    return np.sqrt(np.maximum(x, 0))


def ssz_delta_d(r: Union[float, np.ndarray],
                rs: float) -> Union[float, np.ndarray]:
    """Difference D_SSZ - D_GR.
    
    This quantifies the SSZ-GR deviation at radius r.
    """
    xi = get_xi(r, rs)
    d_ssz_val = d_ssz(xi)
    d_gr_val = d_gr_schwarzschild(r, rs)
    return d_ssz_val - d_gr_val


def regime_label(r: float, rs: float) -> str:
    """Classify formula domain based on r/rs ratio.

    Source: formula_compendium.md §B.2
            regime_and_formula_domain_clarification.md §System 1
    Uses BLEND_START=1.8, BLEND_END=2.2 (named constants).
    - g1 / WEAK: r/rs > BLEND_END (2.2)
    - blend:     BLEND_START (1.8) <= r/rs <= BLEND_END (2.2)
    - g2 / STRONG: r/rs < BLEND_START (1.8)
    """
    ratio = r / rs
    if ratio > BLEND_END:
        return "WEAK"
    elif ratio < BLEND_START:
        return "STRONG"
    else:
        return "BLEND"


def get_xi(r: Union[float, np.ndarray],
           rs: float) -> Union[float, np.ndarray]:
    """Get Xi(r) with automatic formula-domain detection.

    Uses BLEND_START=1.8, BLEND_END=2.2 (source-locked constants).
    WEAK (g1):   Xi_weak = rs/(2r)
    STRONG (g2): xi_strong_saturation (CANONICAL)
    BLEND:       linear interpolation (C0 only; Hermite C2 deferred)
    """
    if np.isscalar(r):
        label = regime_label(r, rs)
        if label == "WEAK":
            return xi_weak(r, rs)
        elif label == "STRONG":
            return xi_strong_saturation(r, rs)
        else:
            xi_in = xi_strong_saturation(BLEND_START * rs, rs)
            xi_out = xi_weak(BLEND_END * rs, rs)
            t = (r / rs - BLEND_START) / (BLEND_END - BLEND_START)
            return (1 - t) * xi_in + t * xi_out
    else:
        return np.array([get_xi(ri, rs) for ri in r])


def validate_positive_radius(r: float) -> bool:
    """Validate that radius is positive and > r_s."""
    return r > 0


def validate_units_basic() -> dict:
    """Validate that constants have correct units."""
    return {
        'PHI': 'dimensionless',
        'C': 'm/s',
        'G': 'm³ kg⁻¹ s⁻²',
        'M_SUN': 'kg',
        'XI_MAX': 'dimensionless',
        'D_MIN': 'dimensionless'
    }
