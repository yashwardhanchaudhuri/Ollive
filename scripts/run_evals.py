#!/usr/bin/env python3
"""Execute the configured application evaluation runner."""

from ollive.evaluation.runner import parse_args, run


def main() -> None:
    """Parse evaluation options and execute the run."""
    args = parse_args()
    run(
        args.dataset,
        args.output,
        args.backends,
        args.repetitions,
        args.limit,
        args.offset,
    )


if __name__ == "__main__":
    main()
