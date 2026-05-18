"""Likelihood functions for SSZ-LIGO model comparison."""
import numpy as np


def residual(data: np.ndarray, model: np.ndarray) -> np.ndarray:
    """Compute residual: r = d - h.
    
    Args:
        data: observed data
        model: model prediction
    
    Returns:
        residual array
    """
    return data - model


def noise_weighted_inner_product(a: np.ndarray, 
                                 b: np.ndarray, 
                                 psd: np.ndarray, 
                                 freqs: np.ndarray) -> float:
    """Noise-weighted inner product ⟨a|b⟩.
    
    Formula: 4 Re ∫ a*(f) b(f) / S_n(f) df
    
    Args:
        a: first signal/array
        b: second signal/array
        psd: power spectral density
        freqs: frequency array
    
    Returns:
        inner product value
    """
    integrand = np.conjugate(a) * b / psd
    return 4 * np.real(np.trapz(integrand, freqs))


def log_likelihood_gaussian(data: np.ndarray, 
                           model: np.ndarray, 
                           psd: np.ndarray, 
                           freqs: np.ndarray) -> float:
    """Log-likelihood for Gaussian noise.
    
    Formula: ln L = -½ ⟨d - h | d - h⟩
    
    Args:
        data: observed data
        model: model waveform
        psd: noise power spectral density
        freqs: frequency array
    
    Returns:
        log-likelihood value
    """
    r = residual(data, model)
    return -0.5 * noise_weighted_inner_product(r, r, psd, freqs)


def delta_log_likelihood(data: np.ndarray, 
                        model_a: np.ndarray, 
                        model_b: np.ndarray, 
                        psd: np.ndarray, 
                        freqs: np.ndarray) -> float:
    """Difference in log-likelihood between two models.
    
    Formula: Δln L = ln L(data|A) - ln L(data|B)
    
    Positive value means model A is preferred.
    """
    ll_a = log_likelihood_gaussian(data, model_a, psd, freqs)
    ll_b = log_likelihood_gaussian(data, model_b, psd, freqs)
    return ll_a - ll_b
