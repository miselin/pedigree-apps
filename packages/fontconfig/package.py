
import os

from support import buildsystem
from support import steps


class FontconfigPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(FontconfigPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'fontconfig'

    def version(self):
        return '2.11.0'

    def build_requires(self):
        return ['libtool', 'expat', 'libfreetype', 'zlib', 'libpng']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://www.freedesktop.org/software/%(package)s/release/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.libtoolize(srcdir, env)
        steps.autoconf(srcdir, env)

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env)

    def build(self, env, srcdir):
        steps.make(srcdir, env, extra_opts=('V=1',))

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
