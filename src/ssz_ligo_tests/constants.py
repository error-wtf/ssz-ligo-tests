"""SSZ constants - canonical values from SSZ_BOOK_DE_CLEAN.md."""
import numpy as np

# Mathematical constants
PHI: float = (1 + np.sqrt(5)) / 2  # Golden ratio φ ≈ 1.618033988749895

# Physical constants (SI)
C: float = 299792458  # Speed of light [m/s]
G: float = 6.67430e-11  # Gravitational constant [m³ kg⁻¹ s⁻²]
M_SUN: float = 1.98847e30  # Solar mass [kg]

# SSZ derived constants
XI_MAX: float = 1 - np.exp(-PHI)  # ≈ 0.801688... (from Book Ch.1)
D_MIN: float = 1 / (1 + XI_MAX)   # ≈ 0.555... (from Book Ch.1)
N0: int = 4  # Base segmentation (from Book Ch.1)

# ---------------------------------------------------------------------------
# Regime / formula-domain boundaries — SOURCE-LOCKED, never silently hardcode
# Source: formula_compendium.md §B.2
#         regime_and_formula_domain_clarification.md §System 1 / System 2
# ---------------------------------------------------------------------------

# Formula-domain boundaries (which Xi formula is operative)
BLEND_START: float = 1.8   # r/rs below → g2 domain (saturation form)
BLEND_END:   float = 2.2   # r/rs above → g1 domain (Xi_weak = rs/2r)

# Physical regime thresholds (interpretive label, NOT formula selector)
STRONG_FIELD_R_OVER_RS_MAX: float = 10.0   # above → "weak" physical regime
WEAK_FIELD_R_OVER_RS_MIN:   float = 10.0   # alias for clarity
PHOTON_SPHERE_R_OVER_RS:    float = 1.387  # universal intersection r*/rs

# Legacy aliases (kept for backward compatibility — do not use in new code)
REGIME_WEAK_THRESHOLD: float = BLEND_END          # 2.2 — formula domain boundary
REGIME_STRONG_THRESHOLD: float = BLEND_START       # 1.8 — formula domain boundary

# ---------------------------------------------------------------------------
# epsilon_220 branch lock
# Source: docs/EPSILON_220_BRANCH_LOCK.md
#         ssz-complete-documentation/06_STRONG_FIELD/qnm_spectrum.md
# ---------------------------------------------------------------------------

# None = not locked; no ringdown claim allowed until author resolves conflict
EPSILON_220_LOCKED = None

EPSILON_220_BRANCHES = {
    "A_v51_ch30": {
        "value": 0.03,
        "status": "PARTIAL_EXPLORATORY",
        "origin": "SSZ_BOOK_DE_CLEAN.md Ch.30 / V51 PDF",
        "ligo_usable": False,
    },
    "B_dmin_squared": {
        "value": D_MIN ** 2,
        "status": "SUPERSEDED_OR_DIFFERENT_REGIME",
        "origin": "Older D_min^2 scaling interpretation",
        "ligo_usable": False,
    },
    "C_photon_sphere": {
        "value": 0.39,
        "status": "DISCARDED_FOR_LIGO_STRAIN_TEST",
        "origin": "qnm_spectrum.md: 1/D(r*) at r*=1.387 rs",
        "ligo_usable": False,
    },
}
