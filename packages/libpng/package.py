
from support import buildsystem
from support import steps


class LibpngPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibpngPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'libpng'

    def version(self):
        return '1.6.58'

    def build_requires(self):
        return ['zlib']

    def install_deps(self):
        return ['zlib']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://download.sourceforge.net/libpng/libpng-%s.tar.xz'
            % self.version(),
            target,
            sha256='28eb403f51f0f7405249132cecfe82ea5c0ef97f1b32c5a65828814ae0d34775',
        )

    def configure(self, env, srcdir):
        steps.cmake_configure(
            self,
            srcdir,
            env,
            extra_config=(
                '-DPNG_SHARED=ON',
                '-DPNG_STATIC=ON',
                '-DPNG_TESTS=OFF',
                '-DPNG_TOOLS=ON',
            ),
        )

    def build(self, env, srcdir):
        steps.cmake_build(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.cmake_install(srcdir, env, deploydir)
