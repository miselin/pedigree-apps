
import os
import subprocess

from support import buildsystem
from support import steps


class Libpcre2Package(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(Libpcre2Package, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'libpcre2'

    def version(self):
        return '10.22'

    def build_requires(self):
        return ['libtool']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'ftp://ftp.csx.cam.ac.uk/pub/software/programming/%(urlpackage)s/%(urlpackage)s2-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
            'urlpackage': 'pcre',
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.autoreconf(srcdir, env)

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, inplace=False)

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install', inplace=False)


class LibpcrePackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibpcrePackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'libpcre'

    def version(self):
        return '8.38'

    def build_requires(self):
        return ['libtool']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'ftp://ftp.csx.cam.ac.uk/pub/software/programming/%(urlpackage)s/%(urlpackage)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
            'urlpackage': 'pcre',
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.autoreconf(srcdir, env)

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, inplace=False)

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install', inplace=False)
