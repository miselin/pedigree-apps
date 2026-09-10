from support import buildsystem
from support import steps


class PatchPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(PatchPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = "xz"

    def name(self):
        return "patch"

    def version(self):
        return "2.8"

    def build_requires(self):
        return []

    def install_deps(self):
        return []

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            "https://ftp.gnu.org/gnu/patch/patch-%s.tar.xz" % self.version(),
            target,
            sha256=(
                "f87cee69eec2b4fcbf60a396b030ad6aa3415f192aa5f7ee84cad5e11f7f5ae3"
            ),
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self,
            srcdir,
            env,
            extra_config=("--enable-cross-guesses=conservative",),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env["DESTDIR"] = deploydir
        steps.make(srcdir, env, target="install")
