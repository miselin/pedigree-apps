
from support import buildsystem
from support import steps


MAKE_OPTIONS = ("HELP2MAN=true",)


class InetutilsPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(InetutilsPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'inetutils'

    def version(self):
        return '2.8'

    def build_requires(self):
        return ['readline']

    def install_deps(self):
        return ['readline']

    def patches(self, env, srcdir):
        return ['pselect-null.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'https://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(
            url, target,
            sha256='57b3cf4f77555992881e5ba2a09a63b05aa2c56342a60ed4305b5f45938390b5')

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            '--disable-rpath',
            '--disable-ifconfig', '--disable-logger', '--disable-rlogin',
            '--disable-rsh', '--disable-rexec', '--disable-rcp',
            '--disable-rexecd', '--disable-rlogind', '--disable-rshd',
            '--disable-syslogd', '--disable-uucpd', '--disable-ftpd',
            '--disable-talkd', '--enable-cross-guesses=conservative'))

    def build(self, env, srcdir):
        steps.make(srcdir, env, extra_opts=MAKE_OPTIONS)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(
            srcdir,
            env,
            target='install',
            extra_opts=MAKE_OPTIONS,
        )
