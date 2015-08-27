
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
        return ['libtool', 'zlib', 'libgmp']

    def patches(self, env, srcdir):
        return ['1.0.1g-docfixes-diff.diff', 'Configure.diff',
                'dso_dlfcn.c.diff']

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
        env['CC'] = env['CROSS_CC']
        steps.cmd(['/bin/sh', os.path.join(srcdir, 'Configure'), 'threads',
                       'shared', 'zlib-dynamic', '--prefix=/',
                       '--openssldir=/support/openssl', 'pedigree-gcc'],
                  cwd=srcdir, env=env)

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.make(srcdir, env, target='install', extra_opts=(
            'INSTALL_PREFIX=%s' % deploydir,))
        renames = (
            ('lib64', 'libraries'),
            ('bin', 'applications'),
        )
        for old, new in renames:
            os.rename(os.path.join(deploydir, old),
                      os.path.join(deploydir, new))
