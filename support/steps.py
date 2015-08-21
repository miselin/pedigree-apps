
# Provides functions for common parts of build steps.

import logging
import os
import shutil
import subprocess
import urllib

from . import util


log = logging.getLogger(__name__)


AUTOCONF_PATHFLAGS = {
    'bindir': '/applications',
    'sbindir': '/applications',
    'libexecdir': '/applications',
    'sysconfdir': '/config',
    'libdir': '/libraries',
    'includedir': '/include',
    'oldincludedir': '/include',
    'mandir': '/doc/man',
    'prefix': '/support/$package',
    'docdir': '/docs/$package',
}


def get_builddir(srcdir, env, inplace):
    if inplace:
        return srcdir
    else:
        path = os.path.join(srcdir, 'pedigree-build')
        if not os.path.isdir(path):
            os.makedirs(path)
        return path


def cmd(*args, **kwargs):
    log.debug('cmd: %r %r', args, kwargs)
    subprocess.check_call(*args, **kwargs)


def libtoolize(srcdir, env, ltdl_dir=None):
    """libtoolize's the target."""
    libtoolize = '/applications/libtoolize'
    if ltdl_dir:
        ltdl_dir = '=%s' % ltdl_dir
    else:
        ltdl_dir = ''
    cmd([libtoolize, '-i', '-f', '--ltdl%s' % ltdl_dir], cwd=srcdir, env=env)


def autoreconf(srcdir, env, extra_flags=()):
    """autoreconf's the target."""
    cmd([env['AUTORECONF'], '-ifs'] + list(extra_flags), cwd=srcdir, env=env)


def autoconf(srcdir, env, aclocal_flags=(), only_aclocal=False):
    """Runs aclocal and then autoconf for the target."""
    aclocal_cmd = [env['ACLOCAL']] + list(aclocal_flags)
    cmd(aclocal_cmd, cwd=srcdir, env=env)
    if not only_aclocal:
        cmd([env['AUTOCONF']], cwd=srcdir, env=env)


def run_configure(package, srcdir, env, inplace=True, host=True,
                  extra_config=(), paths=None, not_paths=None):
    """Runs an Autoconf configure script."""
    cmd_env = env.copy()

    builddir = get_builddir(srcdir, env, inplace)

    configure_script = os.path.join(srcdir, 'configure')
    opts = [configure_script]

    if host:
        opts.append('--host=%s' % cmd_env['CROSS_TARGET'])

    if paths is None:
        paths = AUTOCONF_PATHFLAGS.keys()

    for opt, value in AUTOCONF_PATHFLAGS.items():
        if opt not in paths:
            continue
        elif not_paths and opt in not_paths:
            continue

        if '$' in value:
            value = value.replace('$package', package.name())

        opts.append('--%s=%s' % (opt, value))

    opts.extend(extra_config)

    cmd(opts, cwd=builddir, env=env)


def make(srcdir, env, target=None, inplace=True, extra_opts=()):
    """Runs a Makefile."""
    builddir = get_builddir(srcdir, env, inplace)
    opts = [env['MAKE']]
    if target is not None:
        opts.append(target)
    opts.extend(list(extra_opts))
    cmd(opts, cwd=builddir, env=env)


def download(url, target):
    log.debug('download "%s" -> %s', url, target)
    with open(target, 'wb') as t:
        f = urllib.urlopen(url)
        shutil.copyfileobj(f, t)
        f.close()


def symlinks(deploydir, cross_dir, bins=(), libs=(), headers=()):
    """Create symlinks in the given cross-compiler for the package."""

    symlinks = []

    for bin in bins:
        bin_source = os.path.join(deploydir, 'applications', bin)
        bin_target = os.path.join(cross_dir, 'bin', bin)
        symlinks.append((bin_source, bin_target))

    for lib in libs:
        lib_source = os.path.join(deploydir, 'libraries', lib)
        lib_target = os.path.join(cross_dir, 'lib', lib)
        symlinks.append((lib_source, lib_target))

    for include in headers:
        include_source = os.path.join(deploydir, 'include', include)
        include_target = os.path.join(cross_dir, 'include', include)
        symlinks.append((include_source, include_target))

    for source, target in symlinks:
        logging.debug('symlink: %s -> %s', target, source)
        if os.path.exists(target) or os.path.islink(target):
            os.unlink(target)
        os.symlink(source, target)


def create_package(package, deploydir, env):
    config_file = os.path.join(env['APPS_BASE'], 'pup.conf')

    package_name = package.name()
    package_version = package.version()
    package_arch = env['PACKMAN_TARGET_ARCH']

    env = env.copy()

    env['PYTHONPATH'] = env['PACKMAN_PATH']

    # TODO(miselin): add dependency information.
    cmd([env['PACKMAN_SCRIPT'], '--config=%s' % config_file, 'create',
         '--path', deploydir, '--package', package_name,
         '--version', package_version, '--architecture', package_arch],
        cwd=deploydir)
    cmd([env['PACKMAN_SCRIPT'], '--config=%s' % config_file, 'register',
         '--package', package_name, '--version', package_version,
         '--architecture', package_arch], cwd=deploydir)


def create_chroot(env):
    """Create chroot if it doesn't exist yet and clean it out ready to build.

    Args:
        env: environment to use and modify to use the chroot.
    """
    elevated = os.getuid() == 0

    chroot_base = env['CHROOT_BASE']
    if not os.path.exists(chroot_base):
        os.makedirs(chroot_base)

    # Provide correct access while elevated.
    if elevated:
        os.chown(env['CHROOT_BASE'], int(env['UNPRIVILEGED_UID']),
                 int(env['UNPRIVILEGED_GID']))

    # Host filesystem layout.
    bind_mounts = {
        'bin': '/bin',
        'sbin': '/sbin',
        'usr': '/usr',
        'lib': '/lib',
        'var': '/var',
        'proc': '/proc',
        'dev': '/dev',
        'etc': '/etc',
        'lib64': '/lib64',
        'sys': '/sys',
        'opt': '/opt',
        'cross': env['CROSS_BASE'],
        'pedigree_src': env['PEDIGREE_BASE'],
        'ccache': (True, env['CCACHE_TARGET_DIR']),
        'download': (True, env['DOWNLOAD_TEMP']),
    }
    pedigree_structure = ['applications', 'libraries', 'include', 'support',
                          'system', 'config', 'doc']
    support_structure = ['tmp', 'run', 'patches', 'root', '__deploy']

    extra_unprivileged_paths = ['ccache', 'download']

    # Start by clearing out the chroot tree of anything not in our mounts.
    for entry in os.listdir(chroot_base):
        if entry in bind_mounts:
            continue

        entry_path = os.path.join(chroot_base, entry)
        if os.path.isdir(entry_path):
            shutil.rmtree(entry_path)
        else:
            os.unlink(entry_path)

    # Create necessary Pedigree structure.
    created_dirs = pedigree_structure + support_structure
    if elevated:
        created_dirs.extend(bind_mounts.keys())

    for entry in created_dirs:
        entry_target = os.path.join(chroot_base, entry)
        if not os.path.isdir(entry_target):
            os.makedirs(entry_target)

        if elevated:
            if ((entry in extra_unprivileged_paths) or
                    (entry not in bind_mounts.keys())):
                os.chown(entry_target, int(env['UNPRIVILEGED_UID']),
                         int(env['UNPRIVILEGED_GID']))

    # Update the environment.
    for k, v in env.items():
        if v.startswith(env['CROSS_BASE']):
            v = v.replace(env['CROSS_BASE'], '/cross')
            env[k] = v
    if not util.path_in_colon_list('/cross/bin', env['PATH']):
        env['PATH'] = util.expand(env, '/cross/bin:$PATH')
    if not util.path_in_colon_list('/cross/bin2', env['PATH']):
        env['PATH'] = util.expand(env, '/cross/bin2:$PATH')

    # Done, unless we need to verify mounts.
    if not elevated:
        return

    # Mount.
    for path, target in bind_mounts.items():
        rw = False
        if isinstance(target, tuple):
            rw, target = target

        path = os.path.join(chroot_base, path)
        if not os.path.exists(target):
            # eg, no /lib64 present. This is OK.
            continue

        if not os.listdir(path):
            # Nothing here, we need to create the mount.
            # We remount read-only so that the host filesystem cannot be easily
            # wiped out by accident.
            cmd([env['MOUNT'], '--bind', target, path], env=env)
            if not rw:
                cmd([env['MOUNT'], '--bind', '-o', 'remount,ro', target, path],
                    env=env)
