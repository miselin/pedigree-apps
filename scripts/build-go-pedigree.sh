#!/usr/bin/env bash
set -Eeuo pipefail

repo_root=$(cd -- "$(dirname -- "$0")/.." && pwd -P)
build_root=${PEDIGREE_GO_BUILD_DIR:-"$repo_root/.build/language-ports/go"}
mkdir -p "$build_root"
build_root=$(cd "$build_root" && pwd -P)
go_version=1.26.5
source_sha=495be4bc87176ac567392e5b4116abd98466d33d7b49d41e764ccc6976b2dc42
patch_file="$repo_root/language-ports/go/patches/go${go_version}-pedigree.patch"

case "$(uname -s)/$(uname -m)" in
    Darwin/arm64) host=darwin-arm64; bootstrap_sha=efb87ff28af9a188d0536ef5d42e63dd52ba8263cd7344a993cc48dd11dedb6a ;;
    Darwin/x86_64) host=darwin-amd64; bootstrap_sha=6231d8d3b8f5552ec6cbf6d685bdd5482e1e703214b120e89b3bf0d7bf1ef725 ;;
    Linux/x86_64) host=linux-amd64; bootstrap_sha=5c2c3b16caefa1d968a94c1daca04a7ca301a496d9b086e17ad77bb81393f053 ;;
    Linux/aarch64) host=linux-arm64; bootstrap_sha=fe4789e92b1f33358680864bbe8704289e7bb5fc207d80623c308935bd696d49 ;;
    *) echo "Unsupported bootstrap host: $(uname -s)/$(uname -m)" >&2; exit 1 ;;
esac
host_root="$build_root/$host"
mkdir -p "$host_root/cache" "$host_root/tmp"

sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

fetch() {
    local filename=$1 expected=$2
    if [ ! -f "$build_root/$filename" ]; then
        curl -fL --retry 3 -o "$build_root/$filename.incomplete" "https://go.dev/dl/$filename"
        mv "$build_root/$filename.incomplete" "$build_root/$filename"
    fi
    if [ "$(sha256 "$build_root/$filename")" != "$expected" ]; then
        echo "Checksum mismatch: $build_root/$filename" >&2
        exit 1
    fi
}

if [ -z "${GOROOT_BOOTSTRAP:-}" ]; then
    fetch "go${go_version}.${host}.tar.gz" "$bootstrap_sha"
    GOROOT_BOOTSTRAP="$host_root/bootstrap/go"
    if [ ! -x "$GOROOT_BOOTSTRAP/bin/go" ]; then
        mkdir -p "$host_root/bootstrap"
        tar -xzf "$build_root/go${go_version}.${host}.tar.gz" -C "$host_root/bootstrap"
    fi
fi

go_root=${PEDIGREE_GO_SOURCE_DIR:-"$host_root/go"}
patch_sha=$(sha256 "$patch_file")
patch_marker="$go_root/.pedigree-patched"
if [ -f "$patch_marker" ] && [ "$(cat "$patch_marker")" != "$patch_sha" ]; then
    if [ -n "${PEDIGREE_GO_SOURCE_DIR:-}" ]; then
        echo "Patch changed; provide a freshly extracted PEDIGREE_GO_SOURCE_DIR." >&2
        exit 1
    fi
    rm -rf -- "$go_root"
fi
if [ ! -d "$go_root" ]; then
    fetch "go${go_version}.src.tar.gz" "$source_sha"
    tar -xzf "$build_root/go${go_version}.src.tar.gz" -C "$host_root"
fi
go_root=$(cd "$go_root" && pwd -P)
if [ ! -f "$patch_marker" ]; then
    patch --batch --fuzz=0 -d "$go_root" -p1 < "$patch_file"
    printf '%s\n' "$patch_sha" > "$patch_marker"
fi

export GOENV=off GOTOOLCHAIN=local CGO_ENABLED=0
export GOCACHE="$host_root/cache" GOTMPDIR="$host_root/tmp"
export GOMAXPROCS=${PEDIGREE_APPS_JOBS:-6}
unset GOFLAGS GOEXPERIMENT GOROOT GOHOSTOS GOHOSTARCH
build_marker="$go_root/.pedigree-build"
if [ ! -f "$build_marker" ] || [ "$(cat "$build_marker")" != "$host:$patch_sha" ] ||
    [ ! -x "$go_root/pkg/tool/pedigree_amd64/compile" ]; then
    (
        cd "$go_root/src"
        env GOROOT_BOOTSTRAP="$GOROOT_BOOTSTRAP" GOOS=pedigree GOARCH=amd64 ./make.bash
    )
    printf '%s\n' "$host:$patch_sha" > "$build_marker"
fi

dist_targets=$("$go_root/bin/go" tool dist list)
if ! grep -qx pedigree/amd64 <<< "$dist_targets"; then
    echo "Toolchain does not advertise pedigree/amd64" >&2
    exit 1
fi
env GOOS=pedigree GOARCH=amd64 "$go_root/bin/go" build -trimpath \
    -o "$build_root/go-qualify" "$repo_root/language-ports/go/probe/main.go"

mkdir -p "$host_root/bin"
python3 - "$go_root" "$host_root/bin/pedigree-go" <<'PY'
import pathlib
import shlex
import sys
root, output = sys.argv[1:]
cache = str(pathlib.Path(output).parent.parent / 'cache')
pathlib.Path(output).write_text(
    '#!/usr/bin/env bash\n'
    'export GOOS=pedigree GOARCH=amd64 CGO_ENABLED=0 GOTOOLCHAIN=local GOENV=off\n'
    'export GOROOT=' + shlex.quote(root) + '\n'
    'if [ -z "${GOCACHE:-}" ]; then GOCACHE=' + shlex.quote(cache) + '; fi\n'
    'export GOCACHE\n'
    'exec "$GOROOT/bin/go" "$@"\n'
)
pathlib.Path(output).chmod(0o755)
PY
python3 "$repo_root/language-ports/go/stage.py" \
    "$go_root" "$build_root/go-qualify" "$build_root/native-root" \
    "$repo_root/language-ports/go/native-smoke"
printf 'Cross compiler: %s\nNative package root: %s\nRuntime probe: %s\n' \
    "$host_root/bin/pedigree-go" "$build_root/native-root" "$build_root/go-qualify"
