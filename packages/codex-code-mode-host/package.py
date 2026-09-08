import os
import shutil

from support import buildsystem, steps


EXPERIMENTAL_REASON = "Concurrent sessions, large heaps, full V8 sandbox reservations, and gRPC remain unqualified."


class CodexCodeModeHostPackage(buildsystem.Package):
    def name(self):
        return "codex-code-mode-host"

    def version(self):
        return "0.0.0.20260907"

    def install_deps(self):
        return ["ca-certificates"]

    def download(self, env, target):
        steps.download(
            "https://codeload.github.com/openai/codex/tar.gz/694b6319d3ad2399f6e435760a22d9b9357f0697",
            target,
            sha256="a7be863aed08b3ad8359e4338f81585773182dc6e4cb67c993d534d253e6cac4",
        )

    def build(self, env, srcdir):
        steps.cmd(
            ["python3", os.path.join(env["APPS_BASE"], "scripts/build-codex-app-server.py"),
             "build", "--component", "code-mode-host", "--source", srcdir,
             "--output", os.path.join(srcdir, "pedigree-artifacts"), "--jobs", "1"],
            cwd=srcdir, env=env,
        )

    def patches(self, env, srcdir):
        return ["pedigree.diff"]

    def deploy(self, env, srcdir, deploydir):
        shutil.copytree(os.path.join(srcdir, "pedigree-artifacts/root"), deploydir,
                        symlinks=True, dirs_exist_ok=True)
        shutil.copy2(os.path.join(self._path, "README.md"),
                     os.path.join(deploydir, "usr/share/doc/codex-code-mode-host/README.md"))
