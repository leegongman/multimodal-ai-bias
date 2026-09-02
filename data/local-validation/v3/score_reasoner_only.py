#!/usr/bin/env python3
"""2-pass raw.jsonl에서 reasoner_label만 뽑아 단일 reasoner 효과를 채점.
사용법: python3 score_reasoner_only.py <raw.jsonl> [answer_key.csv]
출력: submission 형식 임시파일 만들어 score_valset.py와 동일 산식."""
import sys, json, csv, subprocess, tempfile, os
raw=sys.argv[1]
key=sys.argv[2] if len(sys.argv)>2 else "answer_key.csv"
rows=[json.loads(l) for l in open(raw)]
tmp=tempfile.NamedTemporaryFile("w",suffix=".csv",delete=False,newline="")
w=csv.writer(tmp); w.writerow(["sample_id","label"])
for r in rows: w.writerow([r["sample_id"], r["reasoner_label"]])
tmp.close()
here=os.path.dirname(os.path.abspath(__file__))
subprocess.run([sys.executable, os.path.join(here,"score_valset.py"), tmp.name, key])
os.unlink(tmp.name)
