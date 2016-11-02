
import logging
import os
import shutil
import subprocess

from . import steps
from . import util


log = logging.getLogger(__name__)


def get_cc(env):
    """Get $CC while checking that it is valid."""
    cc = env['CROSS_CC']
    if not os.path.exists(cc):
        cc = os.path.join(env['CROSS_BASE'], 'bin', env['CROSS_CC'])

    if not os.path.exists(cc):
        log.error('$CC (%s) is useless', cc)
        return None

    return cc


def prepare_compiler(env):
    """Carries across changes from a Pedigree build into the cross-toolchain.

    This is necessary to pick up changes in libc, libm, pthread, and various
    other Pedigree-specific libraries.
    """
    log.info('== Preparing Compiler ==')

    cc = get_cc(env)
    if not cc:
        raise Exception('could not find the C compiler')

    vers = subprocess.check_output([cc, '-dumpversion']).strip()

    links = (
        # Source -> Target
        ('$PEDIGREE_BASE/build/musl/lib/libc.so',
            '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/libpedigree.so',
            '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/libpedigree-c.so',
            '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/libpedigree.so',
            '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/libs/libui.so',
            '$CROSS_BASE/$CROSS_TARGET/lib/'),

        # Dummy libs for musl (everything is in libc).
        ('$PEDIGREE_BASE/build/musl/lib/libdl.a',
            '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/musl/lib/libm.a',
            '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/musl/lib/libpthread.a',
            '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/musl/lib/libresolv.a',
            '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/musl/lib/librt.a',
            '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/musl/lib/libutil.a',
            '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/musl/lib/libxnet.a',
            '$CROSS_BASE/$CROSS_TARGET/lib/'),

        # crt
        ('$PEDIGREE_BASE/build/musl/lib/crt1.o',
            '$CROSS_BASE//lib/gcc/$CROSS_TARGET/%s/crt1.o' % vers),
        ('$PEDIGREE_BASE/build/musl/lib/rcrt1.o',
            '$CROSS_BASE//lib/gcc/$CROSS_TARGET/%s/rcrt1.o' % vers),
        ('$PEDIGREE_BASE/build/musl/lib/Scrt1.o',
            '$CROSS_BASE//lib/gcc/$CROSS_TARGET/%s/Scrt1.o' % vers),
        ('$PEDIGREE_BASE/build/musl/lib/crti.o',
            '$CROSS_BASE//lib/gcc/$CROSS_TARGET/%s/crti.o' % vers),
        ('$PEDIGREE_BASE/build/musl/lib/crtn.o',
            '$CROSS_BASE//lib/gcc/$CROSS_TARGET/%s/crtn.o' % vers),

        # NO $CROSS_TARGET include directory - use /include!!
        (None,
            '$CROSS_BASE/$CROSS_TARGET/include'),
    )

    # Clean up the base tree of the cross-compiler.
    cleanup_dirs = ['lib', 'include', 'bin']
    for cleanup in cleanup_dirs:
        target = os.path.join(env['CROSS_BASE'], cleanup)

        for entry in os.listdir(target):
            entry = os.path.join(target, entry)
            if os.path.islink(entry):
                log.debug('unlink %s', entry)
                os.unlink(entry)

    # Create specific links that must exist.
    for source, target in links:
        if source:
            source = util.expand(env, source)
        target = util.expand(env, target)

        if target.endswith('/'):
            target = os.path.join(target, os.path.basename(source))

        if source:
            log.debug('link %s -> %s', target, source)
        else:
            log.debug('rm   %s', target)

        if os.path.isfile(target) or os.path.islink(target):
            os.unlink(target)
        if os.path.isdir(target):
            shutil.rmtree(target)

        if source:
            steps.cmd(['/bin/cp', '-a', source, target])


def pedigree_into_chroot(env, chroot_dir):
    """Copy Pedigree-specific files into the given chroot for compilation.

    This is needed to provide the correct files, especially for #includes.
    """

    copy_paths = (
        ('$PEDIGREE_BASE/build/musl/include', 'include/'),
        ('$PEDIGREE_BASE/src/lgpl/SDL-1.2.14/include', 'include/SDL'),
        ('$PEDIGREE_BASE/build/libSDL.so', 'libraries/'),
        ('$PEDIGREE_BASE/build/libpedigree.so', 'libraries/'),
        ('$PEDIGREE_BASE/build/libpedigree-c.so', 'libraries/'),
        ('$PEDIGREE_BASE/build/libs/libui.so', 'libraries/'),
        ('$PEDIGREE_BASE/images/local/support/gcc/include/c++', 'include/c++'),
        ('$PEDIGREE_BASE/images/local/libraries/libstdc++.so', 'libraries/'),
        ('$PEDIGREE_BASE/images/local/libraries/libstdc++.a', 'libraries/'),
        ('$PEDIGREE_BASE/images/local/libraries/libsupc++.a', 'libraries/'),
        ('$APPS_BASE/bin/sdl-config', 'applications/'),
    )

    for source, target in copy_paths:
        source = util.expand(env, source)

        target_path = os.path.join(chroot_dir, target)
        if not os.path.isdir(target_path):
            os.makedirs(target_path)

        flags = '-a'
        if os.path.isdir(source):
            flags += 'rT'  # merge directory trees

        # Copy files (use cp - much more elegant than doing this in Python)
        if os.path.exists(source):
            steps.cmd(['/bin/cp', flags, source, target_path])


def prepare_package_manager(env):
    """Create necessary configuration files for the package manager."""
    with open(os.path.join(env['APPS_BASE'], 'pup.conf'), 'w') as f:
        f.write('''
[paths]
installroot=%(CHROOT_BASE)s
localdb=%(PACKMAN_REPO)s

[settings]
arch=%(PACKMAN_TARGET_ARCH)s

[remotes]
server=http://the-pedigree-project.appspot.com
upload=http://the-pedigree-project.appspot.com
''' % env)


def chroot_spec(env):
    """Creates a new spec file for the build chroot.

    This forces GCC to look in the correct place for its libraries during the
    builds while allowing the use of a cross-toolchain that is already set up
    for non-chroot compilations.

    This will modify the environment so the compilers use the correct spec.

    Args:
        env: environment to use for the preparation
    """

    cc = get_cc(env)
    if not cc:
        return

    # Get the existing specs.
    new_specs = subprocess.check_output([cc, '-dumpspecs']).decode('utf-8')

    replacements = {
        '%D': '-L/libraries -rpath-link /libraries %D',
        '*cpp:\n': ('*cpp:\n-D__PEDIGREE__ -I/include -isystem '
                    '/include/c++/%%(version) -isystem '
                    '/include/c++/%%(version)/%s ' % env['CROSS_TARGET'])
    }

    additions = ''
    if 'cc1_cpu' in new_specs:
        additions += '%rename cc1_cpu old_cc1_cpu\n\n'

    additions += '''*cc1_cpu:
    %s %%(old_cc1_cpu)
''' % env['CROSS_CFLAGS']

    for needle, repl in replacements.items():
        new_specs = new_specs.replace(needle, repl)

    new_specs += additions

    specfile_name = 'spec-%s' % env['CROSS_TARGET']
    with open(os.path.join(env['CROSS_BASE'], specfile_name), 'w') as f:
        f.write(new_specs)

    # Create a secondary bin directory for our wrappers :-)
    bin2 = os.path.join(env['CROSS_BASE'], 'bin2')
    if not os.path.isdir(bin2):
        os.makedirs(bin2)

    compilers = (env['CROSS_CC'], env['CROSS_CXX'],
                 '%s-c++' % env['CROSS_TARGET'])

    for compiler in compilers:
        bin2_compiler = os.path.join(bin2, compiler)
        with open(bin2_compiler, 'w') as f:
            f.write('''#!/bin/sh
%s /cross/bin/%s -pipe -specs=/cross/%s "$@"
''' % (env['CCACHE'], compiler, specfile_name))
        os.chmod(bin2_compiler, 0o755)

    # Create a dangling symlink for libtool. This won't be usable unless
    # packages actually declare libtool as a build-requires.
    libtool_link = os.path.join(bin2, 'libtool')
    if not (os.path.exists(libtool_link) or os.path.islink(libtool_link)):
        os.symlink('/applications/libtool', libtool_link)
    libtoolize_link = os.path.join(bin2, 'libtoolize')
    if not (os.path.exists(libtoolize_link) or
            os.path.islink(libtoolize_link)):
        os.symlink('/applications/libtoolize', libtoolize_link)
