
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
        pass

    def build(self, env, srcdir):
        steps.make(srcdir, env, target='posix', extra_opts=(
            'ARCH_TARGET=%s' % env['CROSS_TARGET'],))

    def deploy(self, env, srcdir, deploydir):
        steps.make(srcdir, env, target='install', extra_opts=(
            'INSTALL_TOP=%s' % deploydir,
            'INSTALL_BIN=%s/applications' % deploydir,
            'INSTALL_LIB=%s/libraries' % deploydir,
            'INSTALL_LMOD=%s/support/lua/share/5.1' % deploydir,
            'INSTALL_CMOD=%s/libraries/lua/5.1' % deploydir,))
