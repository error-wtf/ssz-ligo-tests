"""SSZ inspiral - real forward model from orbital mechanics to phase.

This is the first true forward bridge: not posterior, but
Orbit/Energy loss → Phase → Waveform.

Source: SSZ Book Ch.31-32 (Lagrangian/Wirkungsprinzip section)
"""
import numpy as np
from scipy import integrate
from typing import Tuple
from .constants import G, C
from .ssz_core import get_xi, d_ssz
from .radial_scaling import s_scale


def gw_power_gr(r: float, 
                M: float, 
                mu: float) -> float:
    """GR gravitational wave power (luminosity).
    
    Standard quadrupole formula for circular orbit:
    P_GR = (32/5) * (G⁴/c⁵) * (M²μ²/r⁴) * (1 + ... higher order)
    
    Leading order:
    P_GR = (32/5) * (G/c)⁵ * (M²μ²/r⁴) * (M/r)
    
    Actually, standard formula is:
    P_GW = (32/5) * (G⁴/c⁵) * (M³μ²/r⁵) for circular orbit
    
    Args:
        r: orbital separation
        M: total mass
        mu: reduced mass
    
    Returns:
        GW power [W]
    """
    # Leading order quadrupole formula
    # P = (32/5) * (G/c)^5 * (M^3 * mu^2) / r^5
    # But this needs careful factor
    
    # More standard: P = (32/5) * (G^4 / c^5) * (M^3 * mu^2) / r^5
    return (32/5) * (G**4 / C**5) * (M**3 * mu**2) / (r**5)


def gw_power_ssz(r: float, 
                M: float, 
                mu: float, 
                rs: float) -> float:
    """SSZ gravitational wave power with radial scaling correction.
    
    From SSZ Book Ch.31-32:
    P_GW^SSZ = P_GW^GR × D(r)² / s(r)²
    
    This accounts for the modified strong-field geometry.
    
    Args:
        r: orbital separation
        M: total mass
        mu: reduced mass
        rs: Schwarzschild radius
    
    Returns:
        SSZ GW power [W]
    """
    p_gr = gw_power_gr(r, M, mu)
    
    # SSZ correction
    xi = get_xi(r, rs)
    d = d_ssz(xi)
    s = s_scale(xi)
    
    correction = (d ** 2) / (s ** 2)
    return p_gr * correction


def rdot_gr(r: float, 
            M: float, 
            mu: float) -> float:
    """GR radial inspiral rate (dr/dt).
    
    From energy balance: dE/dt = -P_GW
    E = -G*M*mu/(2r) for Newtonian
    
    So: dE/dr = G*M*mu/(2r²)
    dr/dt = (dE/dt) / (dE/dr) = -P_GW / (G*M*mu/(2r²))
          = -P_GW × (2r²) / (G*M*mu)
    """
    p_gr = gw_power_gr(r, M, mu)
    dedr = G * M * mu / (2 * r**2)  # dE/dr (positive, so use carefully)
    
    # dr/dt = -P / (dE/dr) with sign
    # Actually E = -G*M*mu/(2r), so dE = G*M*mu/(2r²) dr
    # So dr = (2r²)/(G*M*mu) dE
    # And dE/dt = -P, so dr/dt = -P × (2r²)/(G*M*mu)
    return -p_gr * (2 * r**2) / (G * M * mu)


def rdot_ssz(r: float, 
            M: float, 
            mu: float, 
            rs: float) -> float:
    """SSZ radial inspiral rate with correction.
    
    From SSZ Book Ch.31-32:
    rdot_SSZ = rdot_GR × D(r)² / s(r)⁴
    
    This is a stronger correction than P_GW because it involves
    the dynamics, not just the radiation.
    
    Args:
        r: orbital separation
        M: total mass
        mu: reduced mass
        rs: Schwarzschild radius
    
    Returns:
        SSZ radial inspiral rate [m/s]
    """
    rdot_gr_val = rdot_gr(r, M, mu)
    
    # SSZ correction
    xi = get_xi(r, rs)
    d = d_ssz(xi)
    s = s_scale(xi)
    
    correction = (d ** 2) / (s ** 4)
    return rdot_gr_val * correction


def orbital_frequency(r: float, M: float) -> float:
    """Keplerian orbital frequency.
    
    Formula: Ω(r) = √(GM/r³)
    
    Args:
        r: orbital separation
        M: total mass
    
    Returns:
        Angular frequency [rad/s]
    """
    return np.sqrt(G * M / r**3)


def dphi_dr(r: float, 
            M: float, 
            mu: float, 
            rs: float,
            model: str = "ssz") -> float:
    """Orbital phase accumulation per radial step.
    
    Formula: dφ/dr = Ω(r) / ṙ(r)
    
    Args:
        r: orbital separation
        M: total mass
        mu: reduced mass
        rs: Schwarzschild radius
        model: "ssz" or "gr"
    
    Returns:
        dφ/dr [rad/m]
    """
    omega = orbital_frequency(r, M)
    
    if model == "ssz":
        rdot = rdot_ssz(r, M, mu, rs)
    else:  # "gr"
        rdot = rdot_gr(r, M, mu)
    
    # Avoid division by very small numbers near ISCO
    if abs(rdot) < 1e-10:
        return 0.0
    
    return omega / rdot


def accumulated_phase(r_start: float,
                     r_end: float,
                     M: float,
                     mu: float,
                     rs: float,
                     model: str = "ssz") -> float:
    """Accumulated orbital phase from r_start to r_end.
    
    Formula: φ = ∫_{r_start}^{r_end} (dφ/dr) dr
    
    Args:
        r_start: starting orbital separation
        r_end: ending orbital separation (smaller)
        M: total mass
        mu: reduced mass
        rs: Schwarzschild radius
        model: "ssz" or "gr"
    
    Returns:
        Accumulated phase [rad]
    """
    def integrand(r):
        return dphi_dr(r, M, mu, rs, model)
    
    # Integration from r_start to r_end (going inward, so r_end < r_start)
    result, _ = integrate.quad(integrand, r_start, r_end, limit=200)
    return result


def delta_phase_ssz_minus_gr(r_start: float,
                             r_end: float,
                             M: float,
                             mu: float,
                             rs: float) -> float:
    """Difference in accumulated phase: SSZ - GR.
    
    This is the key observable for LIGO phase comparison.
    
    Returns:
        Δφ = φ_SSZ - φ_GR [rad]
    """
    phi_ssz = accumulated_phase(r_start, r_end, M, mu, rs, "ssz")
    phi_gr = accumulated_phase(r_start, r_end, M, mu, rs, "gr")
    return phi_ssz - phi_gr


def r_isco(M: float) -> float:
    """Innermost stable circular orbit (ISCO) for Schwarzschild.
    
    Formula: r_ISCO = 6GM/c² = 3 r_s
    
    Args:
        M: total mass
    
    Returns:
        ISCO radius [m]
    """
    return 6 * G * M / C**2
