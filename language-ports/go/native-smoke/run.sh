#!/bin/sh
set -eu

source_dir=${1:-/usr/share/go/native-smoke}
work=$(mktemp -d /tmp/go-native-XXXXXX)
trap 'rm -rf "$work"' EXIT HUP INT TERM
cp -R "$source_dir/." "$work/"
cd "$work"
mkdir cache tmp
export GOCACHE="$work/cache" GOTMPDIR="$work/tmp"
export GOMAXPROCS=2 GOENV=off GOTOOLCHAIN=local CGO_ENABLED=0
export GOPROXY=off GOSUMDB=off GOFLAGS=

go version
go test -p 1 -vet=off .
go build -p 1 -trimpath -o wordcount .
result=$(printf 'RED blue red green blue red\n' | ./wordcount)
expected=$(printf 'red 3\nblue 2\ngreen 1')
test "$result" = "$expected"
printf 'GO-NATIVE: PASS compile-test-run\n'
