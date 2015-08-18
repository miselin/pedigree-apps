
import logging
import os
import shutil
import subprocess
import sys
import tarfile

from . import buildsystem


log = logging.getLogger(__name__)


def build_package(package, env):
    """Builds the given package."""
    package_id = '%s-%s' % (package.name(), package.version())
    env = env.copy()

    download_filename = '_%s' % package_id
    download_target = os.path.join(env['DOWNLOAD_TEMP'], download_filename)
    srcdir = os.path.join(env['CHROOT_BASE'], 'src')
    deploydir = os.path.join(env['CHROOT_BASE'], '__deploy')

    for d in [deploydir, srcdir]:
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)

    pass0_steps = ('download',)
    pass1_steps = ('patch', 'prebuild', 'configure', 'build')
    pass2_steps = ('deploy', 'postdeploy')
    pass3_steps = ('repository',)

    if not os.path.isfile(download_target):
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
        shutil.copy2(os.path.join(package._path, 'patches', patch),
            os.path.join(env['CHROOT_BASE'], 'patches', patch))

    # Clean up our handles before forking.
    sys.stdout.flush()
    sys.stderr.flush()
    child = os.fork()
    if child:
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
                method(env.copy(), srcdir, deploydir)
            except buildsystem.OptionalError:
                pass

        return

    os.chroot(env['CHROOT_BASE'])

    download_target = os.path.join('/download', download_filename)
    deploydir = '/__deploy'
    srcdir = '/src'

    # Extract the given tarball.
    if download_target is not None:
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

                try:
                    tar = tarfile.open(download_target, mode=mode)
                    tar.extractall(path=srcdir, members=(strip_first(x) for x in tar if check_strip(x)))
                    tar.close()
                except:
                    # Wipe out the download if extraction failed.
                    if os.path.exists(download_target):
                        os.unlink(download_target)

                    raise
        elif tar_format == 'xz':
            # Can't do it in-process, shell out.
            subprocess.check_call([env['TAR'], '--strip', '1', '-xf', download_target], cwd=srcdir, env=env)

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

    exit(0)
