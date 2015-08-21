#!/bin/bash

# Usage: ./run_pup.sh ...
PYTHONPATH=./pup:$PYTHONPATH ./pup/pedigree_updater/frontend/main.py $*

