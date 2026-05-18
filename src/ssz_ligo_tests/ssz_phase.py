"""SSZ phase - mapping orbital phase to frequency domain.

This connects the inspiral phase accumulation to LIGO observable δΨ(f).
"""
import numpy as np
from typing import Union
from .constants import G
from .ssz_inspiral import (
    orbital_frequency, 
    accumulated_phase,
    rdot_ssz,
    rdot_gr
)


def frequency_to_radius_proxy(f: Union[float, np.ndarray], 
                             M: float) -> Union[float, np.ndarray]:
    """Leading-order proxy: map GW frequency to orbital radius.
    
    For quadrupole radiation from circular orbit:
    f_GW = 2 × f_orb (for dominant mode)
    f_orb = Ω/(2π)
    
    So: f_GW = Ω/π = (1/π) × √(GM/r³)
    
    Inverting: r = (GM/(πf)²)^(1/3)
    
    Args:
        f: GW frequency [Hz]
        M: total mass [kg]
    
    Returns:
        Orbital separation proxy [m]
    """
    return (G * M / (np.pi * f)**2) ** (1/3)


def radius_to_frequency_proxy(r: float, M: float) -> float:
    """Leading-order proxy: map radius to GW frequency.
    
    Formula: f_GW = (1/π) × √(GM/r³)
    
    Args:
        r: orbital separation [m]
        M: total mass [kg]
    
    Returns:
        GW frequency [Hz]
    """
    return np.sqrt(G * M / r**3) / np.pi


def delta_phi_at_radius(r: float,
                       M: float,
                       mu: float,
                       rs: float) -> float:
    """Cumulative phase difference up to radius r.
    
    Integrates from a large outer radius down to r.
    
    Returns:
        Δφ(r) = φ_SSZ(r) - φ_GR(r) [rad]
    """
    # Start from a large radius where SSZ ≈ GR
    r_outer = 100 * rs  # Far enough that weak field applies
    
    from .ssz_inspiral import delta_phase_ssz_minus_gr
    return delta_phase_ssz_minus_gr(r_outer, r, M, mu, rs)


def delta_psi_ssz(freqs: np.ndarray,
                M: float,
                mu: float,
                rs: float) -> np.ndarray:
    """SSZ phase correction as function of frequency.
    
    This is the key observable for LIGO:
    δΨ_SSZ(f) = accumulated phase difference mapped to frequency
    
    Formula chain:
    f → r(f) → Δφ(r) → δΨ(f)
    
    Args:
        freqs: array of GW frequencies [Hz]
        M: total mass [kg]
        mu: reduced mass [kg]
        rs: Schwarzschild radius [m]
    
    Returns:
        Phase correction δΨ_SSZ(f) [rad]
    """
    delta_psi = np.zeros_like(freqs)
    
    for i, f in enumerate(freqs):
        # Map frequency to radius
        r = frequency_to_radius_proxy(f, M)
        
        # Get phase difference at this radius
        delta_psi[i] = delta_phi_at_radius(r, M, mu, rs)
    
    return delta_psi


def phase_correction_window(freqs: np.ndarray,
                           f_start: float = 20.0,
                           f_end: float = 500.0) -> np.ndarray:
    """Window function to apply phase correction only in relevant band.
    
    SSZ effects are relevant in strong field (late inspiral).
    Window is active from f_start to f_end.
    
    Returns:
        Window array W(f)
    """
    window = np.ones_like(freqs)
    
    # Low frequency cutoff
    window[freqs < f_start * 0.8] = 0.0
    
    # Smooth transition at low end
    mask_low = (freqs >= f_start * 0.8) & (freqs < f_start)
    window[mask_low] = (freqs[mask_low] - f_start * 0.8) / (f_start * 0.2)
    
    # High frequency cutoff (near merger)
    window[freqs > f_end] = 0.0
    
    return window


def apply_ssz_phase_to_waveform(h_gr_f: np.ndarray,
                               freqs: np.ndarray,
                               M: float,
                               mu: float,
                               rs: float) -> np.ndarray:
    """Apply SSZ phase correction to GR waveform.
    
    Formula: h_SSZ(f) = h_GR(f) × exp(i × δΨ_SSZ(f) × W(f))
    
    Args:
        h_gr_f: GR waveform in frequency domain
        freqs: frequency array [Hz]
        M: total mass [kg]
        mu: reduced mass [kg]
        rs: Schwarzschild radius [m]
    
    Returns:
        SSZ waveform in frequency domain
    """
    # Compute phase correction
    delta_psi = delta_psi_ssz(freqs, M, mu, rs)
    
    # Apply window
    window = phase_correction_window(freqs)
    delta_psi_windowed = delta_psi * window
    
    # Apply to waveform
    return h_gr_f * np.exp(1j * delta_psi_windowed)


def estimate_phase_magnitude(f_ref: float = 100.0,
                             M_solar: float = 30.0,
                             q: float = 1.0) -> float:
    """Estimate magnitude of SSZ phase correction at reference frequency.
    
    Quick estimate for order-of-magnitude assessment.
    
    Args:
        f_ref: reference frequency [Hz]
        M_solar: total mass in solar masses
        q: mass ratio (m1/m2)
    
    Returns:
        |δΨ| at f_ref [rad]
    """
    M = M_solar * 1.989e30
    mu = M * q / (1 + q)**2  # Reduced mass
    rs = 2 * G * M / 299792458**2
    
    delta_psi = delta_psi_ssz(np.array([f_ref]), M, mu, rs)
    return abs(delta_psi[0])
