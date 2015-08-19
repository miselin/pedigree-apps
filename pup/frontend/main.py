#!/usr/bin/env python
'''
PUP: Pedigree UPdater

Copyright (c) 2015 Matthew Iselin

Permission to use, copy, modify, and distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
'''

import argparse
import logging
import os
import sys

from pup.commands import base
from pup.lib import schema
from pup.lib import util


log = logging.getLogger()


def main():
    cmds = [klass() for klass in base.PupCommand.__subclasses__()]
    cmds = {k.name(): k for k in cmds}

    parser = argparse.ArgumentParser(description='The Pedigree UPdater.')
    parser.add_argument('--config', type=str, help='path to config file.')

    subparsers = parser.add_subparsers(title='pup commands', dest='which')
    for cmd in cmds.values():
        if cmd.name() is None:
            continue

        group = subparsers.add_parser(cmd.name(), help=cmd.help())
        cmd.add_arguments(group)

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    if not args.which:
        parser.print_help()
        exit(1)

    config = util.load_config(args)

    # Perform schema upgrade if needed.
    pup_schema = schema.PupSchema(config.db)
    pup_schema.upgrade()

    cmd = cmds[args.which]
    if cmd.run(args, config):
        exit(1)


if __name__ == '__main__':
    main()
