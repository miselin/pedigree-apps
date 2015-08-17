
import os
import subprocess

from . import util


def prepare_compiler(env):
    """Carries across changes from a Pedigree build into the cross-toolchain.

    This is necessary to pick up changes in libc, libm, pthread, and various
    other Pedigree-specific libraries.
    """
    print '== Preparing Compiler =='

    links = (
        # Source -> Target
        ('$PEDIGREE_BASE/build/kernel/crt0.o', '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/kernel/crti.o', '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/kernel/crtn.o', '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/libpthread.so', '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/libpedigree.so', '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/libpedigree-c.so', '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/libpedigree.so', '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/libc.so', '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/libm.so', '$CROSS_BASE/$CROSS_TARGET/lib/'),
        ('$PEDIGREE_BASE/build/libs/libui.so', '$CROSS_BASE/$CROSS_TARGET/lib/'),

        ('$PEDIGREE_BASE/src/subsys/posix/include', '$CROSS_BASE/$CROSS_TARGET/include'),
        ('$PEDIGREE_BASE/src/subsys/native/include', '$CROSS_BASE/include/pedigree-native'),

        ('$PEDIGREE_BASE/build/libSDL.so', '$CROSS_BASE/lib/'),
        ('$PEDIGREE_BASE/src/lgpl/SDL-1.2.14/include', '$CROSS_BASE/include/SDL'),
    )

    # Clean up the base tree of the cross-compiler.
    cleanup_dirs = ['lib', 'include', 'bin']
    for cleanup in cleanup_dirs:
        target = os.path.join(env['CROSS_BASE'], cleanup)

        for entry in os.listdir(target):
            entry = os.path.join(target, entry)
            if os.path.islink(entry):
                print 'unlink', entry
                os.unlink(entry)

    # Create specific links that must exist.
    for source, target in links:
        source = util.expand(env, source)
        target = util.expand(env, target)

        if target.endswith('/'):
            target = os.path.join(target, os.path.basename(source))

        print target, '->', source

        if os.path.isfile(target) or os.path.islink(target):
            os.unlink(target)
        if os.path.isdir(target):
            shtuil.rmtree(target)

        os.symlink(source, target)


def chroot_spec(env):
    """Creates a new spec file for the build chroot.

    This forces GCC to look in the correct place for its libraries during the
    builds while allowing the use of a cross-toolchain that is already set up
    for non-chroot compilations.

    This will modify the environment so the compilers use the correct spec.

    Args:
        env: environment to use for the preparation
    """

    cc = env['CROSS_CC']
    if not os.path.exists(cc):
        cc = os.path.join(env['CROSS_BASE'], 'bin', env['CROSS_CC'])

    if not os.path.exists(cc):
        print >>sys.stderr, '$CC is useless'
        return

    # Get the existing specs.
    current_specs = new_specs = subprocess.check_output([cc, '-dumpspecs'])

    replacements = {
        '%D': '-L/libraries -rpath-link /libraries %D',
        '*cpp:\n': '*cpp:\n-I/include'
    }

    additions = '''*predefines:
-D__PEDIGREE__

%%rename cc1_cpu old_cc1_cpu
*cc1_cpu:
%s %%(old_cc1_cpu)

''' % env['CROSS_CFLAGS']

    for needle, repl in replacements.items():
        new_specs = new_specs.replace(needle, repl)

    new_specs += additions

    import difflib
    print '\n'.join(difflib.unified_diff(current_specs.splitlines(), new_specs.splitlines()))

    specfile_name = 'spec-%s' % env['CROSS_TARGET']
    with open(os.path.join(env['CROSS_BASE'], specfile_name), 'w') as f:
        f.write(new_specs)

    # Create a secondary bin directory for our wrappers :-)
    bin2 = os.path.join(env['CROSS_BASE'], 'bin2')
    print bin2
    if not os.path.isdir(bin2):
        os.makedirs(bin2)

    bin2_cc = os.path.join(bin2, env['CROSS_CC'])
    with open(bin2_cc, 'w') as f:
        f.write('''#!/bin/sh
%s /cross/bin/%s -specs=/cross/%s $*
''' % (env['CCACHE'], env['CROSS_CC'], specfile_name))
    os.chmod(bin2_cc, 0755)
