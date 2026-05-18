"""epsilon_220 branch registry.

FORMULA_STATUS: BLOCKED_BRANCH_CONFLICT
SOURCE: docs/EPSILON_220_BRANCH_LOCK.md, docs/EPSILON_220_DERIVATION_STATUS.md

Three conflicting branches exist in corpus.
No branch is selected as default for LIGO strain claim.
Usage of any branch requires explicit selection + preregistration.
"""
from .constants import D_MIN

FORMULA_STATUS = "BLOCKED_BRANCH_CONFLICT"
READY_FOR_REAL_CLAIM = "NO"

epsilon_220_for_real_ligo_claim = None
status = "BLOCKED_BRANCH_CONFLICT"

epsilon_220_exploratory_options = {
    "v51_ch30_3_percent": {
        "value": 0.03,
        "canonical_name": "qnm_freq_shift_v51_exploratory",
        "source": "SSZ_BOOK_DE_CLEAN.md Ch.30 / V51 PDF",
        "formula": "fundamental QNM shift, exploratory derivation",
        "regime": "weak-field QNM, testable via stacking or next-gen",
        "ligo_strain_compatible": False,
        "status": "PARTIAL_EXPLORATORY",
    },
    "dmin_squared_scale": {
        "value": D_MIN ** 2,
        "canonical_name": "amplitude_scale_dmin_squared",
        "source": "formula_compendium.md §B.7, D_min=0.555",
        "formula": "D_min^2 = 0.555^2 ~ 0.308 => ~31% downscale",  # noqa: E501
        "regime": "strong-field amplitude, different observable from freq shift",
        "ligo_strain_compatible": False,
        "status": "SUPERSEDED_OR_DIFFERENT_REGIME",
    },
    "photon_sphere_39_percent": {
        "value": 0.39,
        "canonical_name": "source_frame_qnm_ratio",
        "source": "qnm_spectrum.md, photon sphere r/rs~1.387",
        "formula": "f_SSZ/f_GR - 1 = 1/D(r*) - 1 at photon sphere",
        "regime": "source-frame strong-field QNM ratio, NOT LIGO strain",
        "ligo_strain_compatible": False,
        "status": "DISCARDED_FOR_LIGO_STRAIN_TEST",
    },
}

BRANCH_CONFLICT_SUMMARY = {
    "conflict": "Three branches give 3%, 31%, 39% — mutually inconsistent",
    "resolution": "BLOCKED until author selects canonical branch",
    "ligo_claim_allowed": False,
    "note": (
        "39% is a source-frame QNM ratio, not the LIGO strain observable. "
        "The correct observable is the strain phase deformation after "
        "Strong->Weak RSG mapping. This may yield a much smaller effect."
    ),
}
