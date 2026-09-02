
from support import buildsystem
from support import steps


class WgetPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(WgetPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'wget'

    def version(self):
        return '1.25.0'

    def build_requires(self):
        return ['ca-certificates', 'openssl', 'zlib']

    def install_deps(self):
        return self.build_requires()

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
            sha256='766e48423e79359ea31e41db9e5c289675947a7fcf2efdcedb726ac9d0da3784')

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            '--with-ssl=openssl', '--with-openssl',
            '--without-libpsl', '--disable-pcre2', '--disable-pcre',
            '--disable-iri', '--disable-xattr',
            '--enable-cross-guesses=conservative'))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
