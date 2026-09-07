import json
import os
from pathlib import Path
import shutil

from support import buildsystem, steps


EXPERIMENTAL_REASON = "Large heaps, concurrent JIT/GC, WebAssembly, and inspector remain unqualified."
PINS = json.loads((Path(__file__).resolve().parents[2] /
                   "language-ports/v8/source.json").read_text())


class V8Package(buildsystem.Package):
    def name(self):
        return "v8"

    def version(self):
        return PINS["version"]

    def build(self, env, srcdir):
        steps.cmd(
            ["python3", os.path.join(env["APPS_BASE"], "scripts/build-v8.py"),
             "--cache", os.path.join(env["BUILD_BASE"], "v8"),
             "--jobs", os.environ.get("PEDIGREE_APPS_JOBS", "4")],
            cwd=srcdir, env=env,
        )

    def deploy(self, env, srcdir, deploydir):
        shutil.copytree(os.path.join(env["BUILD_BASE"], "v8/root"), deploydir,
                        symlinks=True, dirs_exist_ok=True)
