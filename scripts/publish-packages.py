#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Keep the helper runnable from any working directory without installation.
REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

from pup.dist import DEFAULT_PROJECT, upload_key_from_datastore


def main():
    parser = argparse.ArgumentParser(
        description="Publish completed Pedigree package artifacts."
    )
    parser.add_argument("packages", nargs="*", help="package names to publish")
    parser.add_argument(
        "--all",
        action="store_true",
        help="publish every active package",
    )
    parser.add_argument(
        "--project",
        default=DEFAULT_PROJECT,
        help="GCP project containing the legacy upload credential",
    )
    args = parser.parse_args()
    if args.all and args.packages:
        parser.error("--all cannot be combined with package names")
    if not args.all and not args.packages:
        parser.error("provide package names or use --all")

    environment = os.environ.copy()
    upload_key = environment.pop("UPLOAD_KEY", None)
    selection = [] if args.all else ["--only", *args.packages]

    subprocess.run(
        [
            str(REPOSITORY / "buildPackages.sh"),
            *selection,
            "--audit-only",
        ],
        cwd=REPOSITORY,
        env=environment.copy(),
        check=True,
    )

    if not upload_key:
        try:
            upload_key = upload_key_from_datastore(args.project)
        except RuntimeError as error:
            raise SystemExit(str(error)) from error
    environment["UPLOAD_KEY"] = upload_key

    subprocess.run(
        [
            str(REPOSITORY / "buildPackages.sh"),
            *selection,
            "--upload-only",
        ],
        cwd=REPOSITORY,
        env=environment.copy(),
        check=True,
    )


if __name__ == "__main__":
    main()
