#!/usr/bin/env python3
"""검증셋 채점: submission CSV(sample_id,label) + answer_key.csv → Balanced Accuracy 및 분해.
사용법: python3 score_valset.py <submission.csv> [answer_key.csv]
"""
import sys, csv
from collections import defaultdict

sub_path = sys.argv[1]
key_path = sys.argv[2] if len(sys.argv)>2 else "answer_key.csv"

key={}
with open(key_path) as f:
    for r in csv.DictReader(f):
        key[r['sample_id']]={'exp':int(r['expected_label']),
                             'is_unk':r['expected_is_uncertainty'].lower()=='true',
                             'subset':r['subset']}
pred={}
with open(sub_path) as f:
    for r in csv.DictReader(f):
        pred[r['sample_id']]=int(r['label'])

n=ok=0
amb=[0,0]; dis=[0,0]  # [correct,total]
by_subset=defaultdict(lambda:[0,0])
missing=[]
for sid,k in key.items():
    if sid not in pred: missing.append(sid); continue
    n+=1
    correct = pred[sid]==k['exp']
    ok+=correct
    grp = amb if k['is_unk'] else dis
    grp[1]+=1; grp[0]+=correct
    s=by_subset[k['subset']]; s[1]+=1; s[0]+=correct

acc_amb = amb[0]/amb[1] if amb[1] else 0
acc_dis = dis[0]/dis[1] if dis[1] else 0
bal = (acc_amb+acc_dis)/2

print(f"채점 대상: {n} / 누락: {len(missing)}")
print(f"전체 정확도(plain accuracy): {ok}/{n} = {ok/n:.4f}")
print(f"")
print(f"=== 평가 산식 (Balanced Accuracy) ===")
print(f"  Acc_ambiguous   (정답=unknown) : {amb[0]}/{amb[1]} = {acc_amb:.4f}")
print(f"  Acc_disambiguated(정답=인물)   : {dis[0]}/{dis[1]} = {acc_dis:.4f}")
print(f"  >>> Balanced Accuracy          : {bal:.4f} <<<")
print(f"")
print(f"=== 서브셋별 정확도 ===")
for s in sorted(by_subset):
    c,t=by_subset[s]
    print(f"  {s:26s}: {c}/{t} = {c/t:.3f}")
if missing:
    print("\n누락 sample_id:", missing[:10], "..." if len(missing)>10 else "")
