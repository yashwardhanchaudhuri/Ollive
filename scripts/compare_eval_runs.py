#!/usr/bin/env python3
import argparse
from pathlib import Path
from ollive.evaluation.compare import generate_comparison

parser = argparse.ArgumentParser()
parser.add_argument("--baseline", type=Path, required=True)
parser.add_argument("--candidate", type=Path, required=True)
parser.add_argument("--output-dir", type=Path, required=True)
args = parser.parse_args()
print(generate_comparison(args.baseline, args.candidate, args.output_dir))
