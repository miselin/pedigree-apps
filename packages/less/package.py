
from support import buildsystem
from support import steps


class LessPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LessPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'less'

    def version(self):
        return '704'

    def build_requires(self):
        return ['gettext', 'ncurses']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://www.greenwoodsoftware.com/less/less-%s.tar.gz'
            % self.version(), target,
            sha256='20a0b0a2bb2525fa53c7eee9beb854b4c9cf172eabb209af7020743547bfe9fb')

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            '--with-regex=posix',))

    def install_deps(self):
        return ['ncurses']

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.make(srcdir, env, target='install', extra_opts=(
            'DESTDIR=%s' % deploydir,))
