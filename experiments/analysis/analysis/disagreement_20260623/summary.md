# Multimodal 236722 disagreement analysis — 2026-06-23

## Runs

| model key | public | elapsed | failure | sha256 |
|---|---:|---:|---:|---|
| baseline_qwen35_14006 | 0.9960833333 | 1929.86s | 0 | `d8fc19780cc6…` |
| qwen35_v4 | 0.9913333333 | 1562.92s | 0 | `a4f6bf3cbe49…` |
| gemma4_26b_awq_14006 | 0.99175 | 2563.90s | 0 | `0066dae0582b…` |
| qwen25_vl_32b_awq_14006 | 0.9898333333 | 2501.13s | 0 | `6833e02b9616…` |
| qwen36_35b_a3b_awq_14006 | 0.9695 | 1129.15s | 0 | `c5db2f567f17…` |

## Overall

- Rows: 8500
- Any-model disagreement rows: 1590
- All-model agreement rows: 6910

## Baseline pairwise disagreement

| compared with baseline_qwen35_14006 | changed rows |
|---|---:|
| qwen35_v4 | 293 |
| gemma4_26b_awq_14006 | 749 |
| qwen25_vl_32b_awq_14006 | 653 |
| qwen36_35b_a3b_awq_14006 | 1222 |

## Risk sets

| file | rows | meaning |
|---|---:|---|
| risk_sets/baseline_unique_all_4_others_agree.csv | 71 | Baseline differs while all four other runs agree on another label. |
| risk_sets/model_majority_3plus_against_baseline.csv | 380 | At least three non-baseline runs agree against baseline. |
| risk_sets/baseline_unknown_other3plus_same_non_unknown.csv | 355 | Baseline chose uncertainty; at least three others chose the same specific person/answer. |
| risk_sets/baseline_unknown_other2plus_same_non_unknown.csv | 392 | Baseline chose uncertainty; at least two others chose the same specific person/answer. |
| risk_sets/baseline_non_unknown_other3plus_same_unknown.csv | 17 | Baseline chose a specific answer; at least three others chose uncertainty. |
| risk_sets/baseline_non_unknown_other2plus_same_unknown.csv | 55 | Baseline chose a specific answer; at least two others chose uncertainty. |
| risk_sets/qwen35_v4_changed_from_baseline.csv | 293 | Rows changed by v4 relative to baseline. |
| risk_sets/qwen35_v4_only_changed_against_all_others.csv | 75 | v4 alone changed while baseline and the other three runs agree. |

## Transition counts vs baseline

| model | baseline unknown→non-unknown | baseline non-unknown→unknown | non-unknown→different non-unknown |
|---|---:|---:|---:|
| qwen35_v4 | 168 | 109 | 16 |
| gemma4_26b_awq_14006 | 570 | 166 | 13 |
| qwen25_vl_32b_awq_14006 | 444 | 183 | 26 |
| qwen36_35b_a3b_awq_14006 | 1171 | 15 | 36 |

## Initial interpretation

- v4 changed many rows and scored much worse, so broad prompt rewrites are unsafe.
- The most useful next target is not another full run; it is manual review of small risk sets, especially baseline uncertainty cases with strong non-baseline consensus.
- A v3.1 candidate should be one-line or near-one-line and should be tested only after these risk rows show a clear repeated failure mode.
