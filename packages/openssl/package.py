
import os

from support import buildsystem
from support import steps


class OpensslPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(OpensslPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'openssl'

    def version(self):
        return '1.0.1g'

    def build_requires(self):
        return ['libtool']

    def patches(self, env, srcdir):
        return ['1.0.1g-docfixes-diff.diff', 'Configure.diff', 'b_sock.c.diff',
            'dso_dlfcn.c.diff', 'e_os.h.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://www.%(package)s.org/source/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        pass

    def configure(self, env, srcdir):
        steps.cmd([os.path.join(srcdir, 'Configure'), 'threads', 'shared',
                  'zlib-dynamic', '--prefix=/', '--openssldir=/support/openssl',
                  'pedigree-gcc'], cwd=srcdir, env=env)

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
