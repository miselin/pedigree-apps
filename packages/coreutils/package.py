
import os

from support import buildsystem
from support import steps


class CoreutilsPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(CoreutilsPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'xz'

    def name(self):
        return 'coreutils'

    def version(self):
        return '8.25'

    def build_requires(self):
        return ['gettext', 'libgmp']

    def patches(self, env, srcdir):
        return ['0001-Fix-cross-compile-using-help2man-and-running-target-.patch']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.xz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        pass

    def configure(self, env, srcdir):
        # don't accidentally detect inotify when it doesn't really exist on
        # Pedigree...
        steps.run_configure(self, srcdir, env, extra_config=(
            'ac_cv_func_inotify_init=no',))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
