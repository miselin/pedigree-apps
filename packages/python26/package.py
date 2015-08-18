
import os

from support import buildsystem
from support import steps


class Python26Package(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(Python26Package, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'python26'

    def version(self):
        return '2.6.6'

    def build_requires(self):
        return ['libtool', 'gettext', 'libiconv', 'curl', 'openssl', 'glib']

    def patches(self, env, srcdir):
        return ['Makefile.pre.in.diff', 'configure.in.diff', 'setup.py.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://python.org/ftp/python/%(version)s/%(urlpackage)s-%(version)s.tar.bz2' % {
            'package': self.name(),
            'version': self.version(),
            'urlpackage': 'Python',
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.autoreconf(srcdir, env)

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env)

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        raise Exception('conversion had no idea how to install')
