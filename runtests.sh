#!/usr/bin/env bash

set -euo pipefail

python3 -m unittest -v \
    buildPackages_test \
    environment_test \
    support.build_test \
    support.buildsystem_test \
    support.deps_test \
    support.steps_test \
    support.toolchain_test \
    support.util_test \
    pup.dist_test \
    pup.pedigree_updater.commands.create_test
python3 -m compileall -q \
    buildPackages.py \
    buildInChroot.py \
    environment.py \
    support \
    packages \
    scripts \
    pup/pedigree_updater \
    pup/http/pup_http
