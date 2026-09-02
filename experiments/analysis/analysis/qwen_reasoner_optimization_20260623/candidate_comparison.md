# Candidate Comparison

Scores are qualitative before model A/B. They are based on data profile, shared Reasoner analysis, Qwen2.5 prompt-following risk, and v3 parser constraints.

Legend:

- High: favorable.
- Medium: acceptable but needs A/B evidence.
- Low: weak or risky.

| candidate | public preservation | hidden generalization | over-unknown risk | over-person risk | visual evidence handling | protected-attribute safety | parser stability | prompt length risk | final suitability |
|---|---|---|---|---|---|---|---|---|---|
| A Shared Minimal + Index Safety | High | Medium | Low | Medium | Medium | Medium | High | Low | High backup |
| B Objective Visual Balanced | Medium | Medium-High | Low-Medium | Medium | High | Medium-High | High | Medium | A/B candidate |
| C Conservative Hidden-Safe | Low-Medium | High | High | Low | Medium | High | High | Medium | Risky |
| D Evidence/Elimination Forward | High | Medium | Low | Medium-High | Medium | Medium | High | Medium | A/B candidate |
| E Narrow Subjective Visual Guard | High | High | Low-Medium | Low-Medium | High | High | High | Medium | Primary |
| F Compressed Qwen2.5 | Medium | Medium | Medium | Medium | Medium | Medium | Medium-High | Low | Backup only |
| G Parser-Stable v3 Contract | Medium | Medium | Medium | Low-Medium | Medium | High | Very High | Medium-High | Operational fallback |

## Candidate A

Best use:

- Establishes the closest v3-compatible form of the shared Reasoner.
- Should be the first baseline against any stronger modifications.

Main risk:

- It may not improve hidden generalization enough because subjective visual inference is only covered by broad stereotype language.

## Candidate B

Best use:

- Tests whether current v3 underuses image evidence.
- Useful because 6,671 rows contain objective visual identity/action cues.

Main risk:

- Could increase unsupported person selections if Qwen treats weak visual impressions as objective.

## Candidate C

Best use:

- Stress-test hidden-safe behavior on likely/protected rows.

Main risk:

- It directly weakens the shared Reasoner's public-critical single-instance rule.
- It may choose uncertainty too often on rows intentionally resolved by a stated local fact.

## Candidate D

Best use:

- Stress-test public-preserving behavior on explicit action, negative, and elimination rows.

Main risk:

- Hidden rows with less direct evidence may be over-personed.

## Candidate E

Best use:

- Best first challenger.
- Adds the most general hidden-safe guard without changing the shared Reasoner's core.

Main risk:

- Some rows use visible posture or action to establish a fact. Candidate E must not conflate objective action with subjective expression.

## Candidate F

Best use:

- Useful if Qwen2.5 struggles with long prompts or schema adherence.

Main risk:

- It loses concrete examples and may become too generic.

## Candidate G

Best use:

- Use when parse failures are the main problem.

Main risk:

- It resembles the current v3 style and may underperform shared-style decision quality.

## Current Ranking Before A/B

1. Candidate E: best balance of public preservation and hidden generalization.
2. Candidate A: safest baseline-preserving fallback.
3. Candidate B: useful if visual under-use is observed.
4. Candidate D: useful if over-unknown is observed.
5. Candidate G: operational fallback if parsing dominates.
6. Candidate F: compact fallback if Qwen2.5 instruction-following degrades with longer prompts.
7. Candidate C: hidden-safe stress test, not a likely final submission candidate unless public-like A/B supports it.

