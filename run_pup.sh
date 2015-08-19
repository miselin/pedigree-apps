#!/bin/bash

# Usage: ./run_pup.sh ...
PYTHONPATH=./pup:$PYTHONPATH ./pup/frontend/main.py $*

