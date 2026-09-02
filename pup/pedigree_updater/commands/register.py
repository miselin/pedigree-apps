#!/usr/bin/env python3
"""
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
"""

import hashlib
import logging
import os

from . import base
from ..lib import http as pup_http

log = logging.getLogger(__name__)


class RegisterPackageCommand(base.PupCommand):
    def name(self):
        return "register"

    def help(self):
        return "register packages"

    def add_arguments(self, parser):
        parser.add_argument(
            "--package", type=str, required=True, help="name of the package to register"
        )
        parser.add_argument(
            "--version",
            type=str,
            required=True,
            help="version of the package to register",
        )
        parser.add_argument(
            "--architecture",
            type=str,
            required=True,
            choices=("amd64", "arm"),
            help="architecture of the package to register",
        )
        parser.add_argument(
            "--key",
            type=str,
            default=os.environ.get("PUP_UPLOAD_KEY"),
            help="upload key for the repository (or set PUP_UPLOAD_KEY)",
        )
        parser.add_argument(
            "dependency",
            nargs="*",
            type=str,
            help="reserved; legacy repository dependency storage is unavailable",
        )

    def run(self, args, config):
        package_name = f"{args.package}-{args.version}-{args.architecture}"
        pup_filename = f"{package_name}.pup"
        package_file = os.path.join(config.local_cache, pup_filename)
        if not os.path.isfile(package_file):
            print(f"No file exists for package {package_file}.")
            return 1

        if not args.key:
            print("No upload key was provided.")
            return 1
        if args.dependency:
            print("The legacy repository cannot record runtime dependencies.")
            return 1

        log.info("register package %s [%s]", package_name, package_file)

        if not config.upload_url:
            print("No upload URL is configured in the config file.")
            return 1
        url = f"{config.upload_url}/upload"

        h = hashlib.sha1()
        with open(package_file, "rb") as f:
            h.update(f.read())
        digest = h.hexdigest()

        get_params = {
            "key": "upload",
            "key_value": args.key,
        }

        # Obtain an upload URL.
        try:
            upload_url = pup_http.get_text(
                url,
                parameters=get_params,
                timeout=30,
            ).strip()
        except pup_http.RequestError:
            print("Failed to get upload URL.")
            return 1
        if not upload_url:
            print("Failed to get upload URL.")
            return 1

        # Upload the package to the given upload URL.
        postdata = {
            "name": args.package,
            "vers": args.version,
            "arch": args.architecture,
            "sha1": digest,
        }
        try:
            result = pup_http.post_multipart(
                upload_url,
                postdata,
                "file",
                package_file,
                timeout=300,
            ).strip()
        except pup_http.RequestError:
            print(f'Registering package "{package_name}" failed.')
            return 1

        if result != "ok":
            print(f'Registering package "{package_name}" failed: {result}')
            return 1
        else:
            print(f'Package "{package_name}" has been registered.')
