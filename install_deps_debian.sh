#!/bin/bash

# Grabs a heap of packages that should cover compiling both Pedigree and every
# package in pedigree-apps

ELEVATE=sudo
if [ $UID == 0 ]; then ELEVATE=; fi

$ELEVATE apt-get install -y \
    build-essential libmpfr4 libgmp10 libmpc3 scons ccache diffutils patch \
    texinfo sqlite3 wget libsdl1.2-dev autoconf automake groff-base \
    gtk-doc-tools python-libxml2 bison flex

# TODO: libSDL-dev is just for sdl-config, which we should provide somewhere...

# gtk-doc-tools is for pango et al (to make documentation)
# python-libxml2 needed for mesa
# flex, bison for grub2
