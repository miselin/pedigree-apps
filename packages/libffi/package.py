
import os

from support import buildsystem
from support import steps


class TemplatePackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(TemplatePackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'libffi'

    def version(self):
        return '3.1'

    def patches(self, env, srcdir):
        return []

    def build_requires(self):
        return ['libtool']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'ftp://sourceware.org/pub/%(package)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.autoreconf(srcdir, env)

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, inplace=False)

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, 'install', inplace=False)

    def links(self, env, deploydir, cross_dir):
        libs = ['libffi-3.1', 'libffi.a', 'libffi.so']
        steps.symlinks(deploydir, cross_dir, libs=libs)
