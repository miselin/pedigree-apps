
import os

from support import buildsystem
from support import steps


class ExpatPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(ExpatPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'expat'

    def version(self):
        return '2.0.1'

    def build_requires(self):
        return ['libtool']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://sourceforge.net/projects/%(package)s/files/%(package)s/%(version)s/%(package)s-%(version)s.tar.gz/download' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.libtoolize(os.path.join(srcdir, 'conftools'), env)
        steps.autoconf(srcdir, env, aclocal_flags=(
                           '-I', os.path.join(srcdir, 'conftools', 'libltdl'),
                           '-I', os.path.join(srcdir, 'conftools', 'libltdl',
                                              'm4')))

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, not_paths=('docdir',))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.make(srcdir, env, target='install', extra_opts=(
            'DESTDIR=%s' % deploydir,))
