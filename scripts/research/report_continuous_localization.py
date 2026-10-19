"""Aggregate recorded development OOF artifacts only; never score or read fresh batches."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
LANES={"A":ROOT.parent/"FaultSeeker--coverage", "B":ROOT.parent/"FaultSeeker--selector", "C":ROOT.parent/"FaultSeeker--learned"}

def wilson(hits,n):
    z=1.959963984540054
    den=1+z*z/n
    center=(hits/n+z*z/(2*n))/den
    half=z*math.sqrt(hits/n*(1-hits/n)/n+z*z/(4*n*n))/den
    return [center-half,center+half]

def collect():
    output=[]
    for lane,root in LANES.items():
        directory=root/"reports/localization_continuous"
        for path in sorted(directory.glob("*/results*.json")):
            data=json.loads(path.read_text(encoding="utf-8"))
            variants=data.get("variants")
            if not variants and data.get("oof_ranks") is not None:
                variants={data.get("method","recorded_method"):data}
            for name,item in (variants or {}).items():
                ranks=item.get("oof_ranks")
                if ranks is None:
                    continue
                if len(ranks)!=110:
                    raise ValueError("Unexpected original development population")
                counts=[sum(r is not None and r<=k for r in ranks) for k in (1,3,5)]
                if item.get("hits") is not None and item["hits"]!=counts:
                    raise ValueError("Recorded hit counts disagree with recorded OOF ranks")
                output.append({"lane":lane,"artifact":str(path.resolve()),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"variant":name,"hits":counts,"n":110,"percent":[100*h/110 for h in counts],"wilson95":[wilson(h,110) for h in counts],"exploratory":True})
    return output

if __name__=="__main__":
    print(json.dumps({"source":"saved original110 OOF artifacts only","records":collect(),"ranking_runs":0,"network_requests":0},indent=2))
