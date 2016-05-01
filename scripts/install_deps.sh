#!/bin/bash

# Script to install dependencies for standalone, which doesn't need to care
# about building disk images.

sudo apt-get install -y scons python-requests libmpfr4 libgmp10 libmpc3
