
import os

from support import buildsystem
from support import steps


class VimPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(VimPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'bz2'

    def name(self):
        return 'vim'

    def version(self):
        return '7.3'

    def build_requires(self):
        return ['ncurses']

    def patches(self, env, srcdir):
        return ['pedigree.cache.diff', 'vim-7.3-cross.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://ftp.%(package)s.org/pub/%(package)s/unix/%(package)s-%(version)s.tar.bz2' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.autoconf(os.path.join(srcdir, 'src'), env)

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            '--with-tlib=ncurses', '--cache-file=auto/config.cache',
            '--enable-256-color'))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')
