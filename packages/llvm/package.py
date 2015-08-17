
import os

from support import buildsystem
from support import steps


class Package(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(Package, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return ''

    def version(self):
        return ''

    def build_requires(self):
        return []

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = '' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        pass

    def configure(self, env, srcdir):
        raise Exception('conversion had no idea how to configure')

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        raise Exception('conversion had no idea how to install')
