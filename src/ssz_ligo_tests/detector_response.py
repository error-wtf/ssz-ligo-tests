"""Detector response for LIGO interferometers."""
import numpy as np
from typing import Tuple


def detector_response(h_plus: np.ndarray, 
                     h_cross: np.ndarray, 
                     F_plus: float, 
                     F_cross: float) -> np.ndarray:
    """Compute detector response for given polarization.
    
    Formula: h_I = F⁺ h_+ + F^× h_×
    
    Args:
        h_plus: plus polarization waveform
        h_cross: cross polarization waveform
        F_plus: plus antenna pattern
        F_cross: cross antenna pattern
    
    Returns:
        Detector strain response
    """
    return F_plus * h_plus + F_cross * h_cross


def time_shift_signal(signal: np.ndarray, 
                     dt: float, 
                     sample_rate: float) -> np.ndarray:
    """Apply time shift to signal.
    
    Args:
        signal: input signal array
        dt: time shift in seconds
        sample_rate: sampling rate in Hz
    
    Returns:
        Time-shifted signal
    """
    shift_samples = int(dt * sample_rate)
    if shift_samples == 0:
        return signal
    elif shift_samples > 0:
        return np.pad(signal, (shift_samples, 0), mode='constant')[:-shift_samples]
    else:
        return np.pad(signal, (0, -shift_samples), mode='constant')[-shift_samples:]


def combine_detectors(responses: list) -> np.ndarray:
    """Combine multiple detector responses (e.g., for network analysis).
    
    Args:
        responses: list of detector response arrays
    
    Returns:
        Combined response (sum)
    """
    return np.sum(responses, axis=0)


def antenna_pattern_h1(ra: float, dec: float, psi: float, gmst: float) -> Tuple[float, float]:
    """LIGO Hanford antenna pattern.
    
    Args:
        ra: right ascension [rad]
        dec: declination [rad]
        psi: polarization angle [rad]
        gmst: Greenwich mean sidereal time [rad]
    
    Returns:
        (F_plus, F_cross)
    """
    # Simplified - real implementation needs full detector geometry
    # This is a placeholder
    return 0.5, 0.5


def antenna_pattern_l1(ra: float, dec: float, psi: float, gmst: float) -> Tuple[float, float]:
    """LIGO Livingston antenna pattern.
    
    Placeholder - needs full geometry.
    """
    return 0.5, 0.5
