
import os
import sys

from support import buildsystem
from support import steps


class NetsurfPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(NetsurfPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'netsurf'

    def version(self):
        return '3.0'

    def source_root(self, srcdir):
        # e,g, /src/src (due to pacakge layout)
        return os.path.join(srcdir, 'src')

    def netsurf_root(self, srcdir):
        # e.g. /src/netsurf-full-3.0/src/netsurf-3.0
        return os.path.join(self.source_root(srcdir), 'netsurf-%s' % self.version())

    def build_requires(self):
        return ['expat', 'curl', 'libpng']

    def patches(self, env, srcdir):
        return ['nsgenbind-newer-bison-versions.patch']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://download.%(package)s-browser.org/%(package)s/releases/source-full/%(package)s-%(version)s-full-src.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        # Allow CFLAGS to come from the environment.
        steps.cmd(['sed', '-i.bak', r's/CFLAGS \:=$/CFLAGS \?=/g', os.path.join(self.netsurf_root(srcdir), 'Makefile.defaults')])

        # Fix paths for Pedigree.
        steps.cmd(['sed', '-i.bak', r's@share/netsurf/@support/netsurf/@g', os.path.join(self.netsurf_root(srcdir), 'framebuffer', 'Makefile.defaults')])

        # Fix a bunch of repeated issues with files in the package.
        for root, dirs, files in os.walk(self.source_root(srcdir)):
            for file in files:
                filename = os.path.join(root, file)

                if file == 'Makefile':
                    # remove -Werror
                    steps.cmd(['sed', '-i.bak', r's/\-Werror$//g', filename])

    def configure(self, env, srcdir):
        pass

    def build_opts(self):
        return ('TARGET=framebuffer', 'HOST=pedigree', 'VQ=', 'Q=',
                'NSFB_LINUX_AVAILABLE=no', 'NETSURF_USE_JPEG=NO',
                'NETSURF_USE_MNG=NO')

    def build(self, env, srcdir):
        env['CC'] = env['CROSS_CC']
        env['CXX'] = env['CROSS_CXX']
        env['AR'] = env['CROSS_AR']
        env['RANLIB'] = env['CROSS_RANLIB']
        steps.make(srcdir, env, extra_opts=self.build_opts(), parallel=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, extra_opts=self.build_opts(), target='install',
                   parallel=False)
