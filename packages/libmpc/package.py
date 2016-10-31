
import os

from support import buildsystem
from support import steps


class LibmpcPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibmpcPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'libmpc'

    def version(self):
        return '0.8.2'

    def build_requires(self):
        return ['libtool', 'libgmp', 'libmpfr']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://www.multiprecision.org/%(urlpackage)s/download/%(urlpackage)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
            'urlpackage': 'mpc',
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        # need an older autoconf/automake for libmpc
        env['AUTORECONF'] = 'autoreconf2.64'
        env['AUTOCONF'] = 'autoconf2.64'
        env['AUTOMAKE'] = 'automake-1.11'
        env['ACLOCAL'] = 'aclocal-1.11'

        steps.libtoolize(srcdir, env)
        steps.autoreconf(srcdir, env)

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env)

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
