
from support import buildsystem
from support import steps


class m4Package(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(m4Package, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'xz'

    def name(self):
        return 'm4'

    def version(self):
        return '1.4.21'

    def build_requires(self):
        return ['gettext', 'libiconv']

    def patches(self, env, srcdir):
        return ['pselect-null.diff', 'pedigree-musl-locale.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'https://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.xz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(
            url, target,
            sha256='f25c6ab51548a73a75558742fb031e0625d6485fe5f9155949d6486a2408ab66')

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            '--enable-cross-guesses=conservative',))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
