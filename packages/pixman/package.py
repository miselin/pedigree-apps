
import os

from support import buildsystem
from support import steps


class PixmanPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(PixmanPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'pixman'

    def version(self):
        return '0.28.2'

    def build_requires(self):
        return ['libtool']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://cairographics.org/releases/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.libtoolize(srcdir, env)
        steps.autoconf(srcdir, env,
                       aclocal_flags=('-I', os.path.join(srcdir, 'libltdl'),
                                      '-I', os.path.join('libltdl', 'm4')),
                       only_aclocal=True)

    def configure(self, env, srcdir):
        # TODO(miselin): fix TLS in pixman (it causes a linker error).
        env['CPPFLAGS'] = '-DPIXMAN_NO_TLS'
        steps.run_configure(self, srcdir, env, extra_config=('--disable-gtk',))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
