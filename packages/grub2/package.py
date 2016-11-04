
import os

from support import buildsystem
from support import steps


class Grub2Package(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(Grub2Package, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'grub2'

    def version(self):
        return '2.00'

    def build_requires(self):
        return []

    def patches(self, env, srcdir):
        return ['grub2-pedigree.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://ftp.gnu.org/gnu/%(urlpackage)s/%(urlpackage)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
            'urlpackage': 'grub',
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        pass

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env,
                            extra_config=('--disable-werror',))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
