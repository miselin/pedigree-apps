
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
    'libexecdir': '/applications/internal',
    'sysconfdir': '/config',
    'libdir': '/libraries',
    'includedir': '/include',
    'oldincludedir': '/include',
    'mandir': '/doc/man',
    'prefix': '/support/$package',
    'exec-prefix': '/support/$package',
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
    target_dir = os.path.dirname(target)
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir)
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


def pup_package(package, deploydir, env, upload=False):
    # Chroot?
    if os.path.exists('/pedigree_apps'):
        config_file = '/pedigree_apps/pup/pup-docker.conf'
    else:
        config_file = os.path.join(env['APPS_BASE'], 'pup.conf')

    package_name = package.name()
    package_version = package.version()
    package_arch = env['PACKMAN_TARGET_ARCH']

    env = env.copy()
    env['PYTHONPATH'] = env['PACKMAN_PATH']

    # TODO(miselin): add dependency information.
    if upload:
        try:
            key = env['UPLOAD_KEY']
        except KeyError:
            log.info('no upload key is present, skipping upload')
            return
        cmd([env['PACKMAN_SCRIPT'], '--config=%s' % config_file, 'register',
             '--package', package_name, '--version', package_version,
             '--architecture', package_arch, '--key', key])
    else:
        log.info('config file is %r', config_file)
        cmd([env['PACKMAN_SCRIPT'], '--config=%s' % config_file, 'create',
             '--path', deploydir, '--package', package_name,
             '--version', package_version, '--architecture', package_arch],
            cwd=deploydir)


def create_package(package, deploydir, env):
    pup_package(package, deploydir, env, upload=False)


def upload_package(package, deploydir, env):
    pup_package(package, deploydir, env, upload=True)


def split_paths(path):
    result = [path]
    head = path
    while True:
        head, tail = os.path.split(head)
        if not tail:
            break

        result.insert(0, head)

    return result


def makedirs_and_chown(path, env):
    elevated = os.getuid() == 0

    if os.path.exists(path):
        return

    for p in split_paths(path):
        if not os.path.exists(p):
            os.mkdir(p)
            # Provide correct access while elevated.
            if elevated:
                os.chown(p, int(env['UNPRIVILEGED_UID']),
                         int(env['UNPRIVILEGED_GID']))


def get_volumes(env):
    # Create needed directories to start with.
    makedirs_and_chown(env['CHROOT_BASE'], env)
    makedirs_and_chown(env['DOWNLOAD_TEMP'], env)
    makedirs_and_chown(env['DEPLOY_BASE'], env)
    makedirs_and_chown(env['PACKMAN_REPO'], env)

    def envify(s, env):
        return s % env

    # Pass volume parameters.
    return [
        '-v', envify('%(CROSS_BASE)s:/cross:ro', env),
        '-v', envify('%(PEDIGREE_BASE)s:/pedigree_src:ro', env),
        '-v', envify('%(APPS_BASE)s:/pedigree_apps:ro', env),
        '-v', envify('%(DOWNLOAD_TEMP)s:/download', env),
        '-v', envify('%(CHROOT_BASE)s/patches:/patches', env),
        '-v', envify('%(PACKMAN_REPO)s:/package_repo', env),
    ]


def create_chroot(env):
    """Create chroot if it doesn't exist yet and clean it out ready to build.

    Args:
        env: environment to use and modify to use the chroot.
    """

    # Make sure we have enough support directories in place.
    makedirs_and_chown(os.path.join(env['CHROOT_BASE'], 'patches'), env)

    # Build Docker image for this system.
    subprocess.check_call(['/usr/bin/env', 'docker', 'build', '-t',
                           'pedigree-apps:buildroot', '-f',
                           os.path.join(env['APPS_BASE'], 'docker',
                                        'Dockerfile'), '.'],
                          cwd=env['APPS_BASE'])


def chroot_environment_update(env):
    """Update the given environment's $PATH as needed for the chroot."""
    for k, v in env.items():
        if v.startswith(env['CROSS_BASE']):
            v = v.replace(env['CROSS_BASE'], '/cross')
            env[k] = v
    if not util.path_in_colon_list('/cross/bin', env['PATH']):
        env['PATH'] = util.expand(env, '/cross/bin:$PATH')
    if not util.path_in_colon_list('/cross/bin2', env['PATH']):
        env['PATH'] = util.expand(env, '/cross/bin2:$PATH')
