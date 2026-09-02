#!/usr/bin/env python3

import sys


def main():
    print(
        "buildInChroot.py has been retired; use ./buildPackages.sh so the "
        "repository-owned Docker builder is selected consistently.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
