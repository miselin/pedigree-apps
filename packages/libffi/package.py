
import os

from support import buildsystem
from support import steps


class LibffiPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibffiPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'libffi'

    def version(self):
        return '3.1'

    def build_requires(self):
        return ['libtool']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'ftp://sourceware.org/pub/%(package)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.libtoolize(srcdir, env)
        steps.autoconf(srcdir, env)

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, inplace=False)

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install', inplace=False)
