import os

from support import buildsystem, steps


EXPERIMENTAL_REASON = "Native compile/test/run on Pedigree is not yet qualified."


class RustPackage(buildsystem.Package):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()

    def name(self):
        return "rust"

    def version(self):
        return "1.85.1"

    def options(self):
        return self._options

    def build_requires(self):
        return ["ca-certificates"]

    def install_deps(self):
        return self.build_requires()

    def deploy(self, env, srcdir, deploydir):
        steps.cmd(
            ["python3", os.path.join(env["APPS_BASE"], "scripts/build-rust.py"),
             "native", "--output", deploydir, "--normalize-native",
             "--native-strip", env["CROSS_STRIP"]],
            cwd=srcdir, env=env,
        )
