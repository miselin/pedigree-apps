
import os

from support import buildsystem
from support import steps


class GccPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(GccPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'gcc'

    def version(self):
        return '4.8.2'

    def build_requires(self):
        return ['libtool', 'libgmp', 'libmpfr', 'libmpc', 'libffi', 'libiconv',
                'gettext', 'zlib']

    def patches(self, env, srcdir):
        # gengtypes patch from, fixes cross-build where fputc_unlocked is
        # available on build but not host.
        # https://git.yoctoproject.org/cgit.cgi/poky/plain/meta/recipes-devtools/gcc/gcc-4.8/0044-gengtypes.patch
        # TODO(miselin): we should also patch fixheaders
        return ['4.8.2/pedigree-gcc.diff', 'override.m4.diff',
                '0044-gengtypes.patch']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        for subdir in ['', 'libbacktrace', 'libssp', 'libstdc++-v3']:
            steps.libtoolize(os.path.join(srcdir, subdir), env)
            steps.autoreconf(os.path.join(srcdir, subdir), env)

    def configure(self, env, srcdir):
        # Note: --target MUST be specified as well as --host. This is necessary
        # for libgcc and libstdc++-v3, as both of those are built for the
        # target, and when we don't specify an explicit target, the configure
        # implicitly uses the build system cc etc
        steps.run_configure(self, srcdir, env, inplace=False, extra_config=(
            '--disable-sjlj-exceptions', '--enable-shared',
            '--with-system-zlib', '--enable-languages=c,c++',
            '--disable-libstdcxx-pch', '--with-newlib', '--disable-multilib',
            '--target=%s' % env['CROSS_TARGET']))

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install', inplace=False)
