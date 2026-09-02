import os
import re

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
        return '1.3.20260721'

    def build_requires(self):
        return ['ncurses']

    def patches(self, env, srcdir):
        return ['pedigree-shared.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://invisible-island.net/archives/dialog/'
            'dialog-1.3-20260721.tgz', target,
            sha256='62bdf59057d4f760a1cc2217827f07887b4a3eebf694c25eacd4803d2171cdc6')

    def configure(self, env, srcdir):
        # ncurses' wide build keeps stdscr and other terminfo symbols in the
        # separate libtinfow DSO.
        env['LIBS'] = '-ltinfow'
        steps.run_configure(self, srcdir, env, extra_config=(
            '--with-pkg-config',
            '--with-pkg-config-libdir=/usr/lib/pkgconfig',
            '--with-ncursesw',
            '--enable-pc-files', '--with-shared', '--disable-rpath'),
            not_paths=('docdir',))

    def install_deps(self):
        return ['ncurses']

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        install_opts = ('DESTDIR=' + deploydir,)
        # Create the DSO and its ABI/linker symlinks before install-full copies
        # the development files; install-full alone omits those symlinks.
        steps.make(srcdir, env, target='install.libs',
                   extra_opts=install_opts)
        steps.make(srcdir, env, target='install-full',
                   extra_opts=install_opts)

    def postdeploy(self, env, srcdir, deploydir):
        ports_sysroot = os.path.normpath(env['PORTS_SYSROOT'])
        target_sysroot = os.path.normpath(env['TARGET_SYSROOT'])
        staged_lib = os.path.join(ports_sysroot, 'usr', 'lib')
        forbidden_paths = tuple(
            path
            for path in (
                env.get('APPS_BASE'),
                env.get('CROSS_BASE'),
                ports_sysroot,
                target_sysroot,
            )
            if path
        )

        for relative_path in (
            os.path.join('usr', 'bin', 'dialog-config'),
            os.path.join('usr', 'lib', 'pkgconfig', 'dialog.pc'),
        ):
            metadata_path = os.path.join(deploydir, relative_path)
            with open(metadata_path, encoding='utf-8') as source:
                contents = source.read()
            sanitized = re.sub(
                r'(?<![^\s\'"=])%s(?=$|\s|[\'\"])'
                % re.escape('-Wl,-rpath-link,%s' % staged_lib),
                '',
                contents,
            )
            sanitized = sanitized.replace(ports_sysroot, '')
            sanitized = sanitized.replace(target_sysroot, '')
            leaked = [path for path in forbidden_paths if path in sanitized]
            if leaked:
                raise RuntimeError(
                    '%s contains cross-build paths: %s'
                    % (relative_path, ', '.join(leaked))
                )
            with open(metadata_path, 'w', encoding='utf-8') as destination:
                destination.write(sanitized)
