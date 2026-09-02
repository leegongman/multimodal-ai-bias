# Investigation: Qwen3.5 Reasoner v3 출력·컨텍스트 실패

## Hand-off Brief

1. **What happened.** 사용자는 긴 v3 출력으로 7천 건 이상이 파싱에서 폐기되고 일부 요청은 vLLM 8K 컨텍스트를 초과했다고 보고했으며, RunPod의 완료된 full run은 8,500건 중 391건만 파싱 유효였음을 직접 확인했다.
2. **Where the case stands.** 출력 지시 단순화와 32K 서버 전환 후 최신 50건 테스트는 생성 실패 0건·파싱 유효 49건으로 대량 폐기는 해소됐지만, 1건의 파싱 실패와 약 197분의 full projection이 남아 있다.
3. **What's needed next.** 최신 `test_ctx_fix2`의 유일한 파싱 실패와 요청별 token/latency 분포를 조사해 정확성 결함과 속도 결함을 분리한다.

## Case Info

| Field | Value |
| --- | --- |
| Ticket | N/A |
| Date opened | 2026-06-20 |
| Status | Active |
| System | RunPod Ubuntu 24.04, RTX A6000 48GB, vLLM 0.17.1, Qwen/Qwen3.5-9B, max-model-len 32768 |
| Evidence sources | 사용자 제공 `reasoner_v3.yaml`; RunPod runs·summary·raw/parsed artifacts; vLLM logs; local runner/parser source |

## Problem Statement

사용자 보고: 기존 출력 포맷이 길어 7천 건 이상이 잘려 폐기되어 포맷을 단순화했고, vLLM 8K에서 입력 토큰 초과가 음수 `max_tokens` 오류를 만들어 32K로 전환했지만 아직 문제가 남아 있다.

## Evidence Inventory

| Source | Status | Notes |
| --- | --- | --- |
| `/Users/gongman/Downloads/reasoner_v3.yaml` | Available | 사용자가 제공한 단순화 prompt |
| RunPod `runs/qwen35_v3_full_c64_01/summary.json` | Available | 8,500건, generated 8,279, parse valid 391, invalid 8,109, 75.1분 |
| RunPod `runs/test_ctx_fix2/summary.json` | Available | 50건, generation failure 0, parse valid 49, invalid 1, 69.5초 |
| RunPod `runs/test_ctx_fix2/raw_reasoner.jsonl` | Available | 최신 실패 원문 및 token/latency 분석 가능 |
| RunPod vLLM server | Available | 32K 서버 현재 실행 중 |
| Public score / 정답 label | Missing | 결과 품질 평가는 아직 불가 |

## Investigation Backlog

| # | Path to Explore | Priority | Status | Notes |
| - | --- | --- | --- | --- |
| 1 | `test_ctx_fix2` 유일 parse invalid 원인 | High | Open | strict schema/semantic/truncation 구분 |
| 2 | 50건 token·latency·finish reason 분포 | High | Open | 197분 projection 원인 분해 |
| 3 | 32K 이전 음수 max_tokens 실패의 해소 여부 | High | Open | 최신 50건 generation failure 0으로 부분 확인 |
| 4 | prompt·runner·parser 실제 배포본 일치 여부 | Medium | Open | remote prompt SHA-256 `87d694...` |
| 5 | 대표성 있는 fixed subset 확장 | Medium | Open | 첫 50건만으로 full runtime 일반화 위험 |

## Timeline of Events

| Time | Event | Source | Confidence |
| --- | --- | --- | --- |
| 2026-06-20 07:18–08:33 UTC | 기존 c64 full run: 8,500건 처리, parse valid 391 | RunPod `qwen35_v3_full_c64_01/summary.json` | Confirmed |
| 2026-06-20 09:43–09:44 UTC | 출력 포맷 수정 50건: generated 48, parse valid 47 | RunPod `debug_format_fix2/summary.json` | Confirmed |
| 2026-06-20 10:05–10:06 UTC | 32K 후 50건: generated 50, parse valid 49 | RunPod `test_ctx_fix2/summary.json` | Confirmed |

## Confirmed Findings

### Finding 1: 기존 full run은 제출물로 사용할 수 없다

**Evidence:** RunPod `runs/qwen35_v3_full_c64_01/summary.json`

**Detail:** 8,500건 중 파싱 유효가 391건뿐이고 8,109건이 invalid다.

### Finding 2: 단순화+32K 조합은 대량 생성 실패를 해소했다

**Evidence:** RunPod `runs/test_ctx_fix2/summary.json`

**Detail:** 최신 50건에서 generation failure는 0건이고 parse valid는 49건이다.

### Finding 3: 최신 경로도 아직 full 실행 준비가 아니다

**Evidence:** RunPod `runs/test_ctx_fix2/summary.json`

**Detail:** parse invalid 1건이 남고 측정 projection은 11,810초(약 197분)다.

## Deduced Conclusions

### Deduction 1: 출력 길이와 8K 컨텍스트는 실제 원인이었지만 전체 원인은 아니다

**Based on:** Findings 1–3

**Reasoning:** 수정 전 대량 invalid에서 수정 후 49/50 유효로 개선됐지만 invalid와 runtime 문제가 잔존한다.

**Conclusion:** full 재실행 전에 잔여 실패와 속도 병목을 별도로 진단해야 한다.

## Hypothesized Paths

### Hypothesis 1: 단순화된 출력 포맷과 32K가 모든 실패를 해결했다

**Status:** Refuted

**Theory:** 두 변경만으로 8,500건 제출 가능 상태가 된다.

**Supporting indicators:** 최신 50건 generation failure 0, parse valid 49.

**Would confirm:** 대표 subset에서 generation/parse failure 0과 70분 이내 projection.

**Would refute:** 단 1건의 parse invalid 또는 70분 초과 projection.

**Resolution:** `test_ctx_fix2`에서 parse invalid 1건과 약 197분 projection이 직접 관측됐다.

## Missing Evidence

| Gap | Impact | How to Obtain |
| --- | --- | --- |
| 사용자가 말한 “아직 문제”의 정확한 증상 | 조사 우선순위가 파싱/속도/품질 중 어디인지 확정 불가 | 사용자 증상 또는 오류 로그 제공 |
| 최신 1건 parse invalid 원문 | 잔여 포맷/semantic 원인 확정 불가 | `parsed_reasoner.csv` 실패 행과 대응 raw 출력 추출 |
| 최신 finish reason·token 분포 | 197분 원인 확정 불가 | raw metadata와 vLLM metrics 분석 |
| Public score | label 품질 판단 불가 | 유효 submission 생성 후 제출 |

## Source Code Trace

| Element | Detail |
| --- | --- |
| Error origin | 조사 대기: remote runner output normalization / local strict parser |
| Trigger | Qwen 응답 또는 vLLM request가 출력·컨텍스트 계약을 위반할 때 |
| Condition | 긴 출력, multiline/semantic mismatch, max model length 초과 가능성 |
| Related files | `scripts/run_qwen35_v3_vllm.py`, `src/multimodal_bias/parsing.py`, `configs/prompts/reasoner_v3.yaml` |

## Conclusion

**Confidence:** Medium

두 변경은 기존 대량 폐기의 주요 원인을 크게 줄였지만 최신 50건 증거상 완전 해결은 아니다. 남은 정확한 원인은 최신 invalid 1건과 token/latency 분포를 읽어야 확정할 수 있다.

## Recommended Next Steps

### Fix direction

조사 후 결정. 현재 단계에서 추가 prompt·parser·동시성 변경은 근거가 부족하다.

### Diagnostic

`test_ctx_fix2` 실패 1건을 원문까지 추적하고 요청별 token/latency 분포를 산출한다.

## Reproduction Plan

현재 32K 서버와 동일 prompt/model/revision에서 고정 50건을 재현하고 raw·parsed·summary hash를 비교한다.

## Side Findings

- 최신 50건은 concurrency 8로 실행되어 이전 full c64 처리량과 직접 비교할 수 없다.
