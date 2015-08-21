
import os

from support import buildsystem
from support import steps


class NcursesPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(NcursesPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'ncurses'

    def version(self):
        return '5.7'

    def build_requires(self):
        return ['libtool']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.libtoolize(srcdir, env)

    def configure(self, env, srcdir):
        # TODO(miselin): fix c++ bindings
        steps.run_configure(self, srcdir, env, not_paths=('docdir',),
                            extra_config=('--with-libtool', '--with-shared',
                                          '--without-cxx-binding'))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
