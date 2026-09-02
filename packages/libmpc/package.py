from support import buildsystem
from support import steps


class LibmpcPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = "xz"

    def name(self):
        return "libmpc"

    def version(self):
        return "1.4.1"

    def build_requires(self):
        return ["libgmp", "libmpfr"]

    def install_deps(self):
        return self.build_requires()

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            "https://ftp.gnu.org/gnu/mpc/mpc-%s.tar.xz" % self.version(),
            target,
            sha256=(
                "91204cd32f164bd3b7c992d4a6a8ce65"
                "19511aadab30f78b6982d0bf8d73e931"
            ),
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self,
            srcdir,
            env,
            inplace=False,
            extra_config=("--enable-shared", "--enable-static"),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env["DESTDIR"] = deploydir
        steps.make(srcdir, env, target="install", inplace=False)
