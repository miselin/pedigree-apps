
import os

from support import buildsystem
from support import steps


class BindPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(BindPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'bind'

    def version(self):
        return '9.10.2-P3'

    def build_requires(self):
        return ['libtool', 'openssl']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'https://www.isc.org/downloads/file/%(package)s-9-10-2-p3/?version=tar-gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.libtoolize(srcdir, env)

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env)

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
