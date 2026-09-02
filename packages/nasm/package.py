from support import buildsystem
from support import steps


class NasmPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = "xz"

    def name(self):
        return "nasm"

    def version(self):
        return "3.02"

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            "https://www.nasm.us/pub/nasm/releasebuilds/%s/"
            "nasm-%s.tar.xz" % (self.version(), self.version()),
            target,
            sha256=(
                "87336eba53b4acfe917424ab5d500d2b"
                "0054d9f5148d35c2273ccf2cfb712f0d"
            ),
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self, srcdir, env, extra_config=("--disable-werror",)
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env["DESTDIR"] = deploydir
        steps.make(srcdir, env, target="install")
