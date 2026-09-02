
from support import buildsystem
from support import steps


class CairoPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(CairoPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'xz'

    def name(self):
        return 'cairo'

    def version(self):
        return '1.18.4'

    def build_requires(self):
        return ['libpng', 'zlib', 'libfreetype', 'fontconfig', 'pixman', 'glib']

    def install_deps(self):
        return self.build_requires()

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://cairographics.org/releases/cairo-%s.tar.xz'
            % self.version(),
            target,
            sha256='445ed8208a6e4823de1226a74ca319d3600e83f6369f99b14265006599c32ccb',
        )

    def configure(self, env, srcdir):
        steps.meson_configure(
            self,
            srcdir,
            env,
            extra_config=(
                '-Ddefault_library=both',
                '-Dtests=disabled',
                '-Dxcb=disabled',
                '-Dxlib=disabled',
                '-Dxlib-xcb=disabled',
                '-Dquartz=disabled',
                '-Ddwrite=disabled',
                '-Dtee=disabled',
                '-Dpng=enabled',
                '-Dzlib=enabled',
                '-Dfontconfig=enabled',
                '-Dfreetype=enabled',
                '-Dglib=enabled',
                '-Dspectre=disabled',
                '-Dlzo=disabled',
                '-Dsymbol-lookup=disabled',
                '-Dgtk_doc=false',
            ),
        )

    def build(self, env, srcdir):
        steps.meson_build(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.meson_install(srcdir, env, deploydir)
