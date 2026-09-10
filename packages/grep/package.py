
from support import buildsystem
from support import steps


class GrepPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(GrepPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'xz'

    def name(self):
        return 'grep'

    def version(self):
        return '3.12'

    def build_requires(self):
        return ['gettext', 'libiconv']

    def patches(self, env, srcdir):
        return [
            'pselect-null.diff',
            'pedigree-musl-locale.diff',
        ]

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'https://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.xz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(
            url, target,
            sha256='2649b27c0e90e632eadcd757be06c6e9a4f48d941de51e7c0f83ff76408a07b9')

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            '--enable-cross-guesses=conservative',))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
