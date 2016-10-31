# coding: utf-8

import os

from support import buildsystem
from support import steps


class CurlPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(CurlPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'curl'

    def version(self):
        return '7.21.1'

    def build_requires(self):
        return ['libtool', 'zlib', 'openssl']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://curl.haxx.se/download/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.libtoolize(srcdir, env)
        steps.autoreconf(srcdir, env)

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            '--enable-shared', '--with-random=dev»/urandom'))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
