import argparse, subprocess, sys, hashlib, json, tempfile
from pathlib import Path

def digest(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(); p.add_argument("--seed",type=int,default=20261022); p.add_argument("--scale",choices=["starter","full"],default="starter"); a=p.parse_args()
    with tempfile.TemporaryDirectory() as td:
        roots=[Path(td)/"a",Path(td)/"b"]
        for root in roots:
            subprocess.run([sys.executable,str(Path(__file__).with_name("generate.py")),"--out",str(root),"--seed",str(a.seed),"--scale",a.scale],check=True,stdout=subprocess.DEVNULL)
        files1=sorted(str(x.relative_to(roots[0])) for x in roots[0].rglob("*") if x.is_file())
        files2=sorted(str(x.relative_to(roots[1])) for x in roots[1].rglob("*") if x.is_file())
        # SQLite database bytes can differ due to internal metadata; compare logical exports and manifest.
        comparable=[x for x in files1 if x!="traceability.db"]
        mismatches=[]
        for rel in comparable:
            if digest(roots[0]/rel)!=digest(roots[1]/rel): mismatches.append(rel)
        print(json.dumps({"seed":a.seed,"scale":a.scale,"same_file_list":files1==files2,"mismatches":mismatches,"reproducible":files1==files2 and not mismatches},indent=2))
        if mismatches: sys.exit(1)
if __name__=="__main__": main()
