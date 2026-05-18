"""SSZ-LIGO test suite: Forward model from SSZ to detector strain.

This package implements the SSZ-LIGO forward model for testing 
segmented spacetime predictions against gravitational wave data.

Anti-circularity principles:
- Never use posterior f, m, χ as direct observables
- Always lock SSZ equations before data comparison
- Use strain/residuals only, not inferred parameters
"""

__version__ = "0.1.0"

from .ssz_core import (
    PHI, XI_MAX, D_MIN, N0,
    xi_weak, xi_strong, xi_blend,
    D_ssz, D_gr,
    get_xi, ssz_scaling
)

from .forward_model import SSZForwardModel

__all__ = [
    # Constants
    'PHI', 'XI_MAX', 'D_MIN', 'N0',
    # Core functions
    'xi_weak', 'xi_strong', 'xi_blend',
    'D_ssz', 'D_gr', 'get_xi', 'ssz_scaling',
    # Forward model
    'SSZForwardModel',
]
