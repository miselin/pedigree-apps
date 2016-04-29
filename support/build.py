
import logging
import os
import shutil
import subprocess
import sys
import tarfile

from . import buildsystem
from . import deps
from . import steps
from . import toolchain


log = logging.getLogger(__name__)


def build_package(package, env):
    """Builds the given package."""
    package_id = '%s-%s' % (package.name(), package.version())
    env = env.copy()

    download_filename = '_%s' % package_id
    download_target = os.path.join(env['DOWNLOAD_TEMP'], download_filename)
    srcdir = os.path.join(env['CHROOT_BASE'], 'src')

    pass0_steps = ('download',)
    pass3_steps = ('repository',)

    if (package.options().always_download or
            not os.path.isfile(download_target)):
        for step in pass0_steps:
            log.info('== %s %s step ==', package_id, step)
            method = getattr(package, step)

            try:
                method(env.copy(), download_target)
            except buildsystem.OptionalError:
                download_target = None

    # Prepare to fill a chroot with the necessary files, now that we have the
    # source tarball downloaded and ready to extract.
    log.info('== %s chroot step ==', package_id)

    # Drop in patches as well.
    try:
        patches = package.patches(env, srcdir)
    except buildsystem.OptionalError:
        patches = []

    for patch in patches:
        target_dir = os.path.join(env['CHROOT_BASE'], 'patches')
        if '/' in patch:
            dirname = os.path.join(target_dir, os.path.dirname(patch))
            if not os.path.isdir(dirname):
                os.makedirs(dirname)

        shutil.copy2(os.path.join(package._path, 'patches', patch),
                     os.path.join(target_dir, patch))

    # Log path for the child. We open it in the parent so the child just gets
    # a file descriptor, without having to have the file present inside the
    # chroot proper.
    logdir = os.path.join(env['BUILD_BASE'], 'logs')
    if not os.path.isdir(logdir):
        os.makedirs(logdir)
    child_logpath = os.path.join(logdir, 'build-%s.log' % package_id)
    log_file = open(child_logpath, 'w')

    log.info('== %s log file is %s ==', package_id, child_logpath)

    # Clean up our handles before forking.
    sys.stdout.flush()
    sys.stderr.flush()
    child = os.fork()
    if child:
        # Close our reference to the log file, we don't care anymore.
        log_file.close()
        log_file = None

        # Wait for the forked child to complete, get its status.
        _, status = os.waitpid(child, 0)

        # Child finished, flush output before continuing.
        sys.stdout.flush()
        sys.stderr.flush()

        if status:
            raise Exception('build failed inside chroot')

        # Complete final steps.
        for step in pass3_steps:
            log.info('== %s %s step ==', package_id, step)
            method = getattr(package, step)

            try:
                method(env.copy(), srcdir, None)
                pass
            except buildsystem.OptionalError:
                pass

        return

    # Before entering chroot, redirect output to the build log file.
    log_fd = log_file.fileno()
    os.dup2(log_fd, sys.stdout.fileno())
    os.dup2(log_fd, sys.stderr.fileno())

    # Build parameters for the Docker invocation (including volumes to share).
    args = [
        '/usr/bin/env', 'docker', 'run',
    ]
    args += steps.get_volumes(env)
    args += [
        'pedigree-apps:buildroot',
        '/usr/bin/env', 'python', '/pedigree_apps/buildInChroot.py',
        '--package=' + package.name(), '--filename=' + download_filename,
        '--target=' + env['PACKMAN_TARGET_ARCH'],
    ]

    # Run the in-chroot builder now.
    os.execv(args[0], args)


def in_chroot(env, packages, package, package_id, download_filename):
    # Drop in support files from Pedigree build.
    toolchain.pedigree_into_chroot(env, '/')

    # Install our build_requires packages to the chroot path.
    deps.install_dependent_packages(dict(packages), package, env)

    pass1_steps = ('patch', 'prebuild', 'configure', 'build')
    pass2_steps = ('deploy', 'postdeploy', 'repository_prep')

    download_target = os.path.join('/download', download_filename)
    deploydir = '/__deploy'
    srcdir = '/src'

    # Extract the given tarball.
    if os.path.exists(download_target):
        # tar --strip=1
        def check_strip(tarinfo):
            return '/' in tarinfo.path

        def strip_first(tarinfo):
            stripped = tarinfo.path.split('/')[1:]
            tarinfo.path = os.path.join(*stripped)
            return tarinfo

        try:
            try:
                tar = tarfile.open(download_target)
                tar.extractall(path=srcdir,
                               members=(strip_first(x) for x in tar
                                        if check_strip(x)))
                tar.close()
            except tarfile.ReadError:
                # Can't do it in-process, shell out.
                subprocess.check_call([env['TAR'], '--strip', '1', '-xf',
                                       download_target], cwd=srcdir, env=env)
        except:
            # Wipe out the download if extraction failed.
            if os.path.exists(download_target):
                os.unlink(download_target)

            raise
    else:
        raise Exception('download target %r does not exist!' % download_target)

    for step in pass1_steps:
        log.info('== %s %s step ==', package_id, step)
        method = getattr(package, step)

        try:
            method(env.copy(), srcdir)
        except buildsystem.OptionalError:
            pass

    for step in pass2_steps:
        log.info('== %s %s step ==', package_id, step)
        method = getattr(package, step)

        try:
            method(env.copy(), srcdir, deploydir)
        except buildsystem.OptionalError:
            pass

    return 0
