
# Provides functions for common parts of build steps.

import os
import shutil
import subprocess
import urllib


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
        return os.path.join(srcdir, 'pedigree-build')


def libtoolize(srcdir, env):
    """libtoolize's the target."""
    libtoolize = os.path.join(env['CROSS_BASE'], 'bin', 'libtoolize')
    subprocess.check_call([libtoolize, '-i', '-f', '--ltdl'], cwd=srcdir,
        env=env)


def autoreconf(srcdir, env):
    """autoreconf's the target."""
    subprocess.check_call(['autoreconf', '-ifs'], shell=True, cwd=srcdir,
        env=env)


def autoconf(package, srcdir, env, extra_opts=(), inplace=True, host=True,
             extra_config=(), paths=None):
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

        if '$' in value:
            value = value.replace('$package', package.name())

        opts.append('--%s=%s' % (opt, value))

    opts.extend(extra_config)

    subprocess.check_call(opts, cwd=srcdir, env=env)


def make(srcdir, env, target=None, inplace=True):
    """Runs a Makefile."""
    builddir = get_builddir(srcdir, env, inplace)
    opts = [env['MAKE']]
    if target is not None:
        opts.append(target)
    subprocess.check_call(opts, cwd=builddir, env=env)


def download(url, target):
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
        print target, '->', source
        if os.path.exists(target) or os.path.islink(target):
            os.unlink(target)
        os.symlink(source, target)


def create_package(package, deploydir, env):
    package_builder = env['PACKMAN_PATH']
    repo_dir = env['PACKMAN_REPO']

    package_name = package.name()
    package_version = package.version()
    package_arch = env['PACKMAN_TARGET_ARCH']

    # TODO(miselin): add dependency information to pup.
    subprocess.check_call([package_builder, 'makepkg', '--path', deploydir,
        '--repo', repo_dir, '--name', package_name, '--ver', package_version,
        '--arch', package_arch], cwd=deploydir)
    subprocess.check_call([package_builder, 'regpkg',
        '--repo', repo_dir, '--name', package_name, '--ver', package_version,
        '--arch', package_arch], cwd=deploydir)

