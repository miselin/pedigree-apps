
from support import buildsystem
from support import steps


DISABLED_REASON = (
    "man-db 2.13.1 needs an nroff formatter for ordinary source manual pages. "
    "The catalog does not yet provide groff or mandoc, so packaging man-db "
    "would install a command that cannot perform its primary runtime job."
)


class ManDbPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(ManDbPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'xz'

    def name(self):
        return 'man-db'

    def version(self):
        return '2.13.1'

    def build_requires(self):
        return ['libpipeline', 'gdbm']

    def install_deps(self):
        return ['gdbm', 'gzip', 'less', 'libpipeline']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'https://download.savannah.nongnu.org/releases/%(package)s/%(package)s-%(version)s.tar.xz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(
            url, target,
            sha256='8afebb6f7eb6bb8542929458841f5c7e6f240e30c86358c1fbcefbea076c87d9')

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            '--with-db=gdbm', '--without-libseccomp',
            '--disable-shared', '--enable-static', '--disable-setuid',
            '--with-pager=/usr/bin/less',
            '--with-nroff=/usr/bin/nroff', '--with-gzip=/usr/bin/gzip',
            '--enable-cross-guesses=conservative'))

    def build(self, env, srcdir):
        steps.make(srcdir, env, parallel=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
