#!/usr/bin/env python3
"""Publish a trained model to Hugging Face.

Nothing is uploaded unless you ask for it: the default is a dry run that prints
exactly what would be sent. Authentication comes from the HF_TOKEN environment
variable.

    # See what would happen (uploads nothing)
    uv run python -m scripts.publish_model classifier --repo daley30/cosmic-classifier

    # Actually upload, to a private repo
    export HF_TOKEN=hf_...
    uv run python -m scripts.publish_model classifier \\
        --repo daley30/cosmic-classifier --push

    # Publish it publicly (deliberate: read the model card first)
    uv run python -m scripts.publish_model classifier \\
        --repo daley30/cosmic-classifier --push --public
"""

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.model_publish import PUBLISHABLE_MODELS, publish_model  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "model",
        choices=sorted(PUBLISHABLE_MODELS),
        help="Which trained model to publish",
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="Target Hugging Face repo id, e.g. daley30/cosmic-classifier",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Actually upload. Without this the run is a dry run.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Project artifact root (defaults to this checkout, independent of cwd)",
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="Create the repo public. Repos are private by default.",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Hugging Face write token. Defaults to $HF_TOKEN.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        plan = publish_model(
            args.model,
            args.repo,
            token=args.token,
            root=args.root,
            private=not args.public,
            dry_run=not args.push,
        )
    except (FileNotFoundError, ValueError, ImportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    visibility = "public" if args.public else "private"
    if plan.uploaded:
        print(f"Published {plan.model_key} to {plan.repo_id} ({visibility})")
        print(f"  https://huggingface.co/{plan.repo_id}")
        return 0

    print(
        f"Dry run — nothing uploaded. Would publish to {plan.repo_id} ({visibility}):"
    )
    print(f"  weights: {plan.artifact}")
    print(f"  card:    {len(plan.card.splitlines())} lines")
    print("\n--- model card ---")
    print(plan.card)
    print("Re-run with --push to upload.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
