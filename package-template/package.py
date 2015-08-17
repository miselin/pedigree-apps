
import os

from support import buildsystem
from support import steps


class TemplatePackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(TemplatePackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = '$TARBALL_FORMAT'

    def name(self):
        return '$PACKAGE_NAME'

    def version(self):
        return '$PACKAGE_VERSION'

    def build_requires(self):
        return []

    def patches(self, env, srcdir):
        return $PACKAGE_PATCHES

    def options(self):
        return self._options

    def download(self, env, target):
        url = '$PACKAGE_URL' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):$PREBUILD

    def configure(self, env, srcdir):$CONFIGURE

    def build(self, env, srcdir):$BUILD

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir$INSTALL
