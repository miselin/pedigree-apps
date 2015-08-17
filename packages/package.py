
import os

from support import buildsystem
from support import steps


class TemplatePackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(TemplatePackage, self).__init__(*args, **kwargs)
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
            'package': package.name(),
            'version': package.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        pass

    def configure(self, env, srcdir):
        raise Exception('conversion had no idea how to configure')

    def build(self, env, srcdir):
        raise Exception('conversion had no idea how to build')

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        raise Exception('conversion had no idea how to install')
