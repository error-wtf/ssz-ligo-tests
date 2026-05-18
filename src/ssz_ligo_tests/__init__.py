"""SSZ-LIGO Forward Model Test Suite v0.2

Forward model from SSZ (Segmented Spacetime) to LIGO detector strain
through radial scaling gauge and inspiral phase accumulation.

Anti-circularity:
- Model lock before data comparison
- Strain/residuals only
- Strong field → RSG → phase → weak field → interferometer
"""

__version__ = "0.2.0"

# Constants
from .constants import (  # noqa: F401
    PHI, XI_MAX, D_MIN, N0,
    C, G, M_SUN,
    REGIME_WEAK_THRESHOLD, REGIME_STRONG_THRESHOLD
)

# Core SSZ equations
from .ssz_core import (  # noqa: F401
    schwarzschild_radius,
    xi_max, d_min,
    xi_weak, xi_strong,
    d_ssz, d_gr_schwarzschild, d_gr_schwarzschild as d_gr,
    d_ssz as ssz_scaling,
    ssz_delta_d, regime_label, get_xi,
    validate_positive_radius, validate_units_basic
)

# Radial Scaling Gauge
from .radial_scaling import (  # noqa: F401
    s_scale,
    rho_rsg,
    drho_dr,
    phase_accounting_factor_ssz,
    phase_accounting_factor_gr,
    blend_strong_to_weak,
    xi_blended,
    delta_rsg_coordinate
)

# Inspiral forward model
from .ssz_inspiral import (  # noqa: F401
    gw_power_gr,
    gw_power_ssz,
    rdot_gr,
    rdot_ssz,
    orbital_frequency,
    dphi_dr,
    accumulated_phase,
    delta_phase_ssz_minus_gr,
    r_isco
)

# Phase mapping
from .ssz_phase import (  # noqa: F401
    frequency_to_radius_proxy,
    radius_to_frequency_proxy,
    delta_phi_at_radius,
    phase_correction_window,
    apply_ssz_phase_to_waveform,
    estimate_phase_magnitude
)

# Ringdown (BLOCKED - conflicting sources)
from .ssz_ringdown import (  # noqa: F401
    RINGDOWN_MODEL_STATUS,
    CONFLICTING_SOURCES,
    get_ringdown_conflict_report,
    check_ringdown_usable,
    ringdown_damped_sinusoid,
    ssz_ringdown_frequency_shift,
    ssz_ringdown_tau_shift,
    epsilon_220_from_corpus
)

# Waveform deformation
from .ssz_waveform import (  # noqa: F401
    h_plus_h_cross_ssz,
    waveform_transform_ssz,
    delta_psi_ssz,
    delta_amp_ssz,
    h_ssz_frequency_domain,
    strain_from_detector_response,
    h_ssz_real_domain_or_placeholder
)

# Detector and likelihood
from .detector_response import (  # noqa: F401
    detector_response,
    time_shift_signal,
    combine_detectors
)

# Forward model
from .forward_model import SSZForwardModel  # noqa: F401

from .likelihood import (  # noqa: F401
    residual,
    noise_weighted_inner_product,
    log_likelihood_gaussian,
    delta_log_likelihood
)

# Anti-circularity
from .anti_circularity import (  # noqa: F401
    CircularityStatus,
    classify_observable_source,
    check_independence,
    flag_posterior_self_consistency_risk,
    FORBIDDEN_POSTERIOR_FIELDS,
    ALLOWED_OBSERVABLES
)

# Equation registry
from .equation_registry import (  # noqa: F401
    Equation, EquationStatus,
    LOCKED_CORE_EQUATIONS,
    MISSING_FORWARD_EQUATIONS,
    get_locked_equations,
    get_missing_equations,
    check_ready_for_numerical_test,
    generate_registry_report
)

__all__ = [
    # Version
    '__version__',

    # Constants
    'PHI', 'XI_MAX', 'D_MIN', 'N0', 'C', 'G', 'M_SUN',

    # Core
    'schwarzschild_radius', 'xi_weak', 'xi_strong', 'd_ssz', 'd_gr_schwarzschild',
    'get_xi', 'regime_label', 's_scale',

    # Radial Scaling
    'rho_rsg', 'drho_dr', 'phase_accounting_factor_ssz', 'phase_accounting_factor_gr',
    'blend_strong_to_weak', 'xi_blended', 'delta_rsg_coordinate',

    # Inspiral
    'gw_power_ssz', 'rdot_ssz', 'orbital_frequency', 'dphi_dr',
    'accumulated_phase', 'delta_phase_ssz_minus_gr', 'r_isco',

    # Phase
    'frequency_to_radius_proxy', 'delta_psi_ssz', 'phase_correction_window',
    'apply_ssz_phase_to_waveform', 'estimate_phase_magnitude',

    # Ringdown (BLOCKED)
    'RINGDOWN_MODEL_STATUS', 'CONFLICTING_SOURCES', 'get_ringdown_conflict_report',
    'check_ringdown_usable',

    # Detector
    'detector_response',

    # Likelihood
    'residual', 'log_likelihood_gaussian', 'delta_log_likelihood',

    # Anti-circularity
    'CircularityStatus', 'check_independence',
    'FORBIDDEN_POSTERIOR_FIELDS', 'ALLOWED_OBSERVABLES',

    # Registry
    'EquationStatus', 'get_locked_equations', 'get_missing_equations',
    'check_ready_for_numerical_test',
]
