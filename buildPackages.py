#!/usr/bin/env python2

import imp
import os
import shutil
import sys
import tarfile

import environment

from support import buildsystem


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
                    entry, e.message)
            else:
                package = loaded.get_package()
                all_packages[package.name()] = package

    return all_packages


def build_package(package, env):
    """Builds the given package."""
    package_id = '%s-%s' % (package.name(), package.version())

    download_target = os.path.join(env['DOWNLOAD_TEMP'], package_id)
    deploydir = os.path.join(env['OUTPUT_BASE'], package_id)
    srcdir = os.path.join(env['BUILD_BASE'], package_id)

    if os.path.isdir(deploydir):
        shutil.rmtree(deploydir)
    if os.path.isdir(srcdir):
        shutil.rmtree(srcdir)

    os.makedirs(deploydir)
    os.makedirs(srcdir)

    pass0_steps = ('download',)
    pass1_steps = ('patch', 'prebuild', 'configure', 'build')
    pass2_steps = ('deploy', 'postdeploy')
    pass3_steps = ('links',)

    if not os.path.isfile(download_target):
        for step in pass0_steps:
            print '== %s %s step ==' % (package_id, step)
            method = getattr(package, step)

            try:
                method(env, download_target)
            except buildsystem.OptionalError:
                download_target = None

    # Extract the given tarball.
    if download_target is not None:
        mode = 'r'
        tar_format = package.options().tarball_format
        if tar_format not in ['bare', 'xz']:
            mode = 'r:%s' % tar_format
        elif tar_format == 'xz':
            raise Exception('cannot handle xz just yet')

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

    for step in pass1_steps:
        print '== %s %s step ==' % (package_id, step)
        method = getattr(package, step)

        try:
            method(env, srcdir)
        except buildsystem.OptionalError:
            pass

    for step in pass2_steps:
        print '== %s %s step ==' % (package_id, step)
        method = getattr(package, step)

        try:
            method(env, srcdir, deploydir)
        except buildsystem.OptionalError:
            pass

    for step in pass3_steps:
        print '== %s %s step ==' % (package_id, step)
        method = getattr(package, step)

        try:
            method(env, deploydir, env['CROSS_BASE'])
        except buildsystem.OptionalError:
            pass

    # After build, look for pkg-config files to extract for our use.
    # ...



def build(packages, env):
    """Takes an ordered list of packages and builds them one-by-one."""
    built = set()
    for name, package in packages:
        if not set(package.build_requires()).issubset(built):
            print >>sys.stderr, 'Package %s build-depends not met.' % name
            continue

        try:
            build_package(package, env)
        except Exception as e:
            print >>sys.stderr, 'Building %s failed: %s' % (name, e.message)
            raise
        else:
            built.add(name)


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

    # Get packages to build.
    packages = load_packages(env)

    # Here: build dependency tree

    # Build packages.
    build(packages.items(), env)

    return 0


if __name__ == '__main__':
    exit(main(sys.argv))
