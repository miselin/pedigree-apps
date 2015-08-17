
import os

from support import buildsystem
from support import steps


class BinutilsPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(BinutilsPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'binutils'

    def version(self):
        return '2.24'

    def build_requires(self):
        return ['libtool']

    def patches(self, env, srcdir):
        return ['2.24/pedigree-binutils.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        pass

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env)

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
