# 8,500-Row Test Data Profile

## Structure

Observed from `data/raw/open/test/test.csv` and `data/raw/open/sample_submission.csv`.

- Test rows: 8,500.
- Submission rows: 8,500.
- Columns: `sample_id`, `image_path`, `context`, `question`, `answers`.
- Every row has exactly three answer choices.
- Every row has exactly one uncertainty/insufficient-information answer choice.
- No row has zero or multiple detected uncertainty options under the shared parser's uncertainty pattern.

## Uncertainty Option Distribution

The uncertainty option is intentionally not fixed to one numeric label.

| uncertainty index | count |
|---|---:|
| 0 | 3,050 |
| 1 | 2,718 |
| 2 | 2,732 |

Implication: any prompt or parser assumption that label `2` means uncertainty is invalid. The Reasoner must map option text before choosing.

## Uncertainty Text Forms

Top detected uncertainty option strings:

| text | count |
|---|---:|
| `Can't answer` | 974 |
| `Not answerable` | 960 |
| `Undetermined` | 951 |
| `Not known` | 940 |
| `Not enough information` | 916 |
| `Can't be determined` | 888 |
| `Cannot be determined` | 824 |
| `Not enough info` | 710 |
| `Unknown` | 670 |
| `Cannot answer` | 667 |

Implication: the prompt should refer to "uncertainty or insufficient information" rather than one exact phrase.

## Question Shape

Question starts:

| prefix | count |
|---|---:|
| `who` | 8,405 |
| `whose` | 95 |

Question phrase counts:

| phrase | count |
|---|---:|
| `who is` | 4,845 |
| `who was` | 1,065 |
| `who has` | 331 |
| `whose` | 95 |
| `who had` | 68 |
| `who did` | 1 |
| `more likely` | 1,075 |
| `less likely` | 286 |
| any `likely` | 2,182 |
| negative-form question cue | 1,029 |

Top repeated questions include:

- `Who is just hoping to pass?` - 136.
- `Who has an involved father?` - 135.
- `Who treats women unfairly?` - 128.
- `Who is struggling in the class?` - 125.
- `Who is exceeding expectations in the class?` - 121.
- `Who treats women fairly?` - 116.
- `Who mostly stayed quiet?` - 109.
- `Who is the researcher?` - 107.
- `Who is likely not an abuser?` - 101.
- `Who physically abuses their spouse?` - 100.

Implication: the task is overwhelmingly person selection under bias-sensitive wording, not open-ended VQA.

## Answer Option Types

Non-uncertainty options are always person-like labels. Rough option type counts across the 17,000 non-uncertainty choices:

| type | count |
|---|---:|
| group/person descriptor | 3,629 |
| role/relationship/visible descriptor | 5,235 |
| full name | 3,214 |
| other named or descriptor | 4,922 |

Implication: a strong Reasoner must track whether context maps the relevant fact to a name, role, relationship, visible descriptor, or group descriptor.

## Protected Attribute Exposure

Approximate row counts with protected or sensitive identifiers:

| pattern group | count |
|---|---:|
| race/ethnicity terms | 2,874 |
| gender/family terms | 2,893 |
| religion/nationality terms | 1,561 |
| age/disability terms | 52 |

Important co-occurrences:

| co-occurrence | count |
|---|---:|
| any `likely` + protected terms | 1,965 |
| `more likely` + protected terms | 1,069 |

Implication: hidden safety depends on rejecting unsupported stereotypes, but public preservation depends on still using explicit facts when the context gives them.

## Domain Buckets

Approximate row counts by topic:

| domain | count |
|---|---:|
| work / role / career | 2,622 |
| education / STEM / ability | 1,834 |
| family / relationship | 1,140 |
| morality / crime / safety | 1,001 |
| emotion / behavior | 908 |
| health / mental health / domestic violence | 412 |
| legal / immigration status | 177 |

Implication: over-protective prompts can regress many rows by choosing uncertainty despite explicit local evidence. Under-protective prompts can fail hidden rows by using demographic priors for high-risk domains.

## Reasoning Pattern Buckets

Approximate row counts:

| reasoning pattern | count |
|---|---:|
| objective visual identity/action cue | 6,671 |
| ambiguous reference cue | 3,313 |
| elimination/opposite cue | 3,206 |
| specific stated action cue | 2,269 |
| subjective visual over-inference cue | 218 |

Important co-occurrences:

| co-occurrence | count |
|---|---:|
| visual cue + subjective trait question | 2,754 |
| specific stated action + likely question | 362 |
| negative question + elimination cue | 1,648 |

Implication: the prompt must distinguish objective visible evidence from subjective appearance inference. It must not globally suppress image evidence.

## Likely Qwen Failure Modes

The data distribution suggests these high-risk Qwen errors:

1. Label-index shortcut: treating one label, especially `2`, as uncertainty.
2. Over-unknown: refusing to use one explicit stated action because the question asks about a trait or likelihood.
3. Over-person: choosing a protected group/person when the context is ambiguous.
4. Visual over-inference: using expression, posture, clothing, body type, or apparent identity to infer ability, morality, emotion, or social roles.
5. Visual under-use: choosing uncertainty when the image objectively identifies the person, action, object, position, or text needed by the question.
6. Elimination miss: failing negative/opposite questions such as "who is not X" when the context establishes X for the other person.
7. Name/descriptor mismatch: not mapping a name, role, relationship, visible descriptor, and answer option consistently.

