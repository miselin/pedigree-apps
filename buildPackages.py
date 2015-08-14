#!/usr/bin/env python2

import collections
import imp
import os
import shutil
import sys
import subprocess
import tarfile

import environment

from support import buildsystem
from support import steps
from support import util


VALID_ARCH_TARGETS = ('amd64',)


def load_packages(env):
    # Find packages to build.
    all_packages = {}
    packages_dir = env['SOURCE_BASE']
    for entry in os.listdir(packages_dir):
        entry_path = os.path.join(packages_dir, entry)
        if not os.path.isdir(entry_path):
            continue

        module = os.path.join(entry_path, 'package.py')
        if os.path.exists(module):
            try:
                loaded = imp.load_source('pedigree_%s' % entry, module)
            except Exception as e:
                print >>sys.stderr, '%s failed to load (%s), ignoring.' % (
                    entry, e)

    # Collect subclasses of packages.
    collected_packages = buildsystem.Package.__subclasses__()
    for package_cls in collected_packages:
        package = package_cls(sys.modules[package_cls.__module__].__file__)
        if package.name():
            all_packages[package.name()] = package

    return all_packages


def build_package(package, env):
    """Builds the given package."""
    package_id = '%s-%s' % (package.name(), package.version())
    env = env.copy()

    download_target = os.path.join(env['DOWNLOAD_TEMP'], '_%s' % package_id)
    srcdir = os.path.join(env['BUILD_BASE'], package_id)
    deploydir = os.path.join(env['OUTPUT_BASE'], package_id)

    for d in [deploydir, srcdir]:
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)

    pass0_steps = ('download',)
    pass1_steps = ('patch', 'prebuild', 'configure', 'build')
    pass2_steps = ('deploy', 'postdeploy', 'repository')
    pass3_steps = ('links', 'pkgconfig')

    if not os.path.isfile(download_target):
        for step in pass0_steps:
            print '== %s %s step ==' % (package_id, step)
            method = getattr(package, step)

            try:
                method(env.copy(), download_target)
            except buildsystem.OptionalError:
                download_target = None

    # Prepare to fill a chroot with the necessary files, now that we have the
    # source tarball downloaded and ready to extract.
    print '== %s chroot step ==' % package_id
    print '(todo: chroots)'

    # Extract the given tarball.
    if download_target is not None:
        mode = 'r'
        tar_format = package.options().tarfile_format
        if tar_format not in ['bare', 'xz']:
            mode = 'r:%s' % tar_format

            if tar_format != 'none':
                # tar --strip=1
                def check_strip(tarinfo):
                    return '/' in tarinfo.path
                def strip_first(tarinfo):
                    stripped = tarinfo.path.split('/')[1:]
                    tarinfo.path = os.path.join(*stripped)
                    return tarinfo

                tar = tarfile.open(download_target, mode=mode)
                tar.extractall(path=srcdir, members=(strip_first(x) for x in tar if check_strip(x)))
                tar.close()
        elif tar_format == 'xz':
            # Can't do it in-process, shell out.
            print download_target
            print srcdir
            subprocess.check_call([env['TAR'], '--strip', '1', '-xf', download_target], cwd=srcdir, env=env)

    for step in pass1_steps:
        print '== %s %s step ==' % (package_id, step)
        method = getattr(package, step)

        try:
            method(env.copy(), srcdir)
        except buildsystem.OptionalError:
            pass

    for step in pass2_steps:
        print '== %s %s step ==' % (package_id, step)
        method = getattr(package, step)

        try:
            method(env.copy(), srcdir, deploydir)
        except buildsystem.OptionalError:
            pass

    for step in pass3_steps:
        print '== %s %s step ==' % (package_id, step)
        method = getattr(package, step)

        try:
            method(env.copy(), deploydir, env['CROSS_BASE'])
        except buildsystem.OptionalError:
            pass


def build(packages, env):
    """Takes an ordered list of packages and builds them one-by-one."""
    built = set()
    for name, package in packages:
        if not set(package.build_requires()).issubset(built):
            print >>sys.stderr, 'Package "%s" build-depends not met.' % name
            continue

        try:
            build_package(package, env)
        except Exception as e:
            print >>sys.stderr, 'Building %s failed: %s' % (name, e.message)
            raise
        else:
            built.add(name)


def sort_dependencies(packages):
    """Sorts the given packages based on dependencies.

    Returns:
        An iterable of (package_name, package) tuples.
    """

    tree = collections.defaultdict(list)
    for package_name, package in packages.items():
        _ = tree[package_name]
        for depends in package.build_requires():
            tree[depends].append(package_name)

    # Tree is now a set of <package> -> <things depending on package> pairs.
    # We need to sort the list so the package appears before everything that
    # depends on it.
    # TODO(miselin): this needs substantially more testing
    seen = set()
    result = []
    for package, deps in tree.items():
        insert = False
        for dep in deps:
            if dep in seen:
                insert = True
                break

        insertion = (package, packages[package])

        if insert:
            result.insert(0, insertion)
        else:
            result.append(insertion)

        seen.add(package)

    return result


def prepare_compiler(env):
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


def main(argv):
    if len(argv) < 2:
        print >>sys.stderr, 'Usage: buildPackages <arch_target>'
        return 1

    if argv[1] not in VALID_ARCH_TARGETS:
        print >>sys.stderr, ('Valid arch_target values: %s' %
            ','.join(VALID_ARCH_TARGETS))
        return 1

    # Load up an environment ready for building.
    env = environment.generate_environment(argv[1])

    # Prepare the cross-toolchain for building.
    prepare_compiler(env)

    # Get packages to build.
    packages = load_packages(env)

    # Sort dependencies so the build is performed correctly.
    packages = sort_dependencies(packages)

    # Build packages.
    build(packages, env)

    return 0


if __name__ == '__main__':
    exit(main(sys.argv))
