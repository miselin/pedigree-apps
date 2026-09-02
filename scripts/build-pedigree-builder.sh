#!/usr/bin/env bash

set -euo pipefail

repo_root=$(cd "$(dirname "$0")/.." && pwd -P)
pedigree_source=${PEDIGREE_SOURCE:-"$(cd "$repo_root/../pedigree" && pwd -P)"}
image=${PEDIGREE_BUILDER_OUTPUT_IMAGE:-pedigree-builder:local}

docker buildx build \
    --load \
    --platform linux/amd64 \
    --tag "$image" \
    --file "$pedigree_source/build-etc/docker/pedigree-builder.Dockerfile" \
    "$pedigree_source"

printf 'Built %s from %s\n' "$image" "$pedigree_source"
printf 'Use it with: PEDIGREE_BUILDER_IMAGE=%s ./buildPackages.sh --rebuild-image ...\n' "$image"
