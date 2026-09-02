#!/usr/bin/env python3
"""절충 머지: 기존 v3.1 2pass(0.99617)를 베이스로, v3.4vis 의 '명확히 좋은' 변경만 채택.
HANDOFF_2 진단 결과 v3.4vis 233개 변경 중:
  - 트랩교정(익명그룹->unknown) 54 : 명확히 좋음 (BBQ 편향 트랩 정답화)
  - 이미지근거(추론이 이미지 언급)  30 : 좋을 가능성 높음
  - 기타/불확실                    149 : 위험 (특히 unknown->특정인물 80개) -> 버림
=> 좋은 84개만 베이스에 얹는다. 최종 라벨은 모두 LLM 생성 (기존 or v3.4vis LLM 출력).
   룰로 라벨을 새로 만들지 않고, 어느 LLM 답을 채택할지 트리거로만 선택.

채택 트리거 (기존 답 != v3.4vis 답 이고 아래 중 하나):
  (A) 트랩교정: v3.4vis 답 == 해당 문항 unknown 옵션 AND context 가 익명그룹 진술
  (B) 이미지근거: v3.4vis reasoner_raw 가 구체 시각 사실을 언급 (img_pat) AND (A) 아님
그 외(기타/불확실 149)는 기존 유지.

사용:
  python3 two_pass_v32/selective_merge_v34vis.py \
    --base runs/test-2pass-20260624-1225/submission.csv \
    --cand runs/test-v34vis-20260628-0345/submission.csv \
    --cand-raw runs/test-v34vis-20260628-0345/raw.jsonl \
    --test data/raw/open/test/test.csv \
    --out  runs/test-merge-v34vis-good84/submission.csv
"""
import argparse, csv, json, re
from pathlib import Path

_UNK=re.compile(r"not enough|cannot|can.?t be|can.?t answer|undetermined|undeterminable|not known|unknown|not answerable|no answer|not determinable|can.?t tell|not sure|not be determined",re.I)
_ANON=re.compile(r"\bAn? [A-Z][a-z]+(?:-[A-Z][a-z]+)? person\b")
_IMG=re.compile(r"\b(image|photo|picture|shown|visible|wearing|holding|pointing|positioned|left|right|center|foreground|background|standing|sitting|그림|사진|이미지|보이|입고|착용|들고)\b",re.I)

def uidx(opts):
    h=[i for i,o in enumerate(opts) if _UNK.search(o)]
    return h[0] if len(h)==1 else (min(h,key=lambda i:len(opts[i])) if h else -1)
def load(p): return {r["sample_id"]:int(r["label"]) for r in csv.DictReader(open(p,encoding="utf-8"))}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",required=True)
    ap.add_argument("--cand",required=True)
    ap.add_argument("--cand-raw",required=True)
    ap.add_argument("--test",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    base=load(a.base); cand=load(a.cand)
    test={r["sample_id"]:json.loads(r["answers"]) for r in csv.DictReader(open(a.test,encoding="utf-8"))}
    ctx ={r["sample_id"]:r["context"] for r in csv.DictReader(open(a.test,encoding="utf-8"))}
    raw={}
    for line in open(a.cand_raw,encoding="utf-8"):
        o=json.loads(line); raw[o["sample_id"]]=o.get("reasoner_raw") or ""

    out={}; n_trap=0; n_img=0; n_skip=0
    for sid in base:
        b=base[sid]; c=cand.get(sid,b); opts=test[sid]; u=uidx(opts)
        if b==c:
            out[sid]=b; continue
        is_trap = (c==u) and bool(_ANON.search(ctx[sid]))
        is_img  = (not is_trap) and bool(_IMG.search(raw.get(sid,"")))
        if is_trap:
            out[sid]=c; n_trap+=1
        elif is_img:
            out[sid]=c; n_img+=1
        else:
            out[sid]=b; n_skip+=1   # 위험/불확실 -> 기존 유지

    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    with open(a.out,"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["sample_id","label"])
        for sid in base: w.writerow([sid,out[sid]])
    changed=sum(1 for k in out if out[k]!=base[k])
    print(f"[merge] base={a.base}")
    print(f"[merge] cand={a.cand}")
    print(f"[merge] 채택 트랩교정: {n_trap}")
    print(f"[merge] 채택 이미지근거: {n_img}")
    print(f"[merge] 버린 기타/불확실: {n_skip}")
    print(f"[merge] 기존 대비 총 변경: {changed}")
    print(f"[merge] out -> {a.out}")

if __name__=="__main__":
    main()
