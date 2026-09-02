# Multimodal 236722 — v3.1 가드 A/B 핸드오프

**먼저 읽기:** data/local-validation/v3/codex_handoff/AB_INSTRUCTIONS.md

## 무엇
v3 검증셋에서 best가 익명 그룹 진술에 낚여 0.72로 폭락. 그걸 고치는 가드 프롬프트(v3.1)를
best와 A/B 비교. 모델은 동일(Qwen3.5-9B), 프롬프트만 교체.

## 핵심 2줄
- baseline: run_valset.py (프롬프트 내장)
- v3.1: run_valset.py 에 --system-prompt-file .../prompts/system_v3_1_anon_guard.txt 추가
→ 각각 score_valset.py 채점 → 서브셋 표(특히 amb_protected, dis_named) 회신
