
import os
import stat

from support import buildsystem
from support import steps


class DialogPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(DialogPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'dialog'

    def version(self):
        return '1.2'

    def build_requires(self):
        return ['libtool', 'ncurses']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://invisible-island.net/datafiles/release/%(package)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        pass

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=('--with-shared',
            '--with-pkg-config', '--with-libtool'), not_paths=('docdir',))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.make(srcdir, env, target='install',
                   extra_opts=('DESTDIR=' + deploydir,))

    def postdeploy(self, env, srcdir, deploydir):
        # fix libdialog.so permissions
        path = os.path.join(deploydir, 'libraries', 'libdialog.so')

        st = os.stat(path)
        mode = st.st_mode | (stat.S_IXOTH | stat.S_IXGRP | stat.S_IXUSR)
        os.chmod(path, mode)
