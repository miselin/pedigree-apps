
import os

from support import buildsystem
from support import steps


class ZlibPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(ZlibPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'zlib'

    def version(self):
        return '1.2.8'

    def build_requires(self):
        return [] # ['libtool']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://zlib.net/%s-%s.tar.gz' % (self.name(), self.version())
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        """Performs steps needed to prepare the build."""
        steps.libtoolize(srcdir, env)

    def configure(self, env, srcdir):
        """Performs steps needed to configure the build system."""
        env['CC'] = env['CROSS_CC']
        env['LD'] = env['CROSS_LD']
        env['LDSHARED'] = '%s -shared -Wl,-soname,libz.so.1,--version-script,zlib.map' % env['CROSS_LD']
        steps.autoconf(self, srcdir, env, host=False,
            paths=('prefix', 'libdir', 'includedir'))

    def build(self, env, srcdir):
        """Performs steps needed to actually build."""
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, 'install')

    def links(self, env, deploydir, cross_dir):
        libs = ['libz.a', 'libz.so', 'libz.so.1', 'libz.so.1.2.8']
        headers = ['zconf.h', 'zlib.h']

        symlinks = []

        for lib in libs:
            lib_source = os.path.join(deploydir, 'libraries', lib)
            lib_target = os.path.join(cross_dir, 'lib', lib)
            symlinks.append((lib_source, lib_target))

        for include in headers:
            include_source = os.path.join(deploydir, 'include', include)
            include_target = os.path.join(cross_dir, 'include', include)
            symlinks.append((include_source, include_target))

        for source, target in symlinks:
            print source, '->', target
            if os.path.exists(target):
                os.unlink(target)
            os.symlink(source, target)


def get_package():
    return ZlibPackage()
