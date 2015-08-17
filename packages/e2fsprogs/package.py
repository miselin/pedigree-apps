
import os

from support import buildsystem
from support import steps


class e2fsprogsPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(e2fsprogsPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'e2fsprogs'

    def version(self):
        return '1.41.12'

    def build_requires(self):
        return ['libtool', 'gettext']

    def patches(self, env, srcdir):
        return ['ismounted.c.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://prdownloads.sourceforge.net/%(package)s/%(package)s-%(version)s.tar.gz' % {
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
