
import os

from support import buildsystem
from support import steps


class LibtoolPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibtoolPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'libtool'

    def version(self):
        return '2.4.2'

    def patches(self, env, srcdir):
        return ['libtool.m4.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=('--enable-shared',))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, 'install')
