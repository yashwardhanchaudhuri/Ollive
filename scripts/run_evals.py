#!/usr/bin/env python3
from ollive.evaluation.runner import parse_args, run

if __name__ == "__main__":
    args = parse_args()
    run(args.dataset, args.output, args.backends, args.repetitions, args.limit)
