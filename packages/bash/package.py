
import os
import re
import stat
import subprocess

from support import buildsystem
from support import steps


class BashPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(BashPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'bash'

    def version(self):
        return '5.3.15'

    def release_version(self):
        # PUP releases are immutable; this numeric revision avoids replacing
        # the older package while remaining newer under PUP's version order.
        return self.version() + '.1'

    def build_requires(self):
        return ['readline', 'libiconv', 'gettext']

    def patches(self, env, srcdir):
        return (
            ['bash53-%03d' % patchlevel for patchlevel in range(1, 16)]
            + ['pedigree-sync-loadable.diff']
        )

    def patch(self, env, srcdir):
        # Upstream's official Bash maintenance patches are -p0 context diffs.
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
            'https://ftp.gnu.org/gnu/bash/bash-5.3.tar.gz', target,
            sha256='0d5cd86965f869a26cf64f4b71be7b96f90a3ba8b3d74e27e8e9d9d5550f31ba')

    def configure(self, env, srcdir):
        # Pedigree's libc glue supports getcwd(NULL, 0); cross configure
        # otherwise assumes that GNU extension is missing.
        # ncurses' wide build keeps the termcap entry points in libtinfow.
        env['LIBS'] = '-ltinfow'
        steps.run_configure(self, srcdir, env, extra_config=(
            '--without-bash-malloc', '--with-installed-readline',
            'bash_cv_getcwd_malloc=yes'))

    def install_deps(self):
        return ['readline']

    def build(self, env, srcdir):
        # Bash's support Makefile incorrectly reuses target LIBS for host
        # generators, where Pedigree's split libtinfow is unavailable.
        steps.make(srcdir, env, extra_opts=('LIBS_FOR_BUILD=',))

    def deploy(self, env, srcdir, deploydir):
        steps.make(srcdir, env, target='install', extra_opts=(
            'DESTDIR=%s' % deploydir, 'LIBS_FOR_BUILD='))

    def postdeploy(self, env, srcdir, deploydir):
        loadable_dir = os.path.join(deploydir, 'usr', 'lib', 'bash')
        for entry in os.scandir(loadable_dir):
            if entry.is_file(follow_symlinks=False):
                mode = stat.S_IMODE(entry.stat(follow_symlinks=False).st_mode)
                os.chmod(
                    entry.path,
                    mode & ~(stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH),
                )

        bashbug = os.path.join(deploydir, 'usr', 'bin', 'bashbug')
        with open(bashbug, encoding='utf-8') as source:
            contents = source.read()

        target_sysroot = os.path.normpath(env['TARGET_SYSROOT'])
        ports_sysroot = os.path.normpath(env['PORTS_SYSROOT'])
        staged_lib = os.path.join(ports_sysroot, 'usr', 'lib')
        sanitized = contents.replace(env['CROSS_CC'], 'gcc')
        for option in (
            '--sysroot=%s' % target_sysroot,
            '-Wl,-rpath-link,%s' % staged_lib,
        ):
            sanitized = re.sub(
                r'(?<![^\s\'\"=])%s(?=$|\s|[\'\"])'
                % re.escape(option),
                '',
                sanitized,
            )
        # Dependency flags still describe target paths after staging is gone.
        sanitized = sanitized.replace(ports_sysroot, '')
        sanitized = sanitized.replace(target_sysroot, '')

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
        leaked = [path for path in forbidden_paths if path in sanitized]
        if leaked:
            raise RuntimeError(
                'bashbug contains cross-build paths: %s'
                % ', '.join(leaked)
            )
        bashbug_mode = stat.S_IMODE(os.stat(bashbug).st_mode)
        os.chmod(bashbug, bashbug_mode | stat.S_IWUSR)
        try:
            with open(bashbug, 'w', encoding='utf-8') as destination:
                destination.write(sanitized)
        finally:
            os.chmod(bashbug, bashbug_mode)

        bash_pc = os.path.join(
            deploydir, 'usr', 'lib', 'pkgconfig', 'bash.pc')
        with open(bash_pc, encoding='utf-8') as source:
            pc_contents = source.read()
        pc_sanitized = pc_contents.replace(env['CROSS_CC'], 'gcc')
        pc_sanitized = pc_sanitized.replace(ports_sysroot, '')
        pc_sanitized = pc_sanitized.replace(target_sysroot, '')
        leaked = [path for path in forbidden_paths if path in pc_sanitized]
        if leaked:
            raise RuntimeError(
                'bash.pc contains cross-build paths: %s'
                % ', '.join(leaked)
            )
        with open(bash_pc, 'w', encoding='utf-8') as destination:
            destination.write(pc_sanitized)
