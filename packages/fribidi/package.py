from support import buildsystem
from support import steps


class FribidiPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(FribidiPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'xz'

    def name(self):
        return 'fribidi'

    def version(self):
        return '1.0.16'

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
            'https://github.com/fribidi/fribidi/releases/download/v%s/'
            'fribidi-%s.tar.xz' % (self.version(), self.version()),
            target,
            sha256='1b1cde5b235d40479e91be2f0e88a309e3214c8ab470ec8a2744d82a5a9ea05c',
        )

    def configure(self, env, srcdir):
        steps.meson_configure(
            self,
            srcdir,
            env,
            extra_config=(
                '-Ddefault_library=both',
                '-Ddeprecated=true',
                '-Ddocs=false',
                '-Dbin=true',
                '-Dtests=false',
            ),
        )

    def build(self, env, srcdir):
        steps.meson_build(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.meson_install(srcdir, env, deploydir)
