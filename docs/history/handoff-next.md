# Multimodal 236722 작업 인수인계 (새 대화 이어가기용)

평가: 성균관대 멀티모달 AI Bias 프로젝트 (236722). 종료 2026-06-29.
평가: Balanced Accuracy = (Acc_ambiguous + Acc_disambiguated)/2. test 8500개(정답 미공개).
리더보드: Public 60% / Private 40%. 1차 Private, 2차 = Private top15 + Hidden 1500개 코드검증.
실행환경: RTX 6000 / A6000 48GB, vLLM, 평균 0.5초/sample·8500은 70분 이내, 오프라인.

## 현재 최선 (최종 제출 후보)
- **Qwen3.5-9B + v3.1 가드 프롬프트 + 2-pass(Reasoner+Verifier) = Public 0.99617**
- 안전판: 같은 모델 v3.1 단일 = 0.99617(동일), best(14006) = 0.99608
- 산출물: runs/test-2pass-20260624-1225/submission.csv

## 리더보드 현실 (사용자 확인)
- 1~14등: 전부 **1.0 (만점)** ← 정상 추론으로 불가능 추정. 판단은 보류(내가 단정 안 함).
- 15~25등대: 0.997~0.999. **25등 = 0.99833.**
- 우리 0.99617 → 25등까지 **Public 약 11개, 전체 약 18개** 차이.
- 코드공유에 0.998대 상위권 코드 공개 **없음**(사용자 확인). 공개된 건 baseline + 0.99517 + 0.99633(2-pass) 예시뿐.

## 핵심 진단 (데이터로 확인된 사실)
1. best(Qwen3.5-9B/14006)는 unknown 58.6% 선택. 점수 높은 모델일수록 unknown 多 = 이 task는 ambiguous(정답unknown) 비중 큰 BBQ형.
2. best 약점: 익명 보호속성 진술("A White person did X")에서 그룹 라벨 사람을 고름. test에 이 구조 914행(11%), best가 39% 사람 선택.
3. v3.1 가드("익명 그룹 진술 ≠ 개인 지목, 명시 개인/이름/위치는 그대로")로 그걸 교정 → 검증셋 0.72→0.77, Public +0.00009.
4. 2-pass(Verifier가 trap/도망 좁게 재검토) → 검증셋 0.77→0.81, 단 **Public은 0.99617에서 멈춤(v3.1과 동일)**.
5. best/v3.1/2-pass가 **8089행(95%)에서 동일 답**. Public 천장 = 우리 접근(Qwen3.5-9B)의 한계. 그 18개는 95% 동의구간(모델 한계)에 있음.

## 실패 기록 (다시 하지 말 것)
- v4(룰 11개 확장): 0.99608→0.99133. 전역 프롬프트 재작성 = 잘하던 ambiguous 파괴.
- v3 JSON 스키마 강제: 8500 중 391개만 파싱. 출력 복잡화가 Qwen 망침.
- Qwen2.5-VL-32B-AWQ: 0.98983 / Qwen3.6-35B: 0.9695 / gemma4-26B: 0.99175. **"더 큰 모델"은 다 best보다 낮음**(unknown 덜 골라 trap에 빠짐).
- **InternVL3-14B + v3.1 + 2-pass (방금)**: 검증셋 게이트 실패. dis_named 0.94→0.88(명시 사실조차 "상대 정보 없다"며 unknown 도망). + 속도 1.41초/sample = 0.5초 제약의 2.8배 = **실격 수준**. → 시각 강한 모델 가설 반증됨.

## 작업 원칙 (반드시 지킬 것)
- **근거 없이 막 던지지 말 것.** 검증셋(data/local-validation/v3, 188문항, 정답 논리적 결정)으로 먼저 재고 → 통과해야 full → Public. 검증셋이 도박을 분석으로 바꾸는 핵심 도구.
  - 검증셋 채점: Balanced 분해(amb/dis) + 서브셋별. 기준선 Qwen 2-pass = Balanced 0.8069, amb_protected 0.52, dis_named 0.94.
  - 게이트: amb 유지 + dis 유지/상승이어야 채택. dis 떨어지면 폐기.
- 제출 전 항상 best(0.99608)/2-pass(0.99617) 대비. 떨어지면 폐기, 안전판 유지.
- 규칙: 최종답은 LLM 생성. 룰/조건문으로 라벨 직접결정 금지. test 패턴으로 프롬프트 만들면 leakage(검증셋은 내부도구로만, 제출물 미포함).
- 검증셋 회색지대: test 구조를 참고해 만듦(질문 7개 우연 일치). 제출물엔 영향 없으나, 더 엄격히 하려면 BBQ 원본에서 직접 재구성 가능.

## 아직 안 해본 것 (다음 후보, 단 근거 기반으로)
1. **그 18개 오답의 정체 정밀 규명**: visual_needed(1990행)인지, whose류(95), multi_sentence(827), 특정 질문유형인지. test 정답 없이 모델 confidence/일관성으로 추정.
2. **앙상블** (규칙 내: 여러 모델/프롬프트 후보를 LLM이 종합 생성). 검증셋으로 먼저.
3. Qwen2.5-VL-7B(레포에 있음, RefCOCO Qwen3.5급, 14B보다 빠름) 2-pass — 단 시각모델 가설은 이미 약해짐.
4. 2차 평가 대비: 코드 재현성(학습/추론 분리, 오프라인), 발표자료 PDF.

## 주요 파일 경로 (멀티모달 AI Bias 레포)
- 추론: scripts/run_inference_14006_vllm.py(best), scripts/run_inference_v31_vllm.py(v3.1), two_pass_v32/run_2pass_vllm.py(2-pass)
- 프롬프트: two_pass_v32/prompts/{reasoner_system_v31.txt, verifier_system.txt}
- 검증셋: data/local-validation/v3/{valset.csv, answer_key.csv, score_valset.py}
- 분석: experiments/analysis/qwen_reasoner_optimization_20260623/, experiments/analysis/disagreement_20260623/, experiments/analysis/submission_reports_20260623/
- 데이터: data/raw/open/test/ (test.csv + images/), data/shadow-private/image-pool-v1/images/ (검증셋용)
- 설계서: experiments/analysis/type_routed_solver_design_20260623.md
