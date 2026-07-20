#!/usr/bin/env python3
import argparse
from pathlib import Path
from ollive.evaluation.report import generate

parser = argparse.ArgumentParser()
parser.add_argument("--results", type=Path, required=True)
parser.add_argument("--output-dir", type=Path, required=True)
parser.add_argument("--calibration", type=Path)
args = parser.parse_args()
print(generate(args.results, args.output_dir, args.calibration))
