
import os

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
        return '1.5.4'

    def build_requires(self):
        return ['libtool', 'zlib']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://download.sourceforge.net/%(package)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.libtoolize(srcdir, env)
        steps.autoreconf(srcdir, env)

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env)

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
