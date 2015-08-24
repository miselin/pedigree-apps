
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
                'gettext']

    def patches(self, env, srcdir):
        return ['4.8.2/pedigree-gcc.diff', 'override.m4.diff']

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
            steps.autoreconf(os.path.join(srcdir, subdir), env,
                             extra_flags=('-v',))

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env)

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
