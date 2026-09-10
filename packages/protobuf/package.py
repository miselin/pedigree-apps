from support import buildsystem
from support import steps


class ProtobufPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(ProtobufPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'gz'

    def name(self):
        return 'protobuf'

    def version(self):
        return '35.0'

    def build_requires(self):
        return ['abseil-cpp']

    def install_deps(self):
        return ['abseil-cpp']

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://github.com/protocolbuffers/protobuf/releases/download/'
            'v%s/protobuf-%s.tar.gz' % (self.version(), self.version()),
            target,
            sha256='8f907baca4b34a3b4854103ba5811e418fb6e2ff11fe0d8df9e8280b11d79926',
        )

    def configure(self, env, srcdir):
        steps.cmake_configure(
            self,
            srcdir,
            env,
            extra_config=(
                '-DBUILD_SHARED_LIBS=ON',
                '-DCMAKE_CXX_STANDARD=17',
                '-Dprotobuf_BUILD_EXAMPLES=OFF',
                '-Dprotobuf_BUILD_LIBPROTOC=ON',
                '-Dprotobuf_BUILD_LIBUPB=ON',
                '-Dprotobuf_BUILD_SHARED_LIBS=ON',
                '-Dprotobuf_BUILD_TESTS=OFF',
                '-Dprotobuf_LOCAL_DEPENDENCIES_ONLY=ON',
                '-Dprotobuf_WITH_ZLIB=OFF',
            ),
        )

    def build(self, env, srcdir):
        steps.cmake_build(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.cmake_install(srcdir, env, deploydir)
