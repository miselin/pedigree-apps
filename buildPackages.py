#!/usr/bin/env python3

import argparse
import logging
import os
import sys

import environment
from support import build
from support import buildsystem
from support import deps
from support import steps


VALID_ARCH_TARGETS = ("amd64",)
LOGGING_FORMAT = (
    "%(asctime)s %(module)-15s %(funcName)-20s %(levelname)-8s %(message)s"
)
log = logging.getLogger(__name__)


def upload_metadata_supported(packages):
    supported = True
    for name, package in packages:
        dependencies = package.install_deps()
        if not dependencies:
            continue
        log.error(
            'cannot upload "%s": the legacy PUP service cannot record '
            "runtime dependencies (%s)",
            name,
            ", ".join(dependencies),
        )
        supported = False
    return supported


def upload_all(packages, env, upload_key):
    if not upload_metadata_supported(packages):
        return 2

    artifacts = []
    for name, package in packages:
        deploy_base = os.path.join(
            env["OUTPUT_BASE"], name, package.version()
        )
        deploydir = os.path.join(deploy_base, "root")
        completion_marker = os.path.join(deploy_base, ".complete")
        archive = os.path.join(
            env["PACKMAN_REPO"],
            "%s-%s-%s.pup"
            % (name, package.version(), env["PACKMAN_TARGET_ARCH"]),
        )
        if not (
            os.path.isdir(deploydir)
            and os.path.isfile(completion_marker)
            and os.path.isfile(archive)
        ):
            log.error(
                'cannot upload "%s": build root, completion marker, or PUP '
                "archive is missing",
                name,
            )
            return 2
        artifacts.append((name, package, deploydir))

    for name, package, deploydir in artifacts:
        try:
            steps.upload_package(package, deploydir, env.copy(), upload_key)
        except Exception:
            log.exception('uploading "%s" failed', name)
            return 1
        log.info('uploaded "%s"', name)
    return 0


def build_all(packages, all_packages, env):
    failed = set()
    blocked = set()

    for name, package in packages:
        failed_dependencies = set(package.build_requires()).intersection(failed | blocked)
        if failed_dependencies:
            log.error(
                'not building "%s" because dependencies failed: %s',
                name,
                ", ".join(sorted(failed_dependencies)),
            )
            blocked.add(name)
            continue

        try:
            package_env = deps.prepare_sysroot(all_packages, package, env)
            build_log = build.build_package(package, package_env)
        except Exception:
            log.exception('building "%s" failed', name)
            failed.add(name)
        else:
            log.info('built "%s"; log: %s', name, build_log)

    if failed:
        log.error("failed packages: %s", ", ".join(sorted(failed)))
    if blocked:
        log.error("dependency-blocked packages: %s", ", ".join(sorted(blocked)))
    if failed or blocked:
        return 1
    return 0


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Build Pedigree ports locally.")
    parser.add_argument("--target", choices=VALID_ARCH_TARGETS, default="amd64")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list", action="store_true", help="list active packages")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--only", nargs="+", metavar="PACKAGE")
    group.add_argument("--only-depends", nargs="+", metavar="PACKAGE")
    upload_group = parser.add_mutually_exclusive_group()
    upload_group.add_argument(
        "--upload-only",
        action="store_true",
        help="upload existing completed artifacts without rebuilding",
    )
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args(argv[1:])


def main(argv=None):
    upload_key = os.environ.pop("UPLOAD_KEY", None)
    argv = argv or sys.argv
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format=LOGGING_FORMAT,
    )

    if not os.environ.get("PEDIGREE_APPS_CONTAINER"):
        log.error("use ./buildPackages.sh so the build runs in its Docker image")
        return 2
    if upload_key and not args.upload_only:
        log.error("UPLOAD_KEY is only accepted by an upload-only process")
        return 2

    env = environment.generate_environment(args.target)
    packages = buildsystem.load_packages(env)
    ordered = deps.sort_dependencies(packages)

    if args.list:
        for name, package in ordered:
            print("%s %s" % (name, package.version()))
        return 0

    if args.only_depends:
        ordered = deps.select_with_dependencies(packages, args.only_depends)
    elif args.only:
        unknown = sorted(set(args.only) - set(packages))
        if unknown:
            log.error("unknown packages: %s", ", ".join(unknown))
            return 2
        wanted = set(args.only)
        ordered = [item for item in ordered if item[0] in wanted]

    if args.dry_run:
        for name, package in ordered:
            print("%s %s" % (name, package.version()))
        return 0

    if args.upload_only and not upload_key:
        log.error("upload requires UPLOAD_KEY")
        return 2

    steps.prepare_package_manager(env)

    if args.upload_only:
        return upload_all(ordered, env, upload_key)

    return build_all(ordered, packages, env)


if __name__ == "__main__":
    raise SystemExit(main())
