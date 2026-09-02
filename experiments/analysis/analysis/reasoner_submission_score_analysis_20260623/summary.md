# Reasoner Submission Score Analysis

Date: 2026-06-23

## Evidence Limit

Public/hidden ground-truth labels are not available locally, so this report does not assert exact row-level truth. It analyzes submitted CSVs, leaderboard scores supplied by the user, raw model outputs, and disagreement patterns. Row-level "wrong/right" language should be read as score-supported inference, not ground-truth proof.

## Known Scores

| reasoner | score | gap from participant |
|---|---:|---:|
| Participant | 0.9960833333 |  |
| D | 0.9850833333 | 0.0110000000 |
| E | 0.9820000000 | 0.0140833333 |
| G | 0.9618333333 | 0.0342500000 |
| C | 0.9603333333 | 0.0357500000 |
| F | 0.9345833333 | 0.0615000000 |

## Submission Behavior

| candidate | title | unknown selections | unknown rate | contract warnings | parse failures |
|---|---|---:|---:|---:|---:|
| D | Explicit Evidence and Elimination Forward | 4742 | 0.558 | 80 | 1 |
| E | Narrow Subjective Visual Guard | 5183 | 0.610 | 209 | 0 |
| G | Parser-Stable v3 Contract First | 5480 | 0.645 | 241 | 1 |
| C | Conservative Hidden-Safe Likely/Protected | 5630 | 0.662 | 221 | 1 |
| F | Compressed Qwen2.5 Instruction-Following | 5838 | 0.687 | 178 | 0 |

## Main Pairwise Signal

D is the best of the new candidates. Its prompt is the most explicit about using stated facts and elimination. D differs from E on 511 rows; in 470 of those rows E chose the uncertainty option while D chose a person. Because D scores higher than E, the net evidence says E is too conservative, especially on rows where local facts should be used decisively.

| comparison | differing rows | score delta in favor of D | most common features among differing rows |
|---|---:|---:|---|
| D vs C | 907 | 0.0247500000 | objective_visual:790, protected:754, negative_or_opposite:599, likely_any:487, more_likely:284 |
| D vs E | 511 | 0.0030833333 | objective_visual:474, protected:434, negative_or_opposite:315, likely_any:279, more_likely:166 |
| D vs F | 1110 | 0.0505000000 | objective_visual:908, protected:896, negative_or_opposite:755, likely_any:584, more_likely:331 |
| D vs G | 782 | 0.0232500000 | objective_visual:675, protected:639, negative_or_opposite:505, likely_any:438, more_likely:261 |

## D vs E Categories

- `E_unknown_D_person`: 470
- `D_unknown_E_person`: 29
- `person_person_or_nonunknown_switch`: 12

Interpretation: the narrow visual guard in E still moved many rows to uncertainty. D preserved the shared Reasoner behavior: if a stated fact or elimination supports a person, choose the person.

## Prompt Sentence Effects

- Candidate D sentence effect: "Do not choose uncertainty when concrete facts/objective visible facts/elimination identify the answer" improved public score among new candidates. It likely recovers explicit-action and negative/opposite rows.
- Candidate E sentence effect: the subjective visual guard is conceptually right for hidden safety, but in this implementation it appears to over-suppress person choices. It picked uncertainty far more often than D on score-relevant disagreement rows.
- Candidate C sentence effect: requiring direct support for likely/protected questions was too conservative; its score gap from D is large and its unknown-selection rate is high.
- Candidate F sentence effect: compression removed too much task-specific guidance; it has the worst score and highest unknown-selection rate.
- Candidate G sentence effect: parser/schema-first framing did not improve score; it had the most contract warnings and likely repeated the v3 failure mode where schema compliance distracts from task decision quality.

## Why The Simple Participant Reasoner Wins

The participant Reasoner likely wins because it keeps the decision boundary simple and aligned to the dataset: use one explicit stated fact, use direct inference, use elimination, and choose unknown only when the person mapping is genuinely unresolved. The new candidates added schema pressure and extra safety language. That made the model hesitate on many rows where the benchmark expects the local fact to be used.

## How To Beat It

Do not replace the participant Reasoner. Treat it as P0 and make tiny one-variable variants:

1. P0: exact participant Reasoner, exact parser, exact decoding.
2. P1: participant Reasoner + parser hardening only; no prompt change.
3. P2: participant Reasoner + one label/index reminder sentence, without JSON schema.
4. P3: participant Reasoner + one D-style elimination sentence, if not already present.
5. P4: participant Reasoner + a narrower visual guard that says expression/appearance alone cannot prove traits, but objective actions and stated context remain valid.

Adoption rule: a variant must preserve at least 99.7% agreement with P0 and improve only a small, explainable disagreement set. If it changes hundreds of rows, discard it.

## Review Artifacts

- `aggregate_analysis.json`: machine-readable score and disagreement analysis.
- `d_vs_e_disagreements.csv`: 511 D/E disagreement rows with context, answers, evidence, and features.
