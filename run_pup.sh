#!/usr/bin/env bash

set -euo pipefail

repo_root=$(cd "$(dirname "$0")" && pwd -P)
builder_image=${PEDIGREE_APPS_BUILDER_IMAGE:-pedigree-apps-builder:local}

if ! docker image inspect "$builder_image" >/dev/null 2>&1; then
    echo "Builder image not found; run ./buildPackages.sh --rebuild-image --dry-run --list first." >&2
    exit 2
fi

docker_args=(
    run --rm --init --platform linux/amd64
    --user "$(id -u):$(id -g)"
    --env HOME=/tmp
    --volume "$repo_root:/workspace"
    --volume "$repo_root/pup/package_repo:/package_repo"
    --volume "$repo_root/pup/pup-docker.conf:/etc/pup.conf:ro"
)
if [[ -n "${PUP_UPLOAD_KEY:-}" ]]; then
    docker_args+=(--env PUP_UPLOAD_KEY)
fi

exec docker "${docker_args[@]}" "$builder_image" \
    pup --config=/etc/pup.conf "$@"
