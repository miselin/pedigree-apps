import os
import subprocess

from support import buildsystem
from support import steps


class ReadlinePackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(ReadlinePackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()

    def name(self):
        return 'readline'

    def version(self):
        return '8.3.3'

    def build_requires(self):
        return ['ncurses']

    def install_deps(self):
        return ['ncurses']

    def patches(self, env, srcdir):
        return [
            'readline83-001', 'readline83-002', 'readline83-003',
            'pedigree-shared.diff',
        ]

    def patch(self, env, srcdir):
        # Upstream's maintenance patches intentionally use patch -p0.
        for patch_filename in self.patches(env, srcdir):
            patch_path = os.path.join(self._path, 'patches', patch_filename)
            with open(patch_path, 'rb') as patch_file:
                subprocess.check_call(
                    [env['PATCH'], '--batch', '--fuzz=0', '-p0'],
                    stdin=patch_file,
                    cwd=srcdir, env=env)

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://ftp.gnu.org/gnu/readline/readline-8.3.tar.gz', target,
            sha256='fe5383204467828cd495ee8d1d3c037a7eba1389c22bc6a041f627976f9061cc')

    def configure(self, env, srcdir):
        # ncurses' wide-character build keeps termcap entry points in the
        # separate libtinfow DSO, which must accompany the ncursesw probe.
        env['LIBS'] = '-ltinfow'
        steps.run_configure(self, srcdir, env, extra_config=(
            '--with-curses', '--with-shared-termcap-library',
            '--enable-shared', '--enable-static'))

    def build(self, env, srcdir):
        steps.make(srcdir, env, extra_opts=(
            'TERMCAP_LIB=-lncursesw -ltinfow',
            'SHLIB_LIBS=-lncursesw -ltinfow',
        ))

    def deploy(self, env, srcdir, deploydir):
        steps.make(srcdir, env, target='install', extra_opts=(
            'DESTDIR=%s' % deploydir,
            'TERMCAP_LIB=-lncursesw -ltinfow',
            'SHLIB_LIBS=-lncursesw -ltinfow',
        ))

    def postdeploy(self, env, srcdir, deploydir):
        libdir = os.path.join(deploydir, 'usr', 'lib')
        for library in ('readline', 'history'):
            real_name = 'lib%s.so.8.3' % library
            real_path = os.path.join(libdir, real_name)
            if not os.path.isfile(real_path):
                raise RuntimeError(
                    'readline shared library is missing: %s' % real_path)

            # Readline's installer does not recognize Pedigree and therefore
            # omits the links needed by both the runtime loader and -lreadline.
            for link_name, target in (
                ('lib%s.so.8' % library, real_name),
                ('lib%s.so' % library, 'lib%s.so.8' % library),
            ):
                link_path = os.path.join(libdir, link_name)
                if os.path.lexists(link_path):
                    os.unlink(link_path)
                os.symlink(target, link_path)
