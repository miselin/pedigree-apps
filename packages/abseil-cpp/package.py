from support import buildsystem
from support import steps


class AbseilCppPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(AbseilCppPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'gz'

    def name(self):
        return 'abseil-cpp'

    def version(self):
        return '20250512.1'

    def build_requires(self):
        return []

    def install_deps(self):
        return []

    def patches(self, env, srcdir):
        return ['pedigree-platform.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://github.com/abseil/abseil-cpp/releases/download/'
            '%s/abseil-cpp-%s.tar.gz' % (self.version(), self.version()),
            target,
            sha256='9b7a064305e9fd94d124ffa6cc358592eb42b5da588fb4e07d09254aa40086db',
        )

    def configure(self, env, srcdir):
        steps.cmake_configure(
            self,
            srcdir,
            env,
            extra_config=(
                '-DABSL_BUILD_TESTING=OFF',
                '-DABSL_BUILD_TEST_HELPERS=OFF',
                '-DABSL_ENABLE_INSTALL=ON',
                '-DABSL_PROPAGATE_CXX_STD=ON',
                '-DBUILD_SHARED_LIBS=ON',
                '-DCMAKE_CXX_STANDARD=17',
                '-DCMAKE_POSITION_INDEPENDENT_CODE=ON',
            ),
        )

    def build(self, env, srcdir):
        steps.cmake_build(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.cmake_install(srcdir, env, deploydir)
