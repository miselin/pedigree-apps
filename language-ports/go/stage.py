#!/usr/bin/env python3
"""Stage the target distribution without host tools or source-test fixtures."""

import os
from pathlib import Path
import shutil
import sys


def stage(source, probe, target, smoke):
    incomplete = target.with_name(target.name + ".incomplete")
    shutil.rmtree(incomplete, ignore_errors=True)
    goroot = incomplete / "usr/lib/go"
    goroot.mkdir(parents=True)
    for name in ("LICENSE", "PATENTS", "VERSION", "go.env"):
        shutil.copy2(source / name, goroot / name)
    for name in ("src", "pkg/include", "lib/time"):
        shutil.copytree(
            source / name,
            goroot / name,
            ignore=shutil.ignore_patterns(
                "testdata", "*_test.go", "*.syso", ".DS_Store"
            ),
        )
    # Generated sources are shipped, so upstream regeneration scripts are not
    # needed to compile the standard library or tools on the target.
    for name in ("src", "pkg/include", "lib/time"):
        for path in (goroot / name).rglob("*"):
            if path.is_file():
                with path.open("rb") as source_file:
                    is_script = source_file.read(2) == b"#!"
                if is_script:
                    path.unlink()
                    continue
                path.chmod(0o644)
    shutil.copytree(source / "bin/pedigree_amd64", goroot / "bin")
    shutil.copytree(
        source / "pkg/tool/pedigree_amd64", goroot / "pkg/tool/pedigree_amd64"
    )
    bindir = incomplete / "usr/bin"
    bindir.mkdir(parents=True)
    for name in ("go", "gofmt"):
        path = bindir / name
        path.write_text(
            "#!/bin/sh\n"
            "export GOROOT=${GOROOT:-/usr/lib/go}\n"
            "export CGO_ENABLED=0 GOTOOLCHAIN=local\n"
            'exec "$GOROOT/bin/' + name + '" "$@"\n'
        )
        path.chmod(0o755)
    shutil.copy2(probe, bindir / "go-qualify")
    shutil.copytree(smoke, incomplete / "usr/share/go/native-smoke")
    shutil.rmtree(target, ignore_errors=True)
    os.replace(incomplete, target)


if __name__ == "__main__":
    stage(*(Path(arg).resolve() for arg in sys.argv[1:]))
