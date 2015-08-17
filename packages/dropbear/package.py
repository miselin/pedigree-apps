
import os

from support import buildsystem
from support import steps


class DropbearPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(DropbearPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'bz2'

    def name(self):
        return 'dropbear'

    def version(self):
        return '2013.58'

    def build_requires(self):
        return ['gettext', 'openssl']

    def patches(self, env, srcdir):
        return ['pedigree-fix-bindir.diff', 'pedigree-fixes.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'https://matt.ucc.asn.au/%(package)s/releases/%(package)s-%(version)s.tar.bz2' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        pass

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env)

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
