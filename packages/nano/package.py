
from support import buildsystem
from support import steps


class NanoPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(NanoPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'xz'

    def name(self):
        return 'nano'

    def version(self):
        return '9.2'

    def build_requires(self):
        return ['gettext', 'libiconv', 'ncurses']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://www.nano-editor.org/dist/latest/nano-%s.tar.xz'
            % self.version(), target,
            sha256='05ecb99247b782e8a5b3a25ed4101dd034b0236902f7449bc9795b717642f7e9')

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            '--enable-utf8', '--enable-cross-guesses=conservative'))

    def install_deps(self):
        return ['ncurses']

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
