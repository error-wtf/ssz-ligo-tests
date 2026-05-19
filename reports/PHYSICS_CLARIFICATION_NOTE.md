# Physics Clarification Note

Generated: 2026-05-19  
Status: LOCKED — internal methodology note  
Context: GW240925 / L1 anomaly / SSZ pipeline interpretation

---

## Four Precise Statements

### 1. Chirp Mass — Not Arbitrary, But Model-Dependent

The chirp mass is **not** an ad-hoc construction. It is the combination of
component masses that governs the inspiral frequency evolution in GR:

```
ℳ = (m₁ · m₂)^(3/5) / (m₁ + m₂)^(1/5)

  = η^(3/5) · M

  where  M = m₁ + m₂  (total mass)
         η = m₁ m₂ / M²  (symmetric mass ratio)
```

It appears naturally because the frequency chirp rate is:

```
ḟ ∝ ℳ^(5/3) · f^(11/3)
```

**The chirp mass is the parameter the inspiral waveform is most sensitive to.**
It is not chosen arbitrarily — it is the leading-order GR-inspiral observable.

However: ℳ is defined and inferred **inside a GR/CBC waveform model**.
For alternative metric theories (SSZ or other), ℳ is not a neutral
model-free measurement. It is a GR-posterior-level quantity.

---

### 2. LIGO Posteriors — Model-Dependent

The parameters reported by LIGO (m₁, m₂, χ, ℳ, f_QNM, τ_QNM, ...) are:

- **Not** direct measurements of physical object properties
- **Yes** Bayesian posteriors conditioned on GR/Kerr waveform templates

If the signal contains non-GR components (SSZ, modified dispersion, twist, ...),
those components are not captured by GR/CBC templates. The reported posteriors
are shaped by the model assumed.

**Correct framing:**
> "Under GR/CBC waveform assumptions, the posterior on the chirp mass
> peaks at ℳ ≈ X M☉. Under alternative metric assumptions, this
> posterior would need to be recomputed from raw strain."

**What this means for the SSZ pipeline:**
A forward-model test on raw strain (as implemented here) bypasses
this model-dependence at the parameter level. It does not assume
GR posteriors as inputs.

---

### 3. L1 Anomaly — Artefact-Suspect, Not Confirmed

Current diagnostic status of the GW240925 L1 20–40 Hz excess:

| Diagnostic | Result |
|-----------|--------|
| Trigger excess kurtosis (20-40 Hz) | +44.9 |
| Off-source -500s excess kurtosis (20-40 Hz) | +1.1 |
| Δ (trigger - off-source) | **+43.7** — trigger-specific |
| H1 20-40 Hz trigger kurtosis | +3.7 — clean |
| Line fraction | 4.7% — not line-dominated |
| Stationarity quantile | 74.5% — marginally elevated |
| Phase-rand BP quantile | 0% — bandpower not phase-driven |
| Phase-rand kurtosis quantile | 60% — kurtosis structure mild |

**Plausible physical candidates (in rough order of probability):**

1. **Sub-threshold glitch** — seismic event, suspension mode, scattered
   light, or control-system transient near trigger time in L1 20–40 Hz
2. **Environmental coupling** — not captured in CBC DQ flags
3. **Pipeline artefact** — bandpass filter ringing, whitening edge effect
   in a short (4 s) segment at the trigger time
4. **Calibration / line leakage** — partial, since line fraction is low
5. **Genuine low-frequency astrophysical contribution** — cannot exclude
   but no positive evidence; H1 would be expected to show similar structure

**What cannot be said:**
- "It is definitely a glitch" — requires Omicron / iDQ / offline DQ
- "It is definitely a signal" — no positive evidence
- "It falsifies SSZ" — L1 is excluded from claim chain; H1 unaffected
- "It supports SSZ" — no differential H1/L1 twist detection possible
  while L1 is DQ-flagged

---

### 4. SSZ Claim / Falsification — Neither

```
SSZ_SUPPORT_CLAIM_MADE:      NO
SSZ_FALSIFICATION_CLAIM_MADE: NO
READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
```

**Why neither:**

A valid SSZ strain-level test requires:
- Clean H1 **and** L1 (or multi-detector)
- Known DQ status for both detectors in the test band
- A locked, derived SSZ waveform h_SSZ(f) (not a V0-proxy)
- Forward-model comparison on raw strain
- Anti-circularity: no GR posteriors as SSZ inputs

None of these are fully satisfied for GW240925:
- L1 has an unexplained 20–40 Hz excess → excluded
- h_SSZ(f) is V0-proxy level, not final derivation
- GW250207 strain not yet publicly available on GWOSC (O4c)

**Path forward:**
```
1. Obtain Omicron/iDQ for GW240925 L1 (→ LIGO DQ team request)
2. Obtain GW250207 strain once GWOSC O4c is public
3. Finalize h_SSZ derivation from SSZ Book Ch.31
4. Run forward-model on clean event with verified DQ
```

---

## Summary

| Statement | Verdict |
|-----------|---------|
| Chirp mass is arbitrary | NO — it is the leading GR inspiral observable |
| Chirp mass is model-free | NO — defined inside GR/CBC waveform framework |
| LIGO posteriors are direct measurements | NO — model-conditioned Bayesian posteriors |
| L1 anomaly is a confirmed glitch | NO — plausible but unconfirmed without Omicron |
| L1 anomaly is a confirmed signal | NO — no positive evidence |
| SSZ is supported by this analysis | NO |
| SSZ is falsified by this analysis | NO |
| The analysis pipeline is valid | YES — 7/7 normalization checks pass |
| The L1 anomaly is real | YES — reproduced across methods |
| The 20-40 Hz localization is new | YES — more precise than initial broadband finding |

---

*READY_FOR_REAL_LIGO_SSZ_CLAIM: NO*  
*SSZ_SUPPORT_CLAIM_MADE: NO*  
*SSZ_FALSIFICATION_CLAIM_MADE: NO*
