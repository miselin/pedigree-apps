
import os

from support import buildsystem
from support import steps


class LuaPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LuaPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'lua'

    def version(self):
        return '5.1.4'

    def build_requires(self):
        return ['libtool']

    def patches(self, env, srcdir):
        return ['Makefile_root.diff', 'Makefile_src.diff', 'luaconf.h.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://www.%(package)s.org/ftp/%(package)s-%(version)s.tar.gz' % {
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
