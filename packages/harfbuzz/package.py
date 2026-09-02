
from support import buildsystem
from support import steps


class HarfbuzzPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(HarfbuzzPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'xz'

    def name(self):
        return 'harfbuzz'

    def version(self):
        return '14.4.0'

    def build_requires(self):
        return ['glib', 'libfreetype', 'cairo', 'libpng', 'zlib']

    def install_deps(self):
        return self.build_requires()

    def patches(self, env, srcdir):
        return ['pedigree-cmake-icu-target.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://github.com/harfbuzz/harfbuzz/releases/download/'
            '%s/harfbuzz-%s.tar.xz' % (self.version(), self.version()),
            target,
            sha256='2357ed966c6ced7bfa720b0640c0231065af01158fbea215093ffa15aed44371',
        )

    def configure(self, env, srcdir):
        steps.meson_configure(
            self,
            srcdir,
            env,
            extra_config=(
                '-Ddefault_library=both',
                '-Dglib=enabled',
                '-Dgobject=enabled',
                '-Dcairo=enabled',
                '-Dpng=enabled',
                '-Dzlib=enabled',
                '-Dfreetype=enabled',
                '-Dchafa=disabled',
                '-Dicu=disabled',
                '-Dgraphite=disabled',
                '-Dgraphite2=disabled',
                '-Dfontations=disabled',
                '-Dharfrust=disabled',
                '-Dkbts=disabled',
                '-Dwasm=disabled',
                '-Draster=disabled',
                '-Dvector=disabled',
                '-Dgpu=disabled',
                '-Dgpu_demo=disabled',
                '-Dtests=disabled',
                '-Dintrospection=disabled',
                '-Ddocs=disabled',
                '-Dutilities=enabled',
                '-Dbenchmark=disabled',
            ),
        )

    def build(self, env, srcdir):
        steps.meson_build(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.meson_install(srcdir, env, deploydir)
