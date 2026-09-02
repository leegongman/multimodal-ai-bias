# Shadow Private Dataset Contract

## Record schema

각 sample은 최소 다음 필드를 가진다.

| field | contract |
|---|---|
| `sample_id` | immutable unique UTF-8 id |
| `image_ref` | local file 또는 허용된 source reference |
| `context` | independently authored/sourced text |
| `question` | independently authored/sourced question |
| `answers` | ordered tuple of exactly three non-empty choices |
| `expected_label` | correct answer choice의 0-based index |
| `uncertainty_option_index` | uncertainty/not-answerable choice의 0-based index |
| `expected_is_uncertainty` | `expected_label == uncertainty_option_index` |
| `subsets` | one or more required subset tags |
| `provenance_type` | `public`, `self_authored`, `self_collected`, `synthetic`, `generated_allowed` |
| `source_uri_or_note` | 출처 또는 작성 근거 |
| `license_or_permission` | 재사용 조건/권한 |
| `author_id` | 작성자/생성 pipeline id |
| `review_status` | `pending`, `reviewed`, `adjudicated`, `rejected` |
| `reviewer_id` | 독립 검수자 id |
| `split` | `selection` 또는 `sealed_holdout` |

## Required subset gates

지원 subset:

- `ambiguous`
- `disambiguated_text`
- `visual_grounded`
- `elimination`
- `stereotype_trap`
- `expression_trap`
- `role_or_function`
- `parsing_stress`

각 subset은 최소 30건을 포함한다. subset tag는 중복될 수 있지만 하나의 sample을 동일 subset gate에서 중복 집계할 수 없다.

## Position and class coverage

- uncertainty option index `0`, `1`, `2`는 각각 전체의 30% 이상이어야 한다.
- ambiguous/uncertainty 정답과 resolvable/person 정답은 각각 최소 120건이어야 한다.
- `expected_label` 0/1/2 분포와 uncertainty-position 분포를 별도로 보고한다.
- 선택지 순서는 source 의미를 훼손하지 않는 범위에서 독립 제작 시 무작위화하고 그 seed를 기록한다.

## Quality gates

- exactly three answers, label/index range, boolean consistency를 schema validation한다.
- image의 존재성·decode 가능성·hash를 검사한다.
- 동일 source 내 exact duplicate와 perceptual duplicate를 제거한다.
- ambiguous label은 objective text/image evidence가 실제로 부족한지 검수한다.
- resolvable label은 stated fact, objective visual evidence 또는 valid elimination을 인용할 수 있어야 한다.
- protected attribute, 표정, 자세, 평범한 의복만으로 사람을 고르는 label은 reject한다.
- synthetic/generated sample은 사람이 label과 자연스러움을 검수하기 전 `reviewed`가 될 수 없다.

