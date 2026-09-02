
from support import buildsystem
from support import steps


class LibfreetypePackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibfreetypePackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'xz'

    def name(self):
        return 'libfreetype'

    def version(self):
        return '2.14.3'

    def build_requires(self):
        return ['zlib', 'libpng']

    def install_deps(self):
        return self.build_requires()

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://download.savannah.gnu.org/releases/freetype/'
            'freetype-%s.tar.xz' % self.version(),
            target,
            sha256='36bc4f1cc413335368ee656c42afca65c5a3987e8768cc28cf11ba775e785a5f',
        )

    def configure(self, env, srcdir):
        steps.meson_configure(
            self,
            srcdir,
            env,
            extra_config=(
                '-Ddefault_library=both',
                '-Dzlib=system',
                '-Dpng=enabled',
                '-Dbzip2=disabled',
                '-Dbrotli=disabled',
                '-Dharfbuzz=disabled',
                '-Dtests=disabled',
            ),
        )

    def build(self, env, srcdir):
        steps.meson_build(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.meson_install(srcdir, env, deploydir)
