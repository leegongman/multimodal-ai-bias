#!/usr/bin/env python3
"""
Reasoner(v3.1) + Verifier 2-pass. 공개 0.99633 예시 구조.
- Pass1: v3.1 reasoner가 1차 답+근거 생성 (기존과 동일)
- Pass2: '재검토 가치 있는 행'에만 verifier 호출 → 최종답은 verifier LLM이 생성
  트리거(좁게): (a) reasoner=사람인데 context가 익명그룹 진술  (b) reasoner=unknown인데 이름/위치/역할 명시
- 트리거 안된 행은 reasoner 답 유지.
- 최종 라벨은 항상 LLM 생성 텍스트에서 파싱(규칙 준수).

사용:
  python3 run_2pass_vllm.py --data-dir <dir(test.csv,images/)> --output-dir <out> \
     --reasoner-prompt prompts/reasoner_system_v31.txt \
     --verifier-prompt prompts/verifier_system.txt \
     [--verify-all]   # 모든 행 verifier (느림). 기본은 트리거 행만.
검증셋이면 --data-dir 에 valset.csv를 test.csv로 두거나, --csv-name valset.csv 사용.
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

def needs_verify(row,opts,label):
    u=unk_index(opts); ctx=str(row['context'])
    if label!=u and _ANON.search(ctx): return True       # 사람 선택 + 익명그룹 → trap 의심
    if label==u and _NAMED.search(ctx): return True       # unknown + 명시개인 → 도망 의심
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

async def process(idx,row,image_dir,client,sem,r_sys,v_sys,verify_all):
    opts=json.loads(row["answers"]) if isinstance(row["answers"],str) else row["answers"]
    img=image_dir/os.path.basename(row["image_path"]); b=img.read_bytes()
    # Pass1
    out1=await call(client,r_sys,user_text(row,opts),b,img.suffix,sem)
    l1,m1=parse_ans(out1,opts)
    stage="reasoner_only"; final=l1; out2=None
    if verify_all or needs_verify(row,opts,l1):
        reason=out1.split("Reasoning:")[-1].split("Answer:")[0].strip()[:200]
        out2=await call(client,v_sys,verifier_text(row,opts,l1,reason),b,img.suffix,sem)
        l2,m2=parse_ans(out2,opts); final=l2; stage="verified"
    return idx,{"sample_id":row["sample_id"],"label":final,"stage":stage,
                "reasoner_label":l1,"reasoner_raw":out1,"verifier_raw":out2}

async def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-dir",type=Path,required=True)
    ap.add_argument("--csv-name",default="test.csv")
    ap.add_argument("--image-dir",type=Path,default=None)
    ap.add_argument("--output-dir",type=Path,required=True)
    ap.add_argument("--reasoner-prompt",type=Path,required=True)
    ap.add_argument("--verifier-prompt",type=Path,required=True)
    ap.add_argument("--base-url",default="http://127.0.0.1:8000/v1")
    ap.add_argument("--model-name",default=MODEL_NAME)
    ap.add_argument("--concurrency",type=int,default=32)
    ap.add_argument("--verify-all",action="store_true")
    ap.add_argument("--limit",type=int)
    a=ap.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=False)
    r_sys=a.reasoner_prompt.read_text(encoding="utf-8")
    v_sys=a.verifier_prompt.read_text(encoding="utf-8")
    rows=list(csv.DictReader((a.data_dir/a.csv_name).open(encoding="utf-8")))
    if a.limit: rows=rows[:a.limit]
    image_dir=a.image_dir or (a.data_dir/"images")
    client=AsyncOpenAI(base_url=a.base_url,api_key="EMPTY",timeout=300.0); client.model_name=a.model_name
    sem=asyncio.Semaphore(a.concurrency)
    t0=time.perf_counter()
    res=[None]*len(rows)
    tasks=[process(i,r,image_dir,client,sem,r_sys,v_sys,a.verify_all) for i,r in enumerate(rows)]
    for fut in asyncio.as_completed(tasks):
        i,rec=await fut; res[i]=rec
    dt=time.perf_counter()-t0
    await client.close()
    with (a.output_dir/"submission.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["sample_id","label"])
        for r in res: w.writerow([r["sample_id"],r["label"]])
    with (a.output_dir/"raw.jsonl").open("w",encoding="utf-8") as f:
        for r in res: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    nverif=sum(1 for r in res if r["stage"]=="verified")
    nflip=sum(1 for r in res if r["stage"]=="verified" and r["label"]!=r["reasoner_label"])
    summary={"rows":len(rows),"verified":nverif,"flipped_by_verifier":nflip,
             "seconds":dt,"seconds_per_sample":dt/len(rows),"model":a.model_name}
    (a.output_dir/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    print(f"[done] {a.output_dir}/submission.csv")

if __name__=="__main__": asyncio.run(main())
