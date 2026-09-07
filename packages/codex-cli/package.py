import hashlib
import json
import os
import shutil

from support import buildsystem, steps


SOURCE_REVISION = "694b6319d3ad2399f6e435760a22d9b9357f0697"
EXPERIMENTAL_REASON = "Kernel stalls block terminal/RPC qualification; PTY commands need TIOCSPTLCK; authenticated sessions are unqualified."


class CodexCliPackage(buildsystem.Package):
    def name(self):
        return "codex-cli"

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
        return ["../../codex-app-server/patches/pedigree.diff", "pedigree.diff"]

    def build(self, env, srcdir):
        steps.cmd(
            [
                "python3",
                os.path.join(env["APPS_BASE"], "scripts/build-codex-app-server.py"),
                "build",
                "--component", "cli",
                "--source", srcdir,
                "--output", os.path.join(srcdir, "pedigree-artifacts"),
                # Keep the core and terminal compiler working sets separate.
                "--jobs", "1",
            ],
            cwd=srcdir,
            env=env,
        )

    def deploy(self, env, srcdir, deploydir):
        root = os.path.join(srcdir, "pedigree-artifacts", "root")
        shutil.copytree(root, deploydir, symlinks=True, dirs_exist_ok=True)
        docdir = os.path.join(deploydir, "usr/share/doc/codex-cli")
        shutil.copy2(os.path.join(self._path, "README.md"), os.path.join(docdir, "README.md"))
        # The syntax/theme crate stores these required notices in a compressed
        # asset, so the general LICENSE-file scan cannot collect them.
        notices = os.path.join(docdir, "dependencies/two-face-assets")
        shutil.copytree(os.path.join(self._path, "licenses"), notices)
        with open(os.path.join(docdir, "build.json")) as source:
            provenance = json.load(source)
        with open(os.path.join(notices, "ACKNOWLEDGEMENTS.md"), "rb") as source:
            provenance["two_face_asset_notices_sha256"] = hashlib.sha256(source.read()).hexdigest()
        with open(os.path.join(docdir, "build.json"), "w") as destination:
            json.dump(provenance, destination, indent=2)
            destination.write("\n")
