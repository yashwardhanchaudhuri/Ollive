#!/usr/bin/env python3
import argparse
from pathlib import Path
from ollive.evaluation.comprehensive_report import generate

parser = argparse.ArgumentParser()
parser.add_argument("--results", type=Path, required=True)
parser.add_argument("--calibration", type=Path, required=True)
parser.add_argument("--dataset", type=Path, required=True)
parser.add_argument("--output-dir", type=Path, required=True)
args = parser.parse_args()
print(generate(args.results, args.calibration, args.dataset, args.output_dir))
