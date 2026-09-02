# Reasoner v3 Output Contract

## Final generated record

Reasoner는 마지막 non-empty line에 다음 strict JSON을 생성한다.

```text
FINAL_ANSWER_JSON:{
  "label":"0|1|2",
  "uncertainty_option_index":0|1|2,
  "evidence":"non-empty UTF-8 text",
  "evidence_type":"stated_text_fact|objective_visible_evidence|elimination|insufficient_evidence",
  "uncertainty_signal":true|false,
  "protected_attribute_risk":true|false
}
```

`uncertainty_option_index`는 선택 여부와 무관하게 세 답안 중 불확실성/판단 불가를 표현하는 답의 위치다. 숫자 JSON integer로 생성하며 parser는 범위만 검증한다.

## Semantic validation matrix

| 상태 | 필수 조건 | 결과 |
|---|---|---|
| uncertainty 선택 | `label == str(uncertainty_option_index)`, `uncertainty_signal=true`, `evidence_type=insufficient_evidence` | valid |
| decisive 선택 | `label != str(uncertainty_option_index)`, `uncertainty_signal=false`, decisive evidence type | valid |
| signal/index 불일치 | 위 등식이 성립하지 않음 | `invalid_schema` |
| uncertainty + decisive evidence | uncertainty 선택인데 decisive evidence type | `invalid_schema` |
| person + insufficient evidence | decisive 선택인데 `insufficient_evidence` | `invalid_schema` |
| index 누락/범위 오류 | integer 0..2가 아님 | `invalid_schema` |

## Artifact contract

- schema version: `reasoner_output_v3`
- `parsed_reasoner.csv`에 `uncertainty_option_index`와 `schema_version`을 추가한다.
- invalid row는 valid semantic fields를 비우고 raw output과 parse error를 보존한다.
- Verifier prompt에는 원래 답안, Reasoner label, Reasoner uncertainty index와 semantic fields를 전달한다.
- Verifier도 자체 `uncertainty_option_index`를 생성하며 같은 일관성 검사를 적용한다.
- arbitration은 생성된 label 후보만 keep/flip할 수 있다. 양쪽 후보가 invalid면 `unresolved`를 반환하고 submission writer가 실패한다.

## A/B isolation

1. A1: 기존 Qwen 7B + Reasoner v2 + 동일 이미지/엔진/decoding.
2. A2: A1과 동일하고 Reasoner v3 output contract만 변경.
3. uncertainty index 0/1/2별 parse success와 accuracy를 비교한다.
4. 계약 A/B가 끝나기 전 decisiveness 문구, 모델, pixel budget, 엔진을 바꾸지 않는다.

