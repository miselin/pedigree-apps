
from support import buildsystem
from support import steps


class PixmanPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(PixmanPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'xz'

    def name(self):
        return 'pixman'

    def version(self):
        return '0.46.4'

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
            'https://cairographics.org/releases/pixman-%s.tar.xz'
            % self.version(),
            target,
            sha256='a098c33924754ad43f981b740f6d576c70f9ed1006e12221b1845431ebce1239',
        )

    def configure(self, env, srcdir):
        steps.meson_configure(
            self,
            srcdir,
            env,
            extra_config=(
                '-Ddefault_library=both',
                '-Dtls=disabled',
                '-Dgtk=disabled',
                '-Dlibpng=disabled',
                '-Dtests=disabled',
                '-Ddemos=disabled',
                '-Dopenmp=disabled',
            ),
        )

    def build(self, env, srcdir):
        steps.meson_build(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.meson_install(srcdir, env, deploydir)
