from support import buildsystem
from support import steps


class VttestPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()

    def name(self):
        return "vttest"

    def version(self):
        return "20251205"

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            "https://invisible-island.net/archives/vttest/"
            "vttest-%s.tgz" % self.version(),
            target,
            sha256=(
                "cd6886f9aefe6a3f6c566fa61271a557"
                "10901a71849c630bf5376aa984bf77cc"
            ),
        )

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, not_paths=("docdir",))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env["DESTDIR"] = deploydir
        steps.make(srcdir, env, target="install")
