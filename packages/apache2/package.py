
import os

from support import buildsystem
from support import steps


class Apache2Package(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(Apache2Package, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'apache2'

    def version(self):
        return '2.2.27'

    def build_requires(self):
        return ['libtool', 'glib']

    def patches(self, env, srcdir):
        return ['2.2.27/2.2.17.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://mirror.overthewire.com.au/pub/apache/%(package)s/%(package)s-%(version)s.tar.gz' % {
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
