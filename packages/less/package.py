
import os

from support import buildsystem
from support import steps


class LessPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LessPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'less'

    def version(self):
        return '451'

    def build_requires(self):
        return ['gettext', 'ncurses']

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
        pass

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env)

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.make(srcdir, env, target='install', extra_opts=(
            'DESTDIR=%s' % deploydir,))
