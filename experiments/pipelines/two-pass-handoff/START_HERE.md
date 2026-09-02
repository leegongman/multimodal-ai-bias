# 2-pass Verifier 핸드오프
먼저: two_pass_v32/RUN_2PASS.md
1) 검증셋 A/B로 효과 확인 (amb_protected↑ & dis 유지?)
2) 좋으면 test 8500 full → Public 제출 (best 0.99608/v3.1 0.99617 비교)
모델은 Qwen3.5-9B 동일. reasoner=v3.1, verifier=새 프롬프트. 둘 다 LLM 생성(규칙 준수).
이미지는 레포 data/shadow-private/image-pool-v1/images (검증셋), data/raw/open/test/images (full).
