
import os

from support import buildsystem
from support import steps


class ManDbPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(ManDbPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'xz'

    def name(self):
        return 'man-db'

    def version(self):
        return '2.7.5'

    def build_requires(self):
        return ['libpipeline']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://download.savannah.gnu.org/releases/%(package)s/%(package)s-%(version)s.tar.xz' % {
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
