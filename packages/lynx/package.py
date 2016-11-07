
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
        return '2.8.8rel.2'

    def build_requires(self):
        return ['curl', 'openssl', 'ncurses', 'gzip']

    def patches(self, env, srcdir):
        return ['www_tcp.h.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://invisible-mirror.net/archives/lynx/tarballs/%(package)s%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        pass

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, not_paths=('docdir',))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.make(srcdir, env, target='install',
                   extra_opts=('DESTDIR=%s' % deploydir,))
