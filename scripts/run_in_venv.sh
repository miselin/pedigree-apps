#!/bin/bash

GIT_ROOT=$(git rev-parse --show-toplevel)

echo "sourcing virtualenv" >&2

source "$GIT_ROOT/venv/bin/activate"

echo "running $*" >&2

echo $VIRTUAL_ENV >&2

$*
