"""Explicitly publish a validated versioned expansion; never auto-select evidence."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark.cohort_versions import publish_extension
from benchmark.research_protocol import bind


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--parent-split',required=True,type=Path)
    parser.add_argument('--additions-manifest',required=True,type=Path)
    parser.add_argument('--output-directory',required=True,type=Path)
    parser.add_argument('--incident-aliases',required=True,type=Path,help='Reviewed explicit alias JSON object')
    parser.add_argument('--seed',type=int,default=1729)
    args=parser.parse_args();root=args.root.resolve()
    result=publish_extension(root,args.output_directory,bind(root/args.parent_split,root),
        bind(root/args.additions_manifest,root),json.loads((root/args.incident_aliases).read_text()),args.seed)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
