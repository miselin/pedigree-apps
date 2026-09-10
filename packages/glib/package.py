
from support import buildsystem
from support import steps


class GlibPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(GlibPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'xz'

    def name(self):
        return 'glib'

    def version(self):
        return '2.88.3'

    def build_requires(self):
        return ['libffi', 'libpcre2', 'zlib']

    def install_deps(self):
        # GLib installs gdbus-codegen and related Python utilities.
        return self.build_requires() + ['python3']

    def patches(self, env, srcdir):
        return [
            'pedigree-meson-features.diff',
        ]

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://download.gnome.org/sources/glib/2.88/'
            'glib-%s.tar.xz' % self.version(),
            target,
            sha256='ab24d24e698dfa1e408b7bcdb508f4aafc906185a8b8ce72fdf79bbbdc9b383b',
        )

    def configure(self, env, srcdir):
        steps.meson_configure(
            self,
            srcdir,
            env,
            extra_config=(
                '-Ddefault_library=both',
                '-Dtests=false',
                '-Dinstalled_tests=false',
                '-Dintrospection=disabled',
                '-Ddocumentation=false',
                '-Dman-pages=disabled',
                '-Dnls=disabled',
                '-Dselinux=disabled',
                '-Dlibmount=disabled',
                '-Dxattr=false',
                '-Ddtrace=disabled',
                '-Dsystemtap=disabled',
                '-Dsysprof=disabled',
                '-Dlibelf=disabled',
                '-Dglib_debug=disabled',
                '-Dfile_monitor_backend=none',
            ),
        )

    def build(self, env, srcdir):
        steps.meson_build(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.meson_install(srcdir, env, deploydir)
