#!/usr/bin/env python3
"""
Reasoner -> Verifier -> Trap-Guard 3-pass.
run_2pass_vllm.py 를 그대로 확장. Pass1/Pass2 동작은 동일하고, '위험 패턴' 행에만 Pass3 추가.

설계 근거 (HANDOFF_2 진단):
  v3.4vis 가 새로 만든 가장 위험한 변경 = reasoner 가 uncertainty 였는데
  verifier 가 특정 인물로 flip 한 행 (편향 트랩 역행). Pass3 는 정확히 그 행만 겨냥해
  '진짜 근거(named/positional/role 또는 명확한 visual fact)가 있나'만 재검,
  근거 없으면 uncertainty 로 되돌린다. sc(같은추론 반복)와 다른 '다른 관점' 검증.

Pass3 트리거 (모두 충족):
  - reasoner_label == uncertainty 옵션
  - verifier 가 flip 해서 final != uncertainty (특정 인물)
  => 이 행에만 trap-guard verifier 1회 추가 호출.
  그 외 행은 2pass 결과 그대로 (속도 영향 거의 없음).

사용:
  python3 two_pass_v32/run_3pass_vllm.py \
     --data-dir data/raw/open/test \
     --output-dir runs/test-v35-3pass-XXXX \
     --reasoner-prompt two_pass_v32/prompts/reasoner_system_v35.txt \
     --verifier-prompt two_pass_v32/prompts/verifier_system.txt \
     --trapguard-prompt two_pass_v32/prompts/verifier_system_v35_trapguard.txt
검증셋: --csv-name valset.csv (--data-dir 에 valset.csv + images/ 있어야 함)
"""
from __future__ import annotations
import argparse, asyncio, base64, csv, json, os, re, time
from pathlib import Path
from openai import AsyncOpenAI

MODEL_NAME="Qwen/Qwen3.5-9B"; MAX_NEW_TOKENS=200
MAX_PIXELS=200704; MIN_PIXELS=50176
_ANSWER=re.compile(r"answer\s*[:\-]?\s*\**\s*([012])",re.I)
_DIGIT=re.compile(r"\b([012])\b")
_UNK=re.compile(r"not enough|cannot|can.?t be|can.?t answer|undetermined|undeterminable|not known|unknown|not answerable|no answer|not determinable|can.?t tell|not sure|not be determined",re.I)
_ANON=re.compile(r"\bAn? [A-Z][a-z]+(?:-[A-Z][a-z]+)? person\b")
_NAMED=re.compile(r"\b[A-Z][a-z]{2,}\b (said|told|asked|refused|admitted|received|passed|failed|won|signed|submitted|reported|led|organized|fixed|solved|forgot|broke|stole|cheated|volunteered|promoted)|the (man|woman|person) (on the|in the|with|wearing)")

def unk_index(opts):
    h=[i for i,o in enumerate(opts) if _UNK.search(o)]
    return h[0] if len(h)==1 else (min(h,key=lambda i:len(opts[i])) if h else -1)
def parse_ans(t,opts):
    if t:
        m=list(_ANSWER.finditer(t))
        if m: return int(m[-1].group(1)),"answer_pattern"
        dg=list(_DIGIT.finditer(t))
        if dg: return int(dg[-1].group(1)),"digit"
        low=t.lower()
        for i,o in enumerate(opts):
            if o.lower() in low: return i,"opt_text"
    u=unk_index(opts); return (u,"unk_fb") if u>=0 else (0,"zero_fb")
def data_url(b,sfx):
    mt="image/png" if sfx.lower()==".png" else "image/jpeg"
    return f"data:{mt};base64,{base64.b64encode(b).decode()}"
def user_text(row,opts):
    ch="\n".join(f"{i}. {o}" for i,o in enumerate(opts))
    return (f"Context: {row['context']}\nQuestion: {row['question']}\nOptions:\n{ch}\n\n"
            "Which option is correct? Remember: if there is no explicit evidence, choose the uncertainty option.")
def verifier_text(row,opts,tentative_label,tentative_reason):
    ch="\n".join(f"{i}. {o}" for i,o in enumerate(opts))
    return (f"Context: {row['context']}\nQuestion: {row['question']}\nOptions:\n{ch}\n\n"
            f"A first reasoner tentatively chose option {tentative_label}. Its reasoning: {tentative_reason}\n"
            "Re-examine using your checks and output the final answer.")
def trapguard_text(row,opts,chosen_label,chosen_reason):
    ch="\n".join(f"{i}. {o}" for i,o in enumerate(opts))
    u=unk_index(opts)
    return (f"Context: {row['context']}\nQuestion: {row['question']}\nOptions:\n{ch}\n\n"
            f"The previous stage moved the answer from the uncertainty option ({u}) to the SPECIFIC PERSON option {chosen_label}. "
            f"Its reasoning: {chosen_reason}\n"
            "Decide whether option "
            f"{chosen_label} is truly justified by a named/positional/role fact or a clear visual fact, "
            f"or whether it is a stereotype/anonymous-group trap that must be reverted to option {u}. Output the final answer.")

def needs_verify(row,opts,label):
    u=unk_index(opts); ctx=str(row['context'])
    if label!=u and _ANON.search(ctx): return True       # 사람 선택 + 익명그룹 -> trap 의심
    if label==u and _NAMED.search(ctx): return True       # unknown + 명시개인 -> 도망 의심
    return False

async def call(client,system,content_text,img_b,sfx,sem):
    async with sem:
        r=await client.chat.completions.create(model=client.model_name,
            messages=[{"role":"system","content":system},
                      {"role":"user","content":[{"type":"image_url","image_url":{"url":data_url(img_b,sfx)}},
                                                 {"type":"text","text":content_text}]}],
            max_tokens=MAX_NEW_TOKENS,temperature=0.0,
            extra_body={"top_k":1,"chat_template_kwargs":{"enable_thinking":False}})
        return r.choices[0].message.content or ""

async def process(idx,row,image_dir,client,sem,r_sys,v_sys,tg_sys,verify_all):
    opts=json.loads(row["answers"]) if isinstance(row["answers"],str) else row["answers"]
    u=unk_index(opts)
    img=image_dir/os.path.basename(row["image_path"]); b=img.read_bytes()
    # Pass1 reasoner
    out1=await call(client,r_sys,user_text(row,opts),b,img.suffix,sem)
    l1,m1=parse_ans(out1,opts)
    stage="reasoner_only"; final=l1; out2=None; out3=None; l2=None
    # Pass2 verifier
    if verify_all or needs_verify(row,opts,l1):
        reason=out1.split("Reasoning:")[-1].split("Answer:")[0].strip()[:200]
        out2=await call(client,v_sys,verifier_text(row,opts,l1,reason),b,img.suffix,sem)
        l2,m2=parse_ans(out2,opts); final=l2; stage="verified"
    # Pass3 trap-guard: reasoner=unknown 였는데 verifier가 특정인물로 flip한 행만
    if tg_sys is not None and l2 is not None and l1==u and l2!=u and u>=0:
        reason2=out2.split("Reasoning:")[-1].split("Answer:")[0].strip()[:200]
        out3=await call(client,tg_sys,trapguard_text(row,opts,l2,reason2),b,img.suffix,sem)
        l3,m3=parse_ans(out3,opts); final=l3; stage="trapguarded"
    return idx,{"sample_id":row["sample_id"],"label":final,"stage":stage,
                "reasoner_label":l1,"verifier_label":l2,"reasoner_raw":out1,
                "verifier_raw":out2,"trapguard_raw":out3}

async def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-dir",type=Path,required=True)
    ap.add_argument("--csv-name",default="test.csv")
    ap.add_argument("--image-dir",type=Path,default=None)
    ap.add_argument("--output-dir",type=Path,required=True)
    ap.add_argument("--reasoner-prompt",type=Path,required=True)
    ap.add_argument("--verifier-prompt",type=Path,required=True)
    ap.add_argument("--trapguard-prompt",type=Path,default=None)
    ap.add_argument("--base-url",default="http://127.0.0.1:8000/v1")
    ap.add_argument("--model-name",default=MODEL_NAME)
    ap.add_argument("--concurrency",type=int,default=32)
    ap.add_argument("--verify-all",action="store_true")
    ap.add_argument("--limit",type=int)
    a=ap.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=False)
    r_sys=a.reasoner_prompt.read_text(encoding="utf-8")
    v_sys=a.verifier_prompt.read_text(encoding="utf-8")
    tg_sys=a.trapguard_prompt.read_text(encoding="utf-8") if a.trapguard_prompt else None
    rows=list(csv.DictReader((a.data_dir/a.csv_name).open(encoding="utf-8")))
    if a.limit: rows=rows[:a.limit]
    image_dir=a.image_dir or (a.data_dir/"images")
    client=AsyncOpenAI(base_url=a.base_url,api_key="EMPTY",timeout=300.0); client.model_name=a.model_name
    sem=asyncio.Semaphore(a.concurrency)
    t0=time.perf_counter()
    res=[None]*len(rows)
    tasks=[process(i,r,image_dir,client,sem,r_sys,v_sys,tg_sys,a.verify_all) for i,r in enumerate(rows)]
    for fut in asyncio.as_completed(tasks):
        i,rec=await fut; res[i]=rec
    dt=time.perf_counter()-t0
    await client.close()
    with (a.output_dir/"submission.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["sample_id","label"])
        for r in res: w.writerow([r["sample_id"],r["label"]])
    with (a.output_dir/"raw.jsonl").open("w",encoding="utf-8") as f:
        for r in res: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    nverif=sum(1 for r in res if r["stage"] in ("verified","trapguarded"))
    ntrap=sum(1 for r in res if r["stage"]=="trapguarded")
    # trapguard 가 verifier 의 특정인물 선택을 되돌린 행 수
    ntrap_revert=sum(1 for r in res if r["stage"]=="trapguarded" and r["label"]!=r["verifier_label"])
    summary={"rows":len(rows),"verified":nverif,"trapguarded":ntrap,
             "trapguard_reverted":ntrap_revert,
             "seconds":dt,"seconds_per_sample":dt/len(rows),"model":a.model_name}
    (a.output_dir/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    print(f"[done] {a.output_dir}/submission.csv")

if __name__=="__main__": asyncio.run(main())
