import os
import shutil

from support import buildsystem, steps


SOURCE_REVISION = "694b6319d3ad2399f6e435760a22d9b9357f0697"
EXPERIMENTAL_REASON = "SMP config/read faults; authentication and sandboxed execution are unqualified."


class CodexAppServerPackage(buildsystem.Package):
    def name(self):
        return "codex-app-server"

    def version(self):
        return "0.0.0.20260907"

    def install_deps(self):
        return ["ca-certificates"]

    def download(self, env, target):
        steps.download(
            "https://codeload.github.com/openai/codex/tar.gz/%s" % SOURCE_REVISION,
            target,
            sha256="a7be863aed08b3ad8359e4338f81585773182dc6e4cb67c993d534d253e6cac4",
        )

    def patches(self, env, srcdir):
        return ["pedigree.diff"]

    def build(self, env, srcdir):
        steps.cmd(
            [
                "python3",
                os.path.join(env["APPS_BASE"], "scripts/build-codex-app-server.py"),
                "build",
                "--source",
                srcdir,
                "--output",
                os.path.join(srcdir, "pedigree-artifacts"),
            ],
            cwd=srcdir,
            env=env,
        )

    def deploy(self, env, srcdir, deploydir):
        root = os.path.join(srcdir, "pedigree-artifacts", "root")
        shutil.copytree(root, deploydir, symlinks=True, dirs_exist_ok=True)
        docdir = os.path.join(deploydir, "usr/share/doc/codex-app-server")
        os.makedirs(docdir, exist_ok=True)
        for name in ("LICENSE", "NOTICE"):
            shutil.copy2(os.path.join(srcdir, name), docdir)
        shutil.copy2(os.path.join(self._path, "README.md"), docdir)
