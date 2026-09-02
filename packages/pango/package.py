
from support import buildsystem
from support import steps


class PangoPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(PangoPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'xz'

    def name(self):
        return 'pango'

    def version(self):
        return '1.58.2'

    def build_requires(self):
        return [
            'glib',
            'harfbuzz',
            'libfreetype',
            'cairo',
            'fontconfig',
            'fribidi',
        ]

    def install_deps(self):
        return self.build_requires()

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://download.gnome.org/sources/pango/1.58/'
            'pango-%s.tar.xz' % self.version(),
            target,
            sha256='342385b6ca3b7c73455d7c80a13b7dbe4489e00bc3bd4c5bd6ed4dce421e374a',
        )

    def configure(self, env, srcdir):
        steps.meson_configure(
            self,
            srcdir,
            env,
            extra_config=(
                '-Ddefault_library=both',
                '-Ddocumentation=false',
                '-Dman-pages=false',
                '-Dintrospection=disabled',
                '-Dbuild-testsuite=false',
                '-Dbuild-examples=false',
                '-Dfontconfig=enabled',
                '-Dlibthai=disabled',
                '-Dcairo=enabled',
                '-Dxft=disabled',
                '-Dfreetype=enabled',
                '-Dsysprof=disabled',
            ),
        )

    def build(self, env, srcdir):
        steps.meson_build(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.meson_install(srcdir, env, deploydir)
