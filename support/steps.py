
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
    subprocess.check_call(['libtoolize', '-i', '-f', '--ltdl'], shell=True,
        cwd=srcdir, env=env)


def autoreconf(srcdir, env):
    """autoreconf's the target."""
    subprocess.check_call(['autoreconf', '-ifs'], shell=True, cwd=srcdir,
        env=env)


def autoconf(package, srcdir, env, extra_opts=(), inplace=True, host=True,
             paths=None):
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
