#!/usr/bin/env python3
"""
PHASE 3 - REPRODUCTION READINESS PLAN
LIGO GW240925/GW250207 Data Release

OBJECTIVE: Prepare safe, reproducible plan for notebook execution
NO notebook execution yet - only planning
"""

from pathlib import Path
from datetime import datetime

ROOT = Path("E:/clone/ligo-gw240925-gw250207-release")
NOTEBOOK_DIR = ROOT / "03_NOTEBOOK_RUNS"
COMPARISON_DIR = ROOT / "04_COMPARISONS"
INVENTORY_DIR = ROOT / "02_INVENTORY"
LOGS_DIR = ROOT / "06_WINDSURF_LOGS"

# Ensure directories exist
for d in [NOTEBOOK_DIR, COMPARISON_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Output files
reproduction_plan = NOTEBOOK_DIR / "NOTEBOOK_REPRODUCTION_PLAN.md"
env_plan = NOTEBOOK_DIR / "PYTHON_ENVIRONMENT_PLAN.md"
cal_comparison_plan = COMPARISON_DIR / "CALIBRATION_COMPARISON_PLAN.md"
posterior_comparison_plan = COMPARISON_DIR / "POSTERIOR_COMPARISON_PLAN.md"
gr_test_plan = COMPARISON_DIR / "GR_TEST_AND_RINGDOWN_COMPARISON_PLAN.md"
log_file = LOGS_DIR / "PHASE_3_REPRODUCTION_READINESS_LOG.md"

log_content = []
def log(msg):
    print(msg)
    log_content.append(f"{datetime.now().isoformat()} - {msg}")

log("=== PHASE 3 REPRODUCTION READINESS START ===")

# 1. Notebook Reproduction Plan
with open(reproduction_plan, 'w', encoding='utf-8') as f:
    f.write("""# Notebook Reproduction Plan

**Generated:** {timestamp}

## Objective
Reproduce official LIGO notebooks in controlled manner before any SSZ analysis.

## Data Structure Overview

Based on inventory, the release contains:

### Primary Data Products
- **GW240925-C00-Strain.tar**: 2.5 GB - Raw strain data (uncalibrated)
- **calibration.tar.gz**: 484 KB - Calibration priors
- **cal_env.tar.gz**: 8.6 KB - Calibration envelope
- **combined_samples.tar.gz**: 10.2 MB - Posterior samples
- **ringdown.tar.gz**: 830 MB - Ringdown/QNM analysis
- **residuals.tar.gz**: 2.9 MB - Residual products

### Analysis Notebooks (expected in notebook.tar.gz)
- calibration-monitoring.ipynb (likely produces Figs. 5-7)
- parameter-estimation.ipynb
- ringdown-analysis.ipynb
- gr-test-tiger.ipynb
- gr-test-fti.ipynb
- residual-analysis.ipynb

## Execution Order

### Phase A: Environment Setup
1. Verify Python 3.9+ available
2. Create local virtual environment
3. Install dependencies from requirements.txt (if present)
4. Key packages expected:
   - numpy, scipy, matplotlib
   - h5py (for HDF5 files)
   - pandas
   - bilby / pycbc / lalsuite (GW analysis)
   - gwpy (GW data handling)
   - astropy

### Phase B: Metadata Notebooks First
1. **calibration-monitoring.ipynb**
   - Input: calibration.tar.gz, cal_env.tar.gz
   - Output: H1_ASD_20240924.pdf (or similar)
   - Expected: ASD plots with monitoring lines
   - Verification: Compare against published figures

### Phase C: Parameter Estimation
2. **parameter-estimation.ipynb**
   - Input: combined_samples.tar.gz, posterior HDF5 files
   - Output: Mass, spin, distance posteriors
   - Verification: Compare with published values

### Phase D: Ringdown/QNM
3. **ringdown-analysis.ipynb**
   - Input: ringdown.tar.gz
   - Output: QNM frequencies, damping times
   - Critical for SSZ: Strong-field test region

### Phase E: GR Tests
4. **gr-test-tiger.ipynb**, **gr-test-fti.ipynb**
   - Input: Residuals, posterior samples
   - Output: GR deviation statistics
   - Critical for SSZ: These test standard GR

## Safety Protocols

### DO
- Create timestamped run folder for each notebook
- Capture stdout/stderr to log file
- Save all generated figures separately
- Verify outputs exist before claiming success
- Compare figure filenames with notebook code
- Document any deviations from expected output

### DO NOT
- Modify raw data files
- Overwrite previous outputs
- Install packages globally
- Delete intermediate results
- Claim reproduction without output verification

## Output Capture Strategy

```
03_NOTEBOOK_RUNS/
  runs/
    2026-05-14_A_calibration-monitoring/
      notebook.log
      stdout.log
      stderr.log
      figures/
        H1_ASD_20240924.pdf
        ...
    2026-05-14_B_parameter-estimation/
      ...
```

## Verification Checklist

Each notebook run must pass:
- [ ] Notebook executes without fatal errors
- [ ] All expected output files exist
- [ ] Figures match expected names/content
- [ ] HDF5 outputs can be read back
- [ ] Results qualitatively match published values
- [ ] Logs captured completely

## Blockers and Risks

### Potential Blockers
1. **Missing dependencies**: lalsuite, bilby not installed
2. **Data paths**: Notebooks may expect specific relative paths
3. **Compute requirements**: Some analyses may need significant RAM
4. **HPC requirements**: Some notebooks may need cluster resources

### Mitigations
- Use local venv, not conda (simpler)
- Check notebook cell 1 for path assumptions
- Start with smallest/fastest notebook
- Document resource requirements as discovered

## Next Phase Trigger

Proceed to Phase 4 (Actual Notebook Execution) only when:
- This plan reviewed and approved
- Python environment ready
- At least one notebook successfully tested
- Output capture structure validated

""".format(timestamp=datetime.now().isoformat()))

log(f"Created: {reproduction_plan}")

# 2. Python Environment Plan
with open(env_plan, 'w', encoding='utf-8') as f:
    f.write("""# Python Environment Plan

**Generated:** {timestamp}

## Recommended Setup

### Python Version
- **Python 3.9 or 3.10** (3.11+ may have compatibility issues with legacy GW packages)

### Virtual Environment
```bash
cd E:\clone\ligo-gw240925-gw250207-release
python -m venv venv_ligo
venv_ligo\Scripts\activate
```

### Core Dependencies
```
numpy>=1.20.0
scipy>=1.7.0
matplotlib>=3.4.0
h5py>=3.0.0
pandas>=1.3.0
```

### GW-Specific Dependencies
```
gwpy>=2.3.0
astropy>=4.3.0
```

### Optional but Likely Needed
```
bilby>=1.4.0      # Bayesian inference
pycbc>=2.0.0     # CBC waveforms
lalsuite         # LIGO Algorithm Library (heavy install)
```

### Installation Strategy
1. Install core scientific stack first
2. Test basic HDF5 reading
3. Install GW packages one by one
4. Verify each import works
5. Document any failures

### Environment Validation Test
```python
import numpy as np
import h5py
import matplotlib.pyplot as plt

# Test HDF5 reading
with h5py.File('test.h5', 'w') as f:
    f.create_dataset('test', data=np.array([1,2,3]))

print("Core stack: OK")

try:
    import gwpy
    print("GWpy: OK")
except ImportError:
    print("GWpy: MISSING")

try:
    import bilby
    print("Bilby: OK")
except ImportError:
    print("Bilby: MISSING (optional)")
```

## No Global Installation Policy

- All packages installed to venv only
- No conda (to avoid conflicts)
- No pip --user installs
- No system package manager usage

## Blocker Documentation

If installation fails:
1. Document exact error message
2. Try alternative package (e.g., pip vs conda-forge)
3. If still failing: mark notebook as BLOCKED
4. Report which dependency caused issue

""".format(timestamp=datetime.now().isoformat()))

log(f"Created: {env_plan}")

# 3. Calibration Comparison Plan
with open(cal_comparison_plan, 'w', encoding='utf-8') as f:
    f.write("""# Calibration Comparison Plan

**Generated:** {timestamp}

## Objective
Compare results across calibration variants (C00, C01, envcal, cal) to identify:
- Which parameters are calibration-stable
- Which parameters shift with calibration
- Whether effects persist across variants (SSZ-relevant)

## Calibration Variants

| Variant | Description | Files |
|---------|-------------|-------|
| **C00** | Uncalibrated / raw strain | GW240925-C00-Strain.tar |
| **C01** | Calibrated with envelope | GW240925_combinedPHM_envcalC01_metafile.hdf5 |
| **envcal** | Envelope calibration | cal_env.tar.gz |
| **cal** | Standard calibration | calibration.tar.gz |

## Comparison Targets

### Mass Parameters
- Primary mass (m1)
- Secondary mass (m2)
- Chirp mass (M_chirp)
- Total mass (M_total)

### Spin Parameters
- Primary spin (chi1)
- Secondary spin (chi2)
- Effective spin (chi_eff)
- Precession

### Geometry
- Luminosity distance (d_L)
- Inclination (iota)
- Sky location (ra, dec)

### Remnant
- Final mass
- Final spin
- Ringdown frequency (f_ring)
- Damping time (tau)

## Methodology

### Step 1: Load Posteriors
For each calibration variant:
```python
import h5py

# Load C01 posterior
with h5py.File('GW240925_combinedPHM_envcalC01_metafile.hdf5', 'r') as f:
    posterior_c01 = extract_posterior(f)
```

### Step 2: Compute Shifts
For each parameter theta:
- theta_C00 vs theta_C01
- theta_C00 vs theta_envcal
- theta_C01 vs theta_envcal

Quantify shift:
- Absolute: |mean_C00 - mean_C01|
- Relative: |mean_C00 - mean_C01| / sigma_C00
- Credible interval overlap

### Step 3: Identify Stable Parameters
Parameters where:
```
|shift| < 0.1 sigma  →  calibration-robust
|shift| > 1 sigma   →  calibration-sensitive
```

### Step 4: Document for SSZ
For any potential SSZ effect:
- Must persist across calibration variants
- Must be larger than calibration-induced shifts

## Statistical Metrics

### For Posterior Comparison
1. **Kullback-Leibler divergence**: D_KL(P||Q)
2. **Wasserstein distance**: W_1(P, Q)
3. **Credible interval overlap**: fraction of overlap
4. **Mean shift / combined sigma**: (mu1 - mu2) / sqrt(sigma1^2 + sigma2^2)

### For Residuals
1. **Power spectral density**: S_residual(f)
2. **Whitened residual amplitude**: in sigma units
3. **Excess power regions**: frequency bands with SNR > threshold

## Expected Outputs

### Tables
```
Parameter | C00 mean | C01 mean | shift/sigma | robust?
----------|----------|----------|-------------|--------
m1        | X.X      | X.X      | 0.XX        | YES/NO
...
```

### Plots
- Overlapping posterior distributions
- Shift magnitude vs parameter
- Residual PSD comparison

## SSZ Relevance

A calibration-stable anomaly would:
1. Show consistent shift across C00/C01/envcal
2. Be larger than calibration-induced variance
3. Not lie on known monitoring/power/violin lines
4. Appear in multiple detectors

""".format(timestamp=datetime.now().isoformat()))

log(f"Created: {cal_comparison_plan}")

# 4. Posterior Comparison Plan
with open(posterior_comparison_plan, 'w', encoding='utf-8') as f:
    f.write("""# Posterior Comparison Plan

**Generated:** {timestamp}

## Objective
Systematically compare posterior distributions from different runs/calibrations.

## Data Sources

### GW240925
- combined_samples.tar.gz
- GW240925_combinedPHM_envcalC01_metafile.hdf5 (~200 MB)

### GW250207
- GW250207_combinedPHM_cal_metafile.hdf5 (~300 MB)

## HDF5 Structure Inspection

Before analysis, verify structure:
```python
import h5py

with h5py.File('GW240925_combinedPHM_envcalC01_metafile.hdf5', 'r') as f:
    print("Groups:", list(f.keys()))
    
    # Look for posterior group
    if 'posterior' in f:
        post = f['posterior']
        print("Datasets:", list(post.keys()))
        print("Attributes:", dict(post.attrs))
```

## Key Parameters to Compare

### Intrinsic
- mass_1_source (primary mass in source frame)
- mass_2_source (secondary mass)
- chi_1 (primary spin magnitude)
- chi_2 (secondary spin magnitude)
- chi_eff (effective spin)
- chi_p (precession)

### Extrinsic
- luminosity_distance
- inclination
- ra (right ascension)
- dec (declination)
- geocent_time

### Derived
- chirp_mass
- total_mass
- mass_ratio
- symmetric_mass_ratio

### Remnant (if available)
- final_mass
- final_spin
- peak_luminosity

## Comparison Methodology

### 1. Visual Comparison
- Corner plots for each event/variant
- Overlapping 1D marginals
- 2D joint distributions

### 2. Quantitative Metrics

#### Mean/Median Shifts
```
delta = |mean_A - mean_B|
delta_norm = delta / sqrt(sigma_A^2 + sigma_B^2)
```

#### Credible Interval Overlap
```
overlap = |CI_A intersect CI_B| / |CI_A union CI_B|
```

#### Distribution Distance
- KL divergence (asymmetric)
- JS divergence (symmetric)
- Wasserstein distance (interpretable in parameter units)

### 3. Consistency Tests
- Are posteriors within X sigma of each other?
- Do credible intervals overlap at Y% level?
- Are mean shifts smaller than calibration uncertainty?

## Event Comparison: GW240925 vs GW250207

Compare:
- Signal-to-noise ratio (SNR)
- Mass regime
- Spin measurements
- Calibration treatment
- Posterior precision

## SSZ Implications

If SSZ predicts systematic shifts:
- Compare across events (different masses, spins)
- Look for scaling with compactness
- Check ringdown vs inspiral consistency

""".format(timestamp=datetime.now().isoformat()))

log(f"Created: {posterior_comparison_plan}")

# 5. GR Test and Ringdown Comparison Plan
with open(gr_test_plan, 'w', encoding='utf-8') as f:
    f.write("""# GR Test and Ringdown Comparison Plan

**Generated:** {timestamp}

## Objective
Analyze GR tests and ringdown data for potential SSZ signatures.

## Data Sources

### GR Tests
- **tiger.tar.gz**: TIGER (Test Infrastructure for GEneral Relativity)
- **fti.tar.gz**: Fractional Template Analysis
- **pca.tar.gz**: Principal Component Analysis

### Ringdown/QNM
- **ringdown.tar.gz**: Ringdown analysis products
- **qnmrf.tar.gz**: QNM Rational Filter
- **pseobnr.tar.gz**: Precessing SEOBNR (waveform model)

## GR Test Categories

### 1. Inspiral Tests
- Phase evolution consistency
- PN coefficient deviations
- Modified dispersion

### 2. Merger-Ringdown Tests
- IMR consistency (Inspiral-Merger-Ringdown)
- QNM frequency tests
- Damping time tests

### 3. Polarization/Sky
- Tensor modes only vs scalar/vector
- Localization consistency

## Ringdown Analysis Priorities

### QNM Parameters
1. **Frequency (f_220)**: dominant (2,2,0) mode
2. **Damping time (tau_220)**: quality factor
3. **Amplitude**: excitation level
4. **Overtone (f_221)**: first overtone if measurable

### SSZ-Relevant Questions
- Is f_220 consistent with GR prediction?
- Is tau_220 consistent with GR?
- Are there hints of additional modes?
- Does ringdown structure match remnant parameters?

## Analysis Plan

### Step 1: Load GR Test Results
From TIGER, FTI, PCA packages:
- Bayes factors
- Posterior distributions for deviation parameters
- Confidence intervals

### Step 2: Compare to Null (GR)
```
ln B = ln p(data | GR) - ln p(data | modified GR)
```

### Step 3: Ringdown Parameter Extraction
- Load ringdown posteriors
- Extract f_220, tau_220 distributions
- Compare to GR prediction from inspiral

### Step 4: IMR Consistency
- Inspiral predicts final mass/spin
- Ringdown measures final mass/spin
- Compare: consistent within uncertainty?

## SSZ-Specific Analysis

### For Phase/Corrections
If SSZ predicts inspiral phase correction:
```
delta_phi(f) = phi_data(f) - phi_GR(f)
```
Test: Is delta_phi(f) systematic or noise-like?

### For Ringdown
If SSZ predicts QNM correction:
```
f_SSZ = f_GR * (1 + epsilon)
tau_SSZ = tau_GR * (1 + eta)
```
Test: Are residuals consistent with epsilon, eta = 0?

### For Residuals
After best-fit GR subtraction:
```
residual = data - h_GR_bestfit
```
Test: Is residual structure consistent with noise?

## Output Products

### Tables
```
Test | Statistic | GR value | Deviation | Significance
-----|-----------|----------|-----------|-------------
TIGER | ln B | 0 | X.X | X sigma
FTI | ...
Ringdown f_220 | ...
Ringdown tau_220 | ...
IMR consistency | ...
```

### Plots
- QNM frequency vs mass (Kerr prediction overlay)
- Residual time/frequency series
- GR deviation parameter posteriors

## Interpretation Guidelines

### Conservative (GR holds)
- All tests consistent with GR
- No significant Bayes factor for deviations
- Ringdown consistent with inspiral

### Interesting (further study)
- Marginal deviation in one test
- Not reproduced across independent tests
- Calibration-dependent

### Strong (would need confirmation)
- Consistent deviation across multiple tests
- Calibration-robust
- Multiple detectors agree
- Theoretical prediction matches

## SSZ Connection

This analysis provides baseline:
- How much can GR deviate (limits)?
- Where are strongest constraints?
- What systematics exist?

For SSZ testing: Must show deviation **beyond** these GR constraints.

""".format(timestamp=datetime.now().isoformat()))

log(f"Created: {gr_test_plan}")

# Write log file
with open(log_file, 'w', encoding='utf-8') as f:
    f.write("# Phase 3 Reproduction Readiness Log\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    for entry in log_content:
        f.write(f"{entry}\n")
    f.write("\n=== PHASE 3 COMPLETE ===\n")
    f.write("STATUS: PASS\n")
    f.write("All 5 planning documents created.\n")
    f.write("Ready for Phase 4: Actual notebook execution.\n")

log("=== PHASE 3 REPRODUCTION READINESS COMPLETE ===")
log("STATUS: PASS")
log(f"Total files created: 5")
log("Ready for Phase 4: Notebook execution")

print(f"\n=== PHASE 3 COMPLETE ===")
print(f"Plans created in:")
print(f"  {NOTEBOOK_DIR}")
print(f"  {COMPARISON_DIR}")
print(f"Log: {log_file}")
