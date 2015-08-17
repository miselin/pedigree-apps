
import os

from support import buildsystem
from support import steps


class DosboxPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(DosboxPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'dosbox'

    def version(self):
        return '0.74'

    def build_requires(self):
        return []

    def patches(self, env, srcdir):
        return ['configure.diff', 'status.h.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://sourceforge.net/projects/%(package)s/files/%(package)s/%(version)s/%(package)s-%(version)s.tar.gz/download' % {
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
