#!/bin/bash

# Grabs a heap of packages that should cover compiling both Pedigree and every
# package in pedigree-apps

ELEVATE=sudo
if [ $UID == 0 ]; then ELEVATE=; fi

$ELEVATE apt-get install -y \
    build-essential libgmp3-dev libmpfr-dev scons ccache diffutils patch \
    texinfo sqlite3 genisoimage wget libsdl1.2-dev autoconf automake

# TODO: libSDL-dev is just for sdl-config, which we should provide somewhere...

