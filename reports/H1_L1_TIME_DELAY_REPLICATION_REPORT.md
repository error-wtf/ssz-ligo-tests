# H1/L1 Time-Delay Replication Report
Generated: 2026-05-19 10:35:43

## Configuration
- Trigger GPS: 1411261107.984
- Window: 4.0s
- Coarse scan: +/-50.0ms step=1.0ms
- Fine scan: +/-10.0ms step=0.244ms
- Physical range: |dt| <= 10.012ms
- Sign-flip test: +L1 and -L1

## Subbands
| Band | f_lo | f_hi |
|------|------|------|
| 20-40 | 20.0 | 40.0 |
| 40-80 | 40.0 | 80.0 |
| 80-120 | 80.0 | 120.0 |
| 120-160 | 120.0 | 160.0 |
| 160-210 | 160.0 | 210.0 |
| 20-210 | 20.0 | 210.0 |

## Final Classification
| Key | Value |
|-----|-------|
| H1_L1_REPLICATION_STATUS TRIGGER (20-210 Hz) | PHYSICAL_DELAY_COHERENT |
| H1_L1_REPLICATION_STATUS TRIGGER (20-40 Hz) | PHYSICAL_DELAY_COHERENT |
| H1_L1_REPLICATION_STATUS OFF_m500 (20-210 Hz) | PHYSICAL_DELAY_COHERENT |
| H1_L1_REPLICATION_STATUS OFF_m500 (20-40 Hz) | PHYSICAL_DELAY_COHERENT |
| TRIGGER_SPECIFIC | NO — PERSISTENT_SYSTEMATIC |
| L1_20_40_STATUS | H1_REPLICATED_WITH_DELAY |

## Subband Verdicts
| Band | TRIGGER | OFF_m500 |
|------|---------|----------|
| 20-40 Hz | PHYSICAL_DELAY_COHERENT | PHYSICAL_DELAY_COHERENT |
| 40-80 Hz | PHYSICAL_DELAY_COHERENT | PHYSICAL_DELAY_COHERENT |
| 80-120 Hz | PHYSICAL_DELAY_COHERENT | PHYSICAL_DELAY_COHERENT |
| 120-160 Hz | PHYSICAL_DELAY_COHERENT | PHYSICAL_DELAY_COHERENT |
| 160-210 Hz | PHYSICAL_DELAY_COHERENT | PHYSICAL_DELAY_COHERENT |
| 20-210 Hz | PHYSICAL_DELAY_COHERENT | PHYSICAL_DELAY_COHERENT |

## WARNING: Non-Specific Coherence
The trigger and off-source windows show the same verdict.
The H1/L1 coherence is NOT specific to the trigger.
Likely cause: persistent environmental common-mode correlation
(Schumann resonances, 60 Hz harmonics, or common noise floor).
**This result CANNOT be used to claim GW signal replication.**
Further analysis with longer off-source baselines required.

## Interpretation Key
- PHYSICAL_DELAY_COHERENT: peak |xcorr| at |dt|<=10ms,
  SNR>5 vs unphysical range noise floor
- L1_ONLY_STRUCTURE: no physical peak, SNR<2
- UNPHYSICAL_DELAY_PREFERRED: peak outside physical range
- INCONCLUSIVE: ambiguous evidence
- SYSTEMATIC_SATURATION: xcorr saturated at scan boundary

## Anti-Circularity
- No PE/QNM posteriors used
- No Kerr/SSZ parameters used
- READY_FOR_REAL_LIGO_SSZ_CLAIM: NO
- SSZ_SUPPORT_CLAIM_MADE: NO
- SSZ_FALSIFICATION_CLAIM_MADE: NO
