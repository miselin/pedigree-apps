
import os

from support import buildsystem
from support import steps


class LynxPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LynxPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'lynx'

    def version(self):
        return '2.8.7rel.2'

    def build_requires(self):
        return ['curl', 'openssl', 'ncurses', 'gzip']

    def patches(self, env, srcdir):
        return ['www_tcp.h.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://%(package)s.isc.org/current/%(package)s%(version)s.tar.gz' % {
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