from support import buildsystem
from support import steps


UPSTREAM_VERSION = "2.0.7"

DISABLED_REASON = "No active port currently depends on GNU Pth 2.0.7."


class PthPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()

    def name(self):
        return "pth"

    def version(self):
        return UPSTREAM_VERSION

    def patches(self, env, srcdir):
        return ["pedigree-elf.diff"]

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            "https://ftp.gnu.org/gnu/pth/pth-%s.tar.gz" % self.version(),
            target,
            sha256=(
                "72353660c5a2caafd601b20e12e75d86"
                "5fd88f6cf1a088b306a3963f0bc77232"
            ),
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self,
            srcdir,
            env,
            not_paths=("datarootdir", "docdir"),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, parallel=False)

    def deploy(self, env, srcdir, deploydir):
        steps.make(
            srcdir,
            env,
            target="install",
            extra_opts=("DESTDIR=%s" % deploydir,),
            parallel=False,
        )
