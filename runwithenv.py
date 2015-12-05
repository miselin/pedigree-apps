#!/usr/bin/env python

import os
import subprocess
import sys

import environment


def main():
    if len(sys.argv) == 1:
        exit(1)

    arch = sys.argv[1]
    args = None
    if arch not in ['amd64', 'arm']:
        arch = 'amd64'
        args = sys.argv[1:]
    else:
        if len(sys.argv) == 2:
            exit(1)
        args = sys.argv[2:]

    orig_env = environment.OverridableDict(os.environ)
    env = environment.generate_environment(arch, env=orig_env)

    os.execvpe(args[0], args, env)


if __name__ == '__main__':
    main()
