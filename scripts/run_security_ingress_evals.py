#!/usr/bin/env python3
"""Execute a dataset through only the runtime ingress Security LM."""

from ollive.evaluation.security_runner import parse_args, run


def main() -> None:
    """Parse ingress-evaluation options and execute the run."""
    args = parse_args()
    run(
        args.dataset,
        args.output,
        args.repetitions,
        args.limit,
        args.offset,
        args.security_backend,
    )


if __name__ == "__main__":
    main()
