
import os
import shutil

from support import buildsystem
from support import steps


class LibiconvPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibiconvPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'libiconv'

    def version(self):
        return '1.13.1'

    def build_requires(self):
        return ['libtool']

    def patches(self, env, srcdir):
        # TODO(miselin): fix this so this isn't needed.
        return ['libtool.m4.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        # Configure all libiconv projects.
        autotools_flags = ['-I', os.path.join(srcdir, 'm4'),
            '-I', os.path.join(srcdir, 'srcm4')]
        steps.autoconf(srcdir, env, aclocal_flags=autotools_flags)
        steps.autoconf(os.path.join(srcdir, 'preload'), env,
            aclocal_flags=autotools_flags)

        shutil.copy2(os.path.join(srcdir, 'm4', 'libtool.m4'),
            os.path.join(srcdir, 'libcharset', 'm4', 'libtool.m4'))
        steps.autoconf(os.path.join(srcdir, 'libcharset'), env,
            aclocal_flags=autotools_flags)

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=('--enable-shared',),
            inplace=False)

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, 'install', inplace=False)

    def links(self, env, deploydir, cross_dir):
        libs = ['libcharset.a', 'libiconv.la', 'libiconv.a', 'libcharset.la',
            'libcharset.so', 'libiconv.so']
        headers = ['libcharset.h', 'localcharset.h', 'iconv.h']

        steps.symlinks(deploydir, cross_dir, libs=libs, headers=headers)


def get_package_cls():
    return LibiconvPackage
