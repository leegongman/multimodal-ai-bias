# Investigation: Qwen2.5-VL-7B Reasoner 단독 제출 0.91

## Hand-off Brief

1. **확인된 원인:** Multimodal label은 선택지의 0-based 인덱스인데 `reasoner_v1`은 불확실성을 항상 label `2`로 고정했다.
2. **경로 정정:** 보존된 Qwen 배포 번들은 vLLM이 아니라 Transformers `hf_local` 경로였으며, 이미지 바이트는 정적으로 전달되지만 당시 실제 요청·raw output은 남지 않았다.
3. **조치:** v1은 재현용으로 보존하고 매핑만 수정한 v2를 기본화했으며, 다음 RunPod에서는 독립 라벨셋 A/B와 persistent volume의 partial/raw artifact를 사용한다.

## Case Info

| Field | Value |
| --- | --- |
| Date | 2026-06-19 |
| Status | Concluded |
| Scope | Epic 1·2 Qwen Reasoner-only; Epic 3 excluded |
| Reported result | Multimodal Balanced Accuracy 0.91 |
| Production artifact | `/workspace/multimodal-bias/runs/20260619_061802_default/submission.csv` (현재 로컬에 없음) |
| Surviving evidence | runtime ZIP, source/config, 8,500 test inputs/images, reported prediction distribution |

## Final Conclusion

**결론 신뢰도: High(결함 존재), Medium(0.91 전체 기여도).**

선택지 매핑 결함은 정적으로 확정됐다. 공식 label은 선택지 인덱스인데(`Multimodal_236722_평가_요구사항_정리.md:26`, `Multimodal_236722_평가_요구사항_정리.md:69`), v1은 불확실성을 label `2`로 정의하고 uncertainty flag도 label `2`에 결합했다(`configs/prompts/reasoner_v1.yaml:7`, `configs/prompts/reasoner_v1.yaml:37`). 선택지에서 불확실성의 위치가 0 또는 1이면 Reasoner가 의미를 올바르게 판단해도 잘못된 label을 내도록 유도한다.

다만 당시 raw output과 라벨 정답이 없으므로 이 결함이 0.91 하락분을 얼마나 설명하는지, Qwen 7B 한계·보수성·이미지 해상도 영향이 각각 얼마인지는 다음 라벨셋 A/B로 분리해야 한다.

## Evidence Inventory

| Evidence | Status | Finding |
| --- | --- | --- |
| 평가/label 정의 | Available | Balanced Accuracy이며 label은 3개 선택지 인덱스다. |
| production prompt | Available | runtime ZIP과 로컬 v1이 동일하며 label 2를 uncertainty로 고정한다. |
| parser/submission | Available | 모델 label을 재매핑하지 않고 그대로 통과시킨다. |
| Qwen engine path | Available | `hf_local` Transformers 경로다. vLLM adapter는 없다. |
| local test images | Available | 8,500개, 0-byte 없음, 모두 JPEG header; 총 2,924,756,370 bytes. |
| production raw output | Missing | Pod 제거 후 복구 불가. label 2 선택 이유와 실제 request를 사후 검증할 수 없다. |
| hidden/test labels | Missing | 평가 설계상 미제공. |
| independent labeled validation | Missing | 모델·프롬프트·이미지 효과 분리에 필요하다. |

## Confirmed Findings

### F1. 선택지 순서와 0/1/2 전달 코드는 정상이다

- `data_loader`는 CSV의 answers 배열 순서를 그대로 `SampleRecord`에 넣는다(`src/multimodal_bias/data_loader.py:133`, `src/multimodal_bias/data_loader.py:142`).
- prompt formatter는 그 순서대로 `0.`, `1.`, `2.`를 붙인다(`src/multimodal_bias/prompting/templates.py:412`).
- parser는 생성 label 문자열을 그대로 parsed label로 사용한다(`src/multimodal_bias/parsing.py:112`, `src/multimodal_bias/parsing.py:149`).
- submission writer도 final label을 그대로 쓴다(`src/multimodal_bias/submission.py:713`).

따라서 별도 코드 remapping 또는 0/1 swap은 없다. 결함은 prompt의 label 의미 정의다.

### F2. `reasoner_v1`은 실제 선택지 매핑과 충돌한다

재구성 예에서 선택지가 `0. Not enough info / 1. wife / 2. husband`여도 v1 system은 “label 2 = uncertainty”라고 지시한다. 즉, label 2가 사람 선택지인 행에서도 같은 label에 상충하는 의미를 부여한다. Hypothesis #1(매핑/목표 불일치)은 **Confirmed**다.

### F3. 보고된 label 2 분포는 과다 선택 가능성을 보이지만 확정 증거는 아니다

보고된 제출 분포는 `0: 2,661`, `1: 2,649`, `2: 3,190`으로 label 2가 37.53%다. 균등 기준보다 약 4.2%p 높지만 실제 class prior와 raw reasoning이 없으므로 “과다 선택” 자체는 **Open**이다. 다만 label 2로 끌어당기는 prompt 메커니즘은 F2로 확정됐다.

### F4. 당시 Qwen 실행은 vLLM 경로가 아니다

- Qwen config의 adapter는 `hf_local`이다(`configs/models/qwen2_5_vl_7b.yaml:1`).
- adapter registry에는 `dummy`, `hf_local`, `minicpm_v`만 있다(`src/multimodal_bias/models/adapter.py:37`).
- runtime ZIP에도 vLLM runner/의존성이 없고 `hf_vlm.py`가 포함돼 있다.

따라서 “실제 vLLM 요청 프롬프트”는 존재하지 않는다. 보존된 번들 기준 실제 경로는 Transformers `model.generate()`다.

### F5. 실제 logical request 재구성

Reasoner는 system과 user prompt를 `system + "\n\n" + user`로 합친다(`src/multimodal_bias/reasoner.py:250`). HF adapter는 이것을 별도 system role이 아니라 단일 `user` message의 text content로 넣고, 앞에 PIL image content를 추가한 뒤 chat template을 적용한다(`src/multimodal_bias/models/hf_vlm.py:181`). 생성값은 `max_new_tokens=512`, `do_sample=false`다(`configs/models/qwen2_5_vl_7b.yaml:10`).

```text
messages = [{
  role: "user",
  content: [
    {type: "image", image: <PIL image decoded from original bytes>},
    {type: "text", text: <reasoner system + blank line + formatted sample prompt>}
  ]
}]
processor.apply_chat_template(..., add_generation_prompt=True, tokenize=True)
model.generate(..., max_new_tokens=512, do_sample=False)
```

이는 logical prompt 재구성이다. 당시 token IDs, processor-resized tensor shape, raw completion은 보존되지 않아 byte-for-byte runtime 재현은 불가능하다.

### F6. 이미지 전달 경로는 정적으로 정상이나 production 증명은 부족하다

- 로컬 입력은 8,500개 모두 존재하고 JPEG header를 통과한다.
- inference runner는 loaded image bytes와 format을 adapter에 넘긴다(`src/multimodal_bias/reasoner.py:174`).
- HF adapter는 bytes를 PIL image로 열어 chat image content에 넣는다(`src/multimodal_bias/models/hf_vlm.py:181`, `src/multimodal_bias/models/hf_vlm.py:218`).
- 앱 코드에는 602,112-pixel cap이나 명시적 resize가 없다. 해당 cap 가설은 현재 소스 기준 **Refuted**다. 다만 Qwen processor 내부 기본 resize는 당시 processor metadata가 없어 **Open**이다.

### F7. 기존 raw 보존 방식은 장애 분석에 불충분했다

기존 행은 prompt text/hash와 image hash/byte count를 저장하지 않았고, 전체 완료 전에는 숨은 `.raw_reasoner.jsonl.tmp`만 사용했다. Pod의 ephemeral storage를 삭제하면 final/tmp 모두 사라지므로 현재 label-only CSV에서 복구할 방법이 없다.

## Hypothesis Register

| # | Hypothesis | Status | Resolution |
| --- | --- | --- | --- |
| 1 | label semantics/prompt objective mismatch | **Confirmed** | v1의 label 2 고정과 선택지 인덱스 정의가 충돌한다. |
| 2 | 앱의 602,112-pixel downscale가 원인 | **Refuted** | 앱 코드/config에 해당 cap 또는 resize가 없다. processor 내부 동작은 별도 A/B 필요. |
| 3 | `reasoner_v1`이 과도하게 보수적 | **Open** | 금지 cue가 많지만 raw error audit/독립 라벨셋이 없어 효과량 미확정. |
| 4 | Qwen2.5-VL-7B 자체 성능 한계 | **Open** | mapping bug가 confounder이므로 corrected prompt 이후 큰 모델과 비교해야 한다. |
| 5 | 이미지가 모델에 전달되지 않음 | **Refuted(static)/Open(runtime)** | 소스 경로는 전달함. 당시 request/tensor evidence는 소실됨. |
| 6 | label 2 과다 선택 | **Open** | 분포와 유도 메커니즘은 있으나 class prior/raw output 없음. |

## Minimal RunPod A/B Matrix

모든 실험은 test 문항에서 파생하지 않은 동일한 독립 라벨셋을 사용한다. 최소 48개를 `ambiguous 24 / disambiguated-text 12 / visual-grounded 12`로 고정하고, uncertainty 선택지 위치 0/1/2를 균등화한다. seed, model snapshot, generation settings, sample order를 고정한다.

| Run | 고정값 | 단일 변경 | 분리하는 원인 | 필수 산출물/판정 |
| --- | --- | --- | --- | --- |
| A0 | Qwen 7B, HF, image on | `reasoner_v1` | 기존 baseline | balanced accuracy, confusion, label distribution, raw audit |
| A1 | A0와 동일 | `reasoner_v2` mapping-only | 선택지 매핑 결함 | uncertainty-position별 정확도; A0 대비 개선폭 |
| A2 | A1과 동일 | image omitted diagnostic | 이미지 실제 기여/전달 | visual subset만 하락해야 image path가 유효 |
| A3 | A1과 동일 | processor default vs 명시적 high pixel budget | 이미지 전처리 | OCR/작은 객체 subset 개선 여부 |
| A4 | A1과 동일 | HF `model.generate` vs 별도 vLLM runner | 엔진/chat-template 차이 | 동일 logical message와 image hash에서 label/raw 비교 |
| A5 | A1과 동일 | 7B vs A6000 적합한 더 큰 eligible VLM | 7B 성능 한계 | corrected prompt에서도 남는 오류 감소폭 |
| A6 | A1과 동일 | mapping-only v2 vs 별도 decisiveness variant | reasoner 보수성 | ambiguous 손실 없이 disambiguated/over-uncertainty 개선 여부 |

실행 순서는 **A0→A1**이 필수다. A1이 크게 개선되면 mapping이 주원인이다. 이후 A2/A3로 image, A5로 model을 분리한다. A4는 현재 vLLM 구현이 없으므로 엔진 비교가 정말 필요할 때만 별도 runner로 수행한다. A6는 사용자가 제공한 강한 decisiveness 문구를 production 기본값으로 채택하기 전에 검증하는 용도다.

## Raw Output Preservation Contract for Next RunPod

1. 프로젝트와 `runs/`를 ephemeral container가 아니라 RunPod persistent/network volume 아래에 둔다. Pod 삭제 전 mount가 영속 볼륨인지 확인한다.
2. 실행 시작 즉시 CLI가 `run_id`, `run_dir`, `raw_reasoner.partial.jsonl` 위치를 출력한다.
3. 각 raw 행에 exact logical `prompt_text`, `prompt_sha256`, `image_sha256`, `image_byte_count`, `image_format`, engine/model metadata, raw output을 저장한다.
4. partial은 매 행 flush하고 첫 행 및 25행마다 fsync한다. 정상 완료 때만 `raw_reasoner.jsonl`로 atomic rename한다.
5. 종료 전 `wc -l`, `sha256sum`, label distribution, failure count를 기록하고 run directory 전체를 영속 볼륨에 보존한다.
6. 이 계약은 ephemeral disk 자체 삭제를 복구하지 못한다. 영속 볼륨 사용이 필수 전제다.

## Fix Direction Applied

- `reasoner_v1.yaml`은 A/B 재현용으로 보존했다.
- 기본 prompt를 mapping-only `reasoner_v2.yaml`로 전환했다.
- raw 행에 prompt/image audit 필드를 추가했다.
- 숨은 전체-run tmp 대신 명시적인 durable partial artifact를 추가했다.
- Epic 3는 수정하지 않았다.

## Deferred Risk

Epic 3의 verifier/arbitration 일부는 여전히 label `2`를 uncertainty로 해석한다. Reasoner-only Epic 2 제출에는 직접 영향이 없지만, 향후 Epic 3를 다시 활성화하기 전에는 선택지 위치 기반 의미로 별도 수정해야 한다.
