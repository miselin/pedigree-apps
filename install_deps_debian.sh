#!/bin/bash

# Grabs a heap of packages that should cover compiling both Pedigree and every
# package in pedigree-apps

sudo apt-get install \
    build-essential libgmp3-dev libmpfr-dev scons ccache diffutils patch \
    texinfo sqlite3 genisoimage wget libSDL-dev
    
# TODO: libSDL-dev is just for sdl-config, which we should provide somewhere...

