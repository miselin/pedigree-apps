import copy
import logging
import os
import shutil
import tarfile
from pathlib import PurePosixPath

from . import buildsystem
from . import steps


log = logging.getLogger(__name__)


def _safe_members(archive):
    members = archive.getmembers()
    paths = [PurePosixPath(member.name) for member in members]
    first_components = {path.parts[0] for path in paths if path.parts}
    strip_root = None
    if len(first_components) == 1 and any(len(path.parts) > 1 for path in paths):
        strip_root = next(iter(first_components))

    for member in members:
        path = PurePosixPath(member.name)
        parts = path.parts[1:] if strip_root else path.parts
        if not parts:
            continue
        if path.is_absolute() or ".." in parts:
            raise RuntimeError("unsafe archive member: %s" % member.name)
        if member.isdev() or member.isfifo():
            raise RuntimeError("unsupported archive member: %s" % member.name)

        extracted = copy.copy(member)
        extracted.name = str(PurePosixPath(*parts))
        yield extracted


def _run_optional(package, method_name, *args):
    try:
        getattr(package, method_name)(*args)
    except buildsystem.OptionalError:
        return False
    return True


def build_package(package, env):
    package_id = "%s-%s" % (package.name(), package.version())
    env = env.copy()
    os.makedirs(env["DOWNLOAD_TEMP"], exist_ok=True)
    os.makedirs(env["BUILD_BASE"], exist_ok=True)
    os.makedirs(env["OUTPUT_BASE"], exist_ok=True)

    download_target = os.path.join(env["DOWNLOAD_TEMP"], package_id + ".source")
    build_root = os.path.join(env["BUILD_BASE"], "work", package_id)
    srcdir = os.path.join(build_root, "src")
    deploy_base = os.path.join(
        env["OUTPUT_BASE"], package.name(), package.version()
    )
    deploydir = os.path.join(deploy_base, "root")
    staging_deploydir = os.path.join(deploy_base, "root.incomplete")
    completion_marker = os.path.join(deploy_base, ".complete")
    logdir = os.path.join(env["BUILD_BASE"], "logs")
    os.makedirs(logdir, exist_ok=True)
    env["BUILD_LOG"] = os.path.join(logdir, "build-%s.log" % package_id)
    with open(env["BUILD_LOG"], "w", encoding="utf-8") as build_log:
        build_log.write("Building %s\n" % package_id)

    if package.options().always_download and os.path.isfile(download_target):
        os.unlink(download_target)
    log.info("== %s download ==", package_id)
    try:
        package.download(env.copy(), download_target)
    except buildsystem.OptionalError:
        download_target = None

    shutil.rmtree(build_root, ignore_errors=True)
    shutil.rmtree(staging_deploydir, ignore_errors=True)
    os.makedirs(srcdir)
    os.makedirs(staging_deploydir)

    try:
        if download_target:
            log.info("== %s extract ==", package_id)
            with tarfile.open(download_target) as archive:
                archive.extractall(srcdir, members=_safe_members(archive), filter="data")

        for phase in ("patch", "prebuild", "configure", "build"):
            log.info("== %s %s ==", package_id, phase)
            _run_optional(package, phase, env.copy(), srcdir)

        for phase in ("deploy", "postdeploy", "check", "repository_prep"):
            log.info("== %s %s ==", package_id, phase)
            _run_optional(
                package, phase, env.copy(), srcdir, staging_deploydir
            )
    except BaseException:
        shutil.rmtree(staging_deploydir, ignore_errors=True)
        if (
            download_target
            and os.path.isfile(download_target)
            and not tarfile.is_tarfile(download_target)
        ):
            os.unlink(download_target)
        raise

    shutil.rmtree(deploydir, ignore_errors=True)
    os.replace(staging_deploydir, deploydir)
    marker_temporary = completion_marker + ".tmp"
    with open(marker_temporary, "w", encoding="utf-8") as marker:
        marker.write(package_id + "\n")
    os.replace(marker_temporary, completion_marker)

    return env["BUILD_LOG"]
