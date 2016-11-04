
import os
import stat

from support import buildsystem
from support import steps


class ReadlinePackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(ReadlinePackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'readline'

    def version(self):
        return '6.3'

    def build_requires(self):
        return ['libtool']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        with open(os.path.join(srcdir, 'support', 'shobj-conf'), 'w') as f:
            f.write('''#!/bin/sh

echo SHOBJ_STATUS="supported"
echo SHLIB_STATUS="supported"

echo SHOBJ_CC="%(CROSS_TARGET)s-gcc"
echo SHOBJ_CFLAGS=\\"-fPIC -shared\\"
echo SHOBJ_LD="%(CROSS_TARGET)s-gcc"
echo SHOBJ_LDFLAGS="-shared"
echo SHOBJ_XLDFLAGS=""
echo SHOBJ_LIBS=""

echo SHLIB_DOT="."
echo SHLIB_LIBPREF="lib"
echo SHLIB_LIBSUFF="so"

echo SHLIB_LIBVERSION="so"
echo SHLIB_DLLVERSION=""
''' % env)

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
                            'bash_cv_wcwidth_broken=yes',))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.make(srcdir, env, target='install', extra_opts=(
            'DESTDIR=%s' % deploydir,))

    def postdeploy(self, env, srcdir, deploydir):
        # fix libreadline.so permissions
        for lib in ('libreadline.so', 'libhistory.so'):
            path = os.path.join(deploydir, 'libraries', lib)

            st = os.stat(path)
            mode = st.st_mode | (stat.S_IXOTH | stat.S_IXGRP | stat.S_IXUSR)
            os.chmod(path, mode)
