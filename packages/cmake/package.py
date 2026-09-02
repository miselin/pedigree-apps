import os
import shutil

from support import buildsystem
from support import steps


class CmakePackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(CmakePackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()

    def name(self):
        return 'cmake'

    def version(self):
        return '4.4.3'

    def build_requires(self):
        return []

    def patches(self, env, srcdir):
        return ['libuv-pedigree.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://github.com/Kitware/CMake/releases/download/v%s/'
            'cmake-%s.tar.gz' % (self.version(), self.version()),
            target,
            sha256='c46400618b4f1f2b43507f24fb22f3ae830c3416cf23b776e16e1d413aa892f0',
        )

    def configure(self, env, srcdir):
        steps.cmake_configure(
            self,
            srcdir,
            env,
            extra_config=(
                '-DBUILD_TESTING=OFF',
                '-DBUILD_CursesDialog=OFF',
                '-DBUILD_QtDialog=OFF',
                '-DCMake_ENABLE_DEBUGGER=OFF',
                '-DCMAKE_USE_OPENSSL=OFF',
                '-DCMAKE_USE_SYSTEM_LIBRARIES=OFF',
                '-DCMAKE_DOC_DIR=share/doc/cmake-4.4',
                '-DCMAKE_INFO_DIR=share/info',
                '-DCMAKE_MAN_DIR=share/man',
            ),
        )

    def build(self, env, srcdir):
        steps.cmake_build(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.cmake_install(srcdir, env, deploydir)

    def postdeploy(self, env, srcdir, deploydir):
        platform_dir = os.path.join(
            deploydir, 'usr', 'share', 'cmake-4.4', 'Modules', 'Platform'
        )
        source_dir = os.path.join(
            env['APPS_BASE'], 'cmake', 'Modules', 'Platform'
        )
        for filename in ('Pedigree-Initialize.cmake', 'Pedigree.cmake'):
            shutil.copyfile(
                os.path.join(source_dir, filename),
                os.path.join(platform_dir, filename),
            )
