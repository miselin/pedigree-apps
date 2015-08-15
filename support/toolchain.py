
import os

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