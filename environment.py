#!/usr/bin/env python2

import functools
import os


def expand(env, s):
    result = os.path.expandvars(s)
    for k, v in env.items():
        var = '$%s' % k
        result = result.replace(var, v)

    return result


def generate_environment(target_arch):
    env = {}

    # Simplify expansion.
    _expand = functools.partial(expand, env)

    # Remove any existing $MAKEFLAGS - a lot of builds don't handle concurrency
    # very well at all, and we don't want to pull in things like -k/-i/-B.
    env['MAKEFLAGS'] = '-j1'

    # Wipe out $LD_LIBRARY_PATH. None of the build hosts need this, and an
    # $LD_LIBRARY_PATH that contains '.' will cause a ton of weirdness.
    env['LD_LIBRARY_PATH'] = ''

    # Architecture-specific pieces.
    if target_arch == 'amd64':
        env['ARCH_TARGET'] = 'x86_64'
        env['ARCH_BITS'] = _expand('64')
        env['CROSS_CFLAGS'] = _expand('-O3 -m$ARCH_BITS -march=k8 -msse2')
        env['CROSS_CXXFLAGS'] = env['CROSS_CFLAGS']
        env['CROSS_TARGET'] = _expand('$ARCH_TARGET-pedigree')

    # Generic system setup. Overrides come from the
    # local_environment.modify_environment function if it exists.
    env['PEDIGREE_BASE'] = _expand('$HOME/src/pedigree')
    env['APPS_BASE'] = _expand('$HOME/src/pedigree-apps')
    env['CROSS_BASE'] = _expand('$PEDIGREE_BASE/pedigree-compiler')
    env['OUTPUT_BASE'] = _expand('$APPS_BASE/newpacks/$ARCH_TARGET')
    env['SOURCE_BASE'] = _expand('$APPS_BASE/packages')
    env['DOWNLOAD_TEMP'] = _expand('$APPS_BASE/downloads')
    env['BUILD_BASE'] = _expand('$SOURCE_BASE/builds')
    env['PACKMAN_PATH'] = _expand('$APPS_BASE/pup/pup')
    env['PACKMAN_REPO'] = _expand('$APPS_BASE/pup/package_repo')

    # Cross-toolchain.
    env['CROSS_CC'] = _expand('$CROSS_BASE/bin/$ARCH_TARGET-pedigree-gcc')
    env['CROSS_CXX'] = _expand('$CROSS_BASE/bin/$ARCH_TARGET-pedigree-gcc')
    env['CROSS_CPP'] = _expand('$CROSS_BASE/bin/$ARCH_TARGET-pedigree-cpp')
    env['CROSS_AS'] = _expand('$CROSS_BASE/bin/$ARCH_TARGET-pedigree-as')
    env['CROSS_LD'] = _expand('$CROSS_BASE/bin/$ARCH_TARGET-pedigree-gcc')
    env['CROSS_AR'] = _expand('$CROSS_BASE/bin/$ARCH_TARGET-pedigree-ar')
    env['CROSS_RANLIB'] = _expand('$CROSS_BASE/bin/$ARCH_TARGET-pedigree-ranlib')
    env['LIBS'] = _expand('')

    # Preprocessor options.
    # TODO(miselin): maybe we don't need these anymore.
    env['CROSS_CPPFLAGS'] = _expand('-D__PEDIGREE__ -I$CROSS_BASE/include '
        '-I$CROSS_BASE/include/SDL -I$CROSS_BASE/include/ncurses')

    # Linker options; -rpath-link is very important for linking.
    env['CROSS_LDFLAGS'] = _expand('-L$CROSS_BASE/lib -Wl,-rpath-link,$CROSS_BASE/lib')

    # Add local binary paths to $PATH.
    cross_bin = _expand('$CROSS_BASE/bin')
    if cross_bin not in os.environ['PATH']:
        env['PATH'] = _expand('%s:$PATH' % cross_bin)
    apps_bin = _expand('$APPS_BASE/bin')
    if apps_bin not in os.environ['PATH']:
        env['PATH'] = _expand('%s:$PATH' % apps_bin)

    # Build system tools.
    env['MAKE'] = '/usr/bin/make'

    # Pull in any local changes that the local system requires.
    try:
        from local_environment import modify_environment
        env = modify_environment(env)
    except ImportError:
        pass

    return env
