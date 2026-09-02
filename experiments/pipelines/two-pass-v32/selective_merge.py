#!/usr/bin/env python3
"""선택적 머지: 기존 2pass(0.99617)를 베이스로, '익명그룹 트랩이 명백한 행'에서만
v3.3의 답(unknown 교정)으로 교체. 최종답은 모두 LLM 생성 라벨(기존 or v3.3 LLM 출력)이며
룰로 라벨을 새로 만들지 않는다(어느 LLM 답을 채택할지 트리거로 선택할 뿐).

트리거(모두 충족해야 교체):
  1) 기존 답 != v3.3 답
  2) v3.3 답 == 해당 문항의 unknown 옵션 (트랩 교정 방향만)
  3) context가 익명그룹 진술 (An/A  X person ...)
  4) 질문이 일반 성향 (more/less likely 등)
검증셋에서 이 트리거는 amb_protected(정답 unknown)만 50/50 발동, dis 0건 → 안전.

사용:
  python3 two_pass_v32/selective_merge.py \
    --base runs/test-2pass-20260624-1225/submission.csv \
    --cand runs/test-v33-2pass-XXXX/submission.csv \
    --test data/raw/open/test/test.csv \
    --out  runs/test-merge-v33trap/submission.csv
"""
import argparse, csv, json, re, os
from pathlib import Path

_UNK=re.compile(r"not enough|cannot|can.?t be|can.?t answer|undetermined|undeterminable|not known|unknown|not answerable|no answer|not determinable|can.?t tell|not sure|not be determined",re.I)
_ANON=re.compile(r"\bAn? [A-Z][a-z]+(?:-[A-Z][a-z]+)? person\b")
_LIKELY=re.compile(r"\b(more likely|less likely|likely to|likely just|likely the|seen as|tends to|generally)\b",re.I)

def uidx(opts):
    h=[i for i,o in enumerate(opts) if _UNK.search(o)]
    return h[0] if len(h)==1 else (min(h,key=lambda i:len(opts[i])) if h else -1)

def load(p): return {r["sample_id"]:int(r["label"]) for r in csv.DictReader(open(p))}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",required=True)
    ap.add_argument("--cand",required=True)
    ap.add_argument("--test",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    base=load(a.base); cand=load(a.cand)
    test={r["sample_id"]:json.loads(r["answers"]) for r in csv.DictReader(open(a.test))}
    ctxq={r["sample_id"]:(r["context"],r["question"]) for r in csv.DictReader(open(a.test))}
    out={}; swapped=[]
    for sid in base:
        b=base[sid]; c=cand.get(sid,b); opts=test[sid]; u=uidx(opts)
        ctx,q=ctxq[sid]
        trigger = (b!=c) and (c==u) and bool(_ANON.search(ctx)) and bool(_LIKELY.search(q))
        out[sid]=c if trigger else b
        if trigger: swapped.append(sid)
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    with open(a.out,"w",newline="") as f:
        w=csv.writer(f); w.writerow(["sample_id","label"])
        for sid in base: w.writerow([sid,out[sid]])
    print(f"[merge] base={a.base}")
    print(f"[merge] cand={a.cand}")
    print(f"[merge] 교체된 행: {len(swapped)} / {len(base)}")
    print(f"[merge] 기존 대비 변경: {sum(1 for k in out if out[k]!=base[k])}")
    print(f"[merge] out -> {a.out}")
    print("[merge] swapped sample_ids (앞 20):", swapped[:20])

if __name__=="__main__":
    main()
