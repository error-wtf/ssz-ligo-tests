"""Anti-circularity engine for SSZ-LIGO tests.

Ensures no circular reasoning in test design.
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, List


class CircularityStatus(Enum):
    VALID_INDEPENDENT = "VALID_INDEPENDENT"
    PARTIALLY_COUPLED = "PARTIALLY_COUPLED"
    CIRCULARITY_RISK = "CIRCULARITY_RISK"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


@dataclass
class ObservableCheck:
    observable: str
    source: str
    is_model_inferred: bool
    circularity_status: CircularityStatus
    risk_explanation: str


# FORBIDDEN OBSERVABLES (posterior fields)
FORBIDDEN_POSTERIOR_FIELDS = [
    "H1_only/f",
    "H1_only/m",
    "H1_only/chi",
    "H1_only/m1",
    "H1_only/m2",
    "H1_only/a1",
    "H1_only/a2",
    "L1_only/f",
    "L1_only/m",
    "L1_only/chi",
    "posterior/f",
    "posterior/m",
    "posterior/chi",
]

# ALLOWED OBSERVABLES (strain-based)
ALLOWED_OBSERVABLES = [
    "H1/strain_data",
    "H1/residual",
    "H1/power_spectrum",
    "L1/strain_data",
    "L1/residual",
    "L1/power_spectrum",
    "data/h_t",
    "data/h_f",
]


def classify_observable_source(source_description: str) -> CircularityStatus:
    """Classify observable based on source description.

    INVALID: posterior fields, pSEOBNR, online_posterior_samples
    CIRCULARITY_RISK: ringdown posteriors, qnmrf, metafile PSDs
    VALID_INDEPENDENT: raw strain, PSD from strain, analytic templates
    """
    source = source_description.lower()

    # Explicitly invalid: posterior parameter fields
    _invalid_keywords = [
        "online_posterior_samples",
        "pseobnr",
        "pseobnrv",
        "pca_tiger",
        "pca_fti",
        "tiger",
        "fti",
    ]
    if any(kw in source for kw in _invalid_keywords):
        return CircularityStatus.INVALID

    if any(f in source for f in ["h1_only", "l1_only"]):
        if any(field in source for field in ["/f", "/m", "/chi", "/m1", "/m2"]):
            return CircularityStatus.INVALID

    if "posterior" in source:
        _post_fields = ["/f", "/m", "/chi", "_f_", "_m_", "_chi", "_final"]
        if any(field in source for field in _post_fields):
            return CircularityStatus.INVALID
        return CircularityStatus.CIRCULARITY_RISK

    # Circularity risk: ringdown/QNM posteriors
    _circularity_keywords = [
        "ringdown/f_220",
        "ringdown/tau_220",
        "qnmrf",
        "metafile/psd",
        "bilby",
    ]
    if any(kw in source for kw in _circularity_keywords):
        return CircularityStatus.CIRCULARITY_RISK

    # Valid independent: raw strain, PSD from strain, analytic templates
    if ("strain" in source or "residual" in source or "raw" in source
            or "power_spectrum" in source or "psd" in source):
        return CircularityStatus.VALID_INDEPENDENT

    if "model" in source and "inferred" in source:
        return CircularityStatus.CIRCULARITY_RISK

    return CircularityStatus.UNKNOWN


def check_independence(prediction_source: str, 
                      measured_source: str, 
                      reference_source: str) -> CircularityStatus:
    """Check independence of prediction, measurement, and reference.
    
    Anti-circularity rule: Never use same data product to define and validate prediction.
    """
    # Same source = circular
    if prediction_source == measured_source:
        return CircularityStatus.CIRCULARITY_RISK
    
    # Posterior field measured from model that uses same reference = circular
    if "posterior" in measured_source and reference_source in prediction_source:
        return CircularityStatus.CIRCULARITY_RISK
    
    # Strain is independent
    if "strain" in measured_source:
        return CircularityStatus.VALID_INDEPENDENT
    
    return CircularityStatus.UNKNOWN


def flag_posterior_self_consistency_risk(observable: str) -> Optional[str]:
    """Flag risk if observable is from self-consistency check.
    
    Example: R_f = f_measured / f_Kerr is circular if f_measured came from Kerr fit.
    """
    if observable in FORBIDDEN_POSTERIOR_FIELDS:
        return (
            f"{observable} is a POSTERIOR FIELD from model fit. "
            "Using it assumes the model used to infer it. "
            "This is CIRCULAR if used to test that same model."
        )
    return None


def produce_anti_circularity_record(test_name: str,
                                  prediction_eq: str,
                                  prediction_source: str,
                                  measured_obs: str,
                                  measured_source: str,
                                  reference_model: str) -> Dict:
    """Produce complete anti-circularity record for a test."""
    
    independence = check_independence(prediction_source, measured_source, reference_model)
    posterior_risk = flag_posterior_self_consistency_risk(measured_obs)
    
    record = {
        "test_name": test_name,
        "prediction_equation": prediction_eq,
        "prediction_source": prediction_source,
        "measured_observable": measured_obs,
        "measured_source": measured_source,
        "reference_model": reference_model,
        "independence_status": independence.value,
        "posterior_risk": posterior_risk,
        "usable": independence == CircularityStatus.VALID_INDEPENDENT and posterior_risk is None
    }
    
    return record


def validate_test_design(test_design: Dict) -> List[str]:
    """Validate complete test design for circularity risks."""
    issues = []
    
    for test_name, design in test_design.items():
        record = produce_anti_circularity_record(
            test_name=test_name,
            prediction_eq=design.get("prediction_eq", ""),
            prediction_source=design.get("prediction_source", ""),
            measured_obs=design.get("measured_obs", ""),
            measured_source=design.get("measured_source", ""),
            reference_model=design.get("reference_model", "")
        )
        
        if not record["usable"]:
            issues.append(
                f"{test_name}: {record['independence_status']}"
            )
            if record["posterior_risk"]:
                issues.append(f"  -> {record['posterior_risk']}")
    
    return issues


def print_forbidden_observables():
    """Print list of forbidden observables."""
    print("FORBIDDEN OBSERVABLES (posterior fields):")
    for obs in FORBIDDEN_POSTERIOR_FIELDS:
        print(f"  - {obs}")
    print("\nALLOWED OBSERVABLES (strain-based):")
    for obs in ALLOWED_OBSERVABLES:
        print(f"  - {obs}")
