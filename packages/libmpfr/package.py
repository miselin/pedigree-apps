
import os
import subprocess

from support import buildsystem
from support import steps


class LibmpfrPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibmpfrPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'libmpfr'

    def version(self):
        return '3.1.4'

    def build_requires(self):
        return ['libtool', 'libgmp']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://www.mpfr.org/%(urlpackage)s-current/%(urlpackage)s-%(version)s.tar.xz' % {
            'package': self.name(),
            'version': self.version(),
            'urlpackage': 'mpfr',
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.libtoolize(srcdir, env)
        steps.autoconf(srcdir, env, aclocal_flags=(
                           '-I', os.path.join(srcdir, 'libltdl'),
                           '-I', os.path.join('libltdl', 'm4')))

    def configure(self, env, srcdir):
        build_cc_machine = subprocess.check_output(
            ['/usr/bin/gcc', '-dumpmachine'])
        steps.run_configure(self, srcdir, env, inplace=False, extra_config=(
                                '--build=%s' % build_cc_machine,))

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install', inplace=False)
