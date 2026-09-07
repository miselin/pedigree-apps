import os
import shutil

from support import buildsystem, steps


class RipgrepPackage(buildsystem.Package):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()

    def name(self):
        return "ripgrep"

    def version(self):
        return "15.2.0"

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            "https://codeload.github.com/BurntSushi/ripgrep/tar.gz/refs/tags/15.2.0",
            target,
            sha256="7605249d3eb0d5f170e3414498e3344e26b1e7a147aec518b57090b80036a562",
        )

    def patches(self, env, srcdir):
        return ["optional-jemalloc.diff"]

    def build(self, env, srcdir):
        steps.cmd(
            ["python3", os.path.join(env["APPS_BASE"], "scripts/build-rust.py"),
             "ripgrep", "--source", srcdir, "--output", os.path.join(srcdir, "pedigree-artifacts")],
            cwd=srcdir, env=env,
        )

    def deploy(self, env, srcdir, deploydir):
        bindir = os.path.join(deploydir, "usr/bin")
        docdir = os.path.join(deploydir, "usr/share/doc/ripgrep")
        os.makedirs(bindir)
        os.makedirs(docdir)
        artifacts = os.path.join(srcdir, "pedigree-artifacts")
        shutil.copy2(os.path.join(artifacts, "rg"), os.path.join(bindir, "rg"))
        for name in ("COPYING", "LICENSE-MIT", "UNLICENSE"):
            shutil.copy2(os.path.join(srcdir, name), docdir)
        for name in ("ripgrep-Cargo.lock", "ripgrep-build.json"):
            shutil.copy2(os.path.join(artifacts, name), docdir)
