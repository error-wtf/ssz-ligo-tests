"""SSZ core equations - canonical implementation."""
import numpy as np
from typing import Union

# SSZ Constants - from SSZ_BOOK_DE_CLEAN.md
PHI = (1 + np.sqrt(5)) / 2  # Golden ratio ≈ 1.618
XI_MAX = 1 - np.exp(-PHI)   # ≈ 0.802
D_MIN = 1 / (1 + XI_MAX)    # ≈ 0.555
N0 = 4  # Base segmentation


def xi_weak(r: Union[float, np.ndarray],
            rs: float) -> Union[float, np.ndarray]:
    """Weak field regime formula.
    
    Source: SSZ_BOOK_DE_CLEAN.md Ch.1
    Formula: Ξ_weak(r) = r_s / (2r)
    Valid for: r/r_s > 2.2 (outside blend zone)
    """
    return rs / (2 * r)


def xi_strong(r: Union[float, np.ndarray],
              rs: float,
              phi: float = PHI) -> Union[float, np.ndarray]:
    """Strong field regime formula with saturation.
    
    Source: SSZ_BOOK_DE_CLEAN.md Ch.1
    Formula: Ξ_strong(r) = min(1 - exp(-φr_s / r), Ξ_max)
    Valid for: r_s/r < 1.8 (inside blend zone)
    """
    xi = 1 - np.exp(-phi * r / rs)
    return np.minimum(xi, XI_MAX)


def xi_blend(r: float, rs: float) -> float:
    """Blend zone interpolation (Hermite C^2).
    
    Source: SSZ_BOOK_DE_CLEAN.md Ch.1
    Zone: 0.8 ≤ r/r_s ≤ 2.2
    """
    t = (r - 0.8 * rs) / (2.2 * rs - 0.8 * rs)
    t = np.clip(t, 0, 1)
    # Hermite basis functions
    h00 = 2*t**3 - 3*t**2 + 1
    h01 = -2*t**3 + 3*t**2
    xi_inner = xi_strong(0.8 * rs, rs)
    xi_outer = xi_weak(2.2 * rs, rs)
    return h00 * xi_inner + h01 * xi_outer


def D_ssz(xi: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """SSZ time dilation factor.
    
    Source: SSZ_BOOK_DE_CLEAN.md Ch.1
    Formula: D(r) = 1 / (1 + Ξ(r))
    
    Key property: D_min = 0.555 at r = r_s
    """
    return 1 / (1 + xi)


def D_gr(r: Union[float, np.ndarray],
         rs: float) -> Union[float, np.ndarray]:
    """GR time dilation factor (Schwarzschild).
    
    Formula: D_GR(r) = sqrt(1 - r_s/r)
    
    Key property: D_GR(r_s) = 0 (infinite redshift)
    """
    x = 1 - rs / r
    return np.sqrt(np.maximum(x, 0))


def get_xi(r: float, rs: float) -> float:
    """Get Ξ(r) with automatic regime detection."""
    ratio = r / rs
    if ratio < 0.8:
        return xi_strong(r, rs)
    elif ratio > 2.2:
        return xi_weak(r, rs)
    else:
        return xi_blend(r, rs)


def ssz_scaling(r: Union[float, np.ndarray],
                rs: float) -> Union[float, np.ndarray]:
    """SSZ scaling function D_SSZ(r)."""
    xi = get_xi(r, rs) if np.isscalar(r) else np.array([get_xi(ri, rs) for ri in r])
    return D_ssz(xi)
