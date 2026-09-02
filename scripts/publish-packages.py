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
    parser.add_argument("packages", nargs="+", help="package names to publish")
    parser.add_argument(
        "--project",
        default=DEFAULT_PROJECT,
        help="GCP project containing the legacy upload credential",
    )
    args = parser.parse_args()

    environment = os.environ.copy()
    if not environment.get("UPLOAD_KEY"):
        try:
            environment["UPLOAD_KEY"] = upload_key_from_datastore(args.project)
        except RuntimeError as error:
            raise SystemExit(str(error)) from error

    subprocess.run(
        [
            str(REPOSITORY / "buildPackages.sh"),
            "--only",
            *args.packages,
            "--upload-only",
        ],
        cwd=REPOSITORY,
        env=environment,
        check=True,
    )


if __name__ == "__main__":
    main()
