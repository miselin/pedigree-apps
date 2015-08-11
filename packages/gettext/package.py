
import os

from support import buildsystem
from support import steps


class ZlibPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(ZlibPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'gettext'

    def version(self):
        return '0.18.1'

    def build_requires(self):
        return ['libtool', 'libiconv']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.autoreconf(srcdir, env)

    def configure(self, env, srcdir):
        env['CPPFLAGS'] = env['CROSS_CPPFLAGS']
        steps.run_configure(self, srcdir, env)

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, 'install')

    def links(self, env, deploydir, cross_dir):
        print os.listdir(deploydir + '/libraries')
        print os.listdir(deploydir + '/include')
        raise Exception('foo')
        libs = ['libz.a', 'libz.so', 'libz.so.1', 'libz.so.1.2.8']
        headers = ['zconf.h', 'zlib.h']
        steps.symlinks(deploydir, cross_dir, libs=libs, headers=headers)


def get_package_cls():
    return ZlibPackage
