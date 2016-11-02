
import os
import stat

from support import buildsystem
from support import steps


class GettextPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(GettextPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'gettext'

    def version(self):
        return '0.18.1'

    def build_requires(self):
        return ['libtool']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.libtoolize(srcdir, env)
        steps.autoreconf(srcdir, env)

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            'gl_cv_have_weak=no', '--disable-threads', '--without-git',
            '--disable-libasprintf'))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, 'install')

    def postdeploy(self, env, srcdir, deploydir):
        # fix libintl.so permissions
        # TODO: figure out why this installs with 0644 permissions, or whether
        # pedigree's permission checking is wrong to want executable bits here
        path = os.path.join(deploydir, 'libraries', 'libintl.so')

        st = os.stat(path)
        mode = st.st_mode | (stat.S_IXOTH | stat.S_IXGRP | stat.S_IXUSR)
        os.chmod(path, mode)

    def links(self, env, deploydir, cross_dir):
        libs = ['libgettextlib.so', 'libgettextpo.a', 'libasprintf.so',
            'libintl.a', 'gettext', 'libgettextsrc.so', 'libintl.so',
            'libgettextpo.so', 'libasprintf.a']
        headers = ['autosprintf.h', 'gettext-po.h', 'libintl.h']
        steps.symlinks(deploydir, cross_dir, libs=libs, headers=headers)
