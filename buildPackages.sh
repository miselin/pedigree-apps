#!/usr/bin/env bash

set -euo pipefail

repo_root=$(cd "$(dirname "$0")" && pwd -P)
pedigree_source=${PEDIGREE_SOURCE:-"$(cd "$repo_root/../pedigree" 2>/dev/null && pwd -P || true)"}
base_image=${PEDIGREE_BUILDER_IMAGE:-ghcr.io/miselin/pedigree-builder@sha256:14bf372f9d20b6bedda051265e8b6b0bcd98cf429626b55f7d05ce55c2252f75}
builder_image=${PEDIGREE_APPS_BUILDER_IMAGE:-pedigree-apps-builder:local}
rebuild=${PEDIGREE_APPS_REBUILD:-0}
jobs=${PEDIGREE_APPS_JOBS:-8}
upload=0
upload_only=0

if (($#)) && [[ "$1" == "amd64" || "$1" == "x64" ]]; then
    shift
fi

args=()
while (($#)); do
    case "$1" in
        --rebuild-image|--buildimages)
            rebuild=1
            shift
            ;;
        --target)
            if (($# < 2)); then
                echo "--target requires an architecture" >&2
                exit 2
            fi
            case "$2" in
                amd64|x64)
                    shift 2
                    ;;
                *)
                    args+=("$1" "$2")
                    shift 2
                    ;;
            esac
            ;;
        --target=amd64|--target=x64)
            shift
            ;;
        --upload)
            upload=1
            shift
            ;;
        --upload-only)
            upload_only=1
            args+=("$1")
            shift
            ;;
        *)
            args+=("$1")
            shift
            ;;
    esac
done

if [[ "$upload" == 1 && "$upload_only" == 1 ]]; then
    echo "--upload and --upload-only cannot be used together" >&2
    exit 2
fi
if [[ "$upload" == 1 || "$upload_only" == 1 ]] && [[ -z "${UPLOAD_KEY:-}" ]]; then
    echo "upload requires UPLOAD_KEY" >&2
    exit 2
fi

if [[ "$rebuild" == 1 ]] || ! docker image inspect "$builder_image" >/dev/null 2>&1; then
    docker build \
        --platform linux/amd64 \
        --build-arg "PEDIGREE_BUILDER_IMAGE=$base_image" \
        --tag "$builder_image" \
        --file "$repo_root/docker/Dockerfile" \
        "$repo_root"
fi

docker_args=(
    run --rm --init --platform linux/amd64
    --user "$(id -u):$(id -g)"
    --env HOME=/tmp
    --env CCACHE_DIR=/workspace/.build/ccache
    --env PEDIGREE_APPS_CONTAINER=1
    --env "PEDIGREE_APPS_JOBS=$jobs"
    --volume "$repo_root:/workspace"
)

if [[ -n "$pedigree_source" && -d "$pedigree_source" ]]; then
    docker_args+=(--volume "$pedigree_source:/pedigree:ro")
fi
run_builder() {
    local include_upload_key=$1
    shift
    local run_args=("${docker_args[@]}")
    if [[ "$include_upload_key" == 1 ]]; then
        run_args+=(--env UPLOAD_KEY)
    fi
    docker "${run_args[@]}" "$builder_image" \
        python3 /workspace/buildPackages.py --target amd64 "$@"
}

if [[ "$upload" == 1 ]]; then
    if ((${#args[@]})); then
        run_builder 0 "${args[@]}"
        run_builder 1 "${args[@]}" --upload-only
    else
        run_builder 0
        run_builder 1 --upload-only
    fi
elif [[ "$upload_only" == 1 ]]; then
    run_builder 1 "${args[@]}"
else
    if ((${#args[@]})); then
        run_builder 0 "${args[@]}"
    else
        run_builder 0
    fi
fi
