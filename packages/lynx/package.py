from support import buildsystem
from support import steps


class LynxPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()

    def name(self):
        return "lynx"

    def version(self):
        return "2.9.3"

    def build_requires(self):
        return ["ca-certificates", "ncurses", "openssl", "zlib"]

    def install_deps(self):
        return self.build_requires()

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            "https://invisible-mirror.net/archives/lynx/tarballs/"
            "lynx%s.tar.gz" % self.version(),
            target,
            sha256=(
                "6e99e46980974a6d89eceefbb26ca8c7"
                "aa7702b78ecb5bad383b859af225d052"
            ),
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self,
            srcdir,
            env,
            not_paths=("docdir",),
            extra_config=(
                "--disable-dired-dearchive",
                "--disable-dired-gzip",
                "--disable-dired-tar",
                "--disable-dired-uudecode",
                "--disable-dired-zip",
                "--disable-nls",
                "--enable-ipv6",
                "--with-screen=ncursesw",
                "--with-ssl",
                "--with-zlib",
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, parallel=False)

    def deploy(self, env, srcdir, deploydir):
        steps.make(
            srcdir,
            env,
            target="install",
            parallel=False,
            extra_opts=("DESTDIR=%s" % deploydir,),
        )
