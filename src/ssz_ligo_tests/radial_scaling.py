"""Radial Scaling Gauge (RSG) - Phase accounting through strong-to-weak transition.

Based on RSG paper insight: radial scaling is a geometric phase accounting factor,
not a new local dynamics law. Analogous to tortoise/Regge-Wheeler coordinates.
"""
import numpy as np
from scipy import integrate
from typing import Union
from .constants import PHI, G, C
from .ssz_core import xi_weak, xi_strong, get_xi, d_ssz, d_gr_schwarzschild


def s_scale(xi: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """SSZ scaling factor s(r) = 1 + Ξ(r) = 1/D(r).
    
    Source: SSZ Book Ch.1
    Formula: s = 1 + Ξ = 1/D
    """
    return 1 + xi


def rho_rsg(r: float, 
            rs: float, 
            phi: float = PHI) -> float:
    """Radial Scaling Gauge coordinate - tortoise-like.
    
    First version: proxy using integrated D(r)/s(r) weight.
    
    Concept: Transform difficult strong radial structure into
    stretched computational coordinate while preserving physics
    in scaling factor.
    
    Formula: ρ(r) = ∫ D(r')/s(r') dr'  [approximate proxy]
    
    Args:
        r: radial coordinate
        rs: Schwarzschild radius
        phi: golden ratio (default PHI)
    
    Returns:
        RSG coordinate value
    """
    # Proxy implementation: integrate from r_s to r
    # This is a simplified first version, not the final claim
    
    def integrand(r_prime):
        xi = get_xi(r_prime, rs)
        d = d_ssz(xi)
        s = s_scale(xi)
        return d / s
    
    # Numerical integration from rs to r
    if r <= rs:
        return 0.0
    
    result, _ = integrate.quad(integrand, rs, r, limit=100)
    return result


def drho_dr(r: float, rs: float) -> float:
    """Phase accounting weight dρ/dr.
    
    Formula: dρ/dr = D(r)/s(r) = D(r) × (1 + Ξ(r))^{-1} = D(r)²
    
    Wait: s = 1 + Ξ = 1/D, so D/s = D/(1/D) = D²
    
    So: dρ/dr = D(r)²
    """
    xi = get_xi(r, rs)
    d = d_ssz(xi)
    return d ** 2


def phase_accounting_factor_ssz(r: float, rs: float) -> float:
    """SSZ phase accounting factor at radius r.
    
    This determines how much phase accumulates per radial step
    in SSZ compared to flat spacetime.
    
    Formula: A_SSZ(r) = D(r)² / s(r) = D(r)³
    
    Actually: Let's be careful.
    From inspiral: we need D²/s⁴ for rdot, D²/s² for P_GW
    
    For phase accounting: the key is how coordinate time relates to proper time.
    """
    xi = get_xi(r, rs)
    d = d_ssz(xi)
    s = s_scale(xi)
    # Phase accumulation factor
    return (d ** 2) / (s ** 2)


def phase_accounting_factor_gr(r: float, rs: float) -> float:
    """GR phase accounting factor at radius r.
    
    For comparison with SSZ.
    """
    d_gr = d_gr_schwarzschild(r, rs)
    # In GR, s effectively = 1 (no extra scaling)
    return d_gr ** 2


def blend_strong_to_weak(r: float, rs: float) -> float:
    """Hermite C² transition from strong to weak field.
    
    Returns blending weight w(r):
    - w = 1 at r = 0.8 r_s (pure strong)
    - w = 0 at r = 2.2 r_s (pure weak)
    
    From SSZ Book Ch.1: Hermite C² interpolation in blend zone.
    """
    ratio = r / rs
    
    if ratio < 0.8:
        return 1.0  # Pure strong
    elif ratio > 2.2:
        return 0.0  # Pure weak
    else:
        # Blend zone: Hermite interpolation
        # t goes from 1 (inner) to 0 (outer)
        t = (2.2 - ratio) / (2.2 - 0.8)
        # Hermite basis h00 = 3t² - 2t³
        return 3 * t**2 - 2 * t**3


def xi_blended(r: float, rs: float) -> float:
    """Blended Ξ(r) with smooth strong-to-weak transition.
    
    Uses Hermite C² interpolation in blend zone.
    """
    xi_s = xi_strong(r, rs)
    xi_w = xi_weak(r, rs)
    w = blend_strong_to_weak(r, rs)
    return w * xi_s + (1 - w) * xi_w


def delta_rsg_coordinate(r: float, rs: float) -> float:
    """Difference in RSG coordinate: ρ_SSZ - ρ_GR proxy.
    
    This quantifies how much the radial structure differs
    between SSZ and GR.
    """
    # Simple proxy: integrated difference in phase accounting
    def integrand(rp):
        a_ssz = phase_accounting_factor_ssz(rp, rs)
        a_gr = phase_accounting_factor_gr(rp, rs)
        return a_ssz - a_gr
    
    if r <= rs:
        return 0.0
    
    result, _ = integrate.quad(integrand, rs, r, limit=100)
    return result
