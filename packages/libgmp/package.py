
import os

from support import buildsystem
from support import steps


class LibgmpPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibgmpPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'libgmp'

    def version(self):
        return '5.1.3'

    def build_requires(self):
        return ['libtool']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://ftp.gnu.org/gnu/%(urlpackage)s/%(urlpackage)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
            'urlpackage': 'gmp',
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

        # gmp installs some headers into the arch-specific $PREFIX/include
        # directory - so let's pull those out now.
        deploy_include = os.path.join(deploydir, 'include')
        if not os.path.isdir(deploy_include):
            os.makedirs(deploy_include)

        steps.cmd(['/bin/mv',
                   os.path.join(deploydir, 'support/libgmp/include', 'gmp.h'),
                   os.path.join(deploy_include, 'gmp.h')])
