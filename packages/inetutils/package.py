
import os

from support import buildsystem
from support import steps


class InetutilsPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(InetutilsPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'inetutils'

    def version(self):
        return '1.8'

    def build_requires(self):
        return ['libtool', 'readline']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        pass

    def configure(self, env, srcdir):
        env['LIBS'] = '-lbind'
        steps.run_configure(self, srcdir, env, extra_config=(
            '--disable-ifconfig', '--disable-logger', '--disable-rlogin',
            '--disable-rsh', '--disable-rexec', '--disable-rcp',
            '--disable-rexecd', '--disable-rlogind', '--disable-rshd',
            '--disable-syslogd', '--disable-uucpd', '--disable-ftpd',
            '--disable-talkd'))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
