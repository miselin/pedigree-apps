
import os

from support import buildsystem
from support import steps


class MesaPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(MesaPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'mesa'

    def version(self):
        return '9.1.1'

    def build_requires(self):
        return ['libtool']

    def patches(self, env, srcdir):
        return ['configure.ac.diff', 'configure.diff', 'querymatrix.c.diff',
            'ranlib.diff', 'shared.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'ftp://ftp.freedesktop.org/pub/%(package)s/older-versions/9.x/%(version)s/MesaLib-%(version)s.tar.gz' % {
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
