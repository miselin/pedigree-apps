
from support import buildsystem
from support import steps


class AtkPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(AtkPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'xz'

    def name(self):
        return 'atk'

    def version(self):
        # ATK 2.38 is the final standalone release before its APIs moved to GTK.
        return '2.38.0'

    def build_requires(self):
        return ['glib']

    def install_deps(self):
        return self.build_requires()

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://download.gnome.org/sources/atk/2.38/'
            'atk-%s.tar.xz' % self.version(),
            target,
            sha256='ac4de2a4ef4bd5665052952fe169657e65e895c5057dffb3c2a810f6191a0c36',
        )

    def configure(self, env, srcdir):
        steps.meson_configure(
            self,
            srcdir,
            env,
            extra_config=(
                '-Ddefault_library=both',
                '-Ddocs=false',
                '-Dintrospection=false',
            ),
        )

    def build(self, env, srcdir):
        steps.meson_build(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.meson_install(srcdir, env, deploydir)
