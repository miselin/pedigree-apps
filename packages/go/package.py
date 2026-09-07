import os
import shutil

from support import buildsystem, steps


class GoPackage(buildsystem.Package):
    def name(self):
        return "go"

    def version(self):
        return "1.26.5"

    def install_deps(self):
        return ["ca-certificates"]

    def download(self, env, target):
        steps.download(
            "https://go.dev/dl/go%s.src.tar.gz" % self.version(),
            target,
            sha256="495be4bc87176ac567392e5b4116abd98466d33d7b49d41e764ccc6976b2dc42",
        )

    def build(self, env, srcdir):
        command_env = env.copy()
        command_env["PEDIGREE_GO_SOURCE_DIR"] = srcdir
        command_env["PEDIGREE_GO_BUILD_DIR"] = os.path.join(
            env["BUILD_BASE"], "language-ports", "go"
        )
        steps.cmd(
            [os.path.join(env["APPS_BASE"], "scripts", "build-go-pedigree.sh")],
            cwd=srcdir,
            env=command_env,
        )

    def deploy(self, env, srcdir, deploydir):
        root = os.path.join(
            env["BUILD_BASE"], "language-ports", "go", "native-root"
        )
        shutil.copytree(root, deploydir, dirs_exist_ok=True)
