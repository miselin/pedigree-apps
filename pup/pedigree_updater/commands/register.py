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
import json
import logging
import os
import time
import urllib.parse

from . import base
from ..lib import http as pup_http

log = logging.getLogger(__name__)

VERIFY_ATTEMPTS = 5
VERIFY_DELAY_SECONDS = 2


class _Sha1Target:
    def __init__(self):
        self.digest = hashlib.sha1()

    def write(self, contents):
        self.digest.update(contents)
        return len(contents)


def _verify_catalog_entry(repository_url, package, digest, dependencies):
    catalog_url = f"{repository_url.rstrip('/')}/packages.pupdb"
    try:
        database = json.loads(pup_http.get_text(catalog_url, timeout=30))
    except (pup_http.RequestError, ValueError) as error:
        return "could not read the package catalog: %s" % error

    key = f"{package['name']}-{package['architecture']}"
    actual = database.get(key) if isinstance(database, dict) else None
    if not isinstance(actual, dict):
        return 'the catalog does not select package "%s"' % key

    expected = {
        "name": package["name"],
        "version": package["version"],
        "architecture": package["architecture"],
        "sha1": digest,
        "dependencies": dependencies,
    }
    actual_dependencies = actual.get("dependencies", [])
    actual = dict(actual)
    actual["dependencies"] = actual_dependencies
    mismatches = [
        field
        for field, value in expected.items()
        if actual.get(field) != value
    ]
    if mismatches:
        return "the catalog has different %s" % ", ".join(mismatches)
    return None


def _supports_dependency_metadata(repository_url):
    capabilities_url = f"{repository_url.rstrip('/')}/capabilities.json"
    try:
        capabilities = json.loads(
            pup_http.get_text(capabilities_url, timeout=30)
        )
    except (pup_http.RequestError, ValueError):
        return False
    return (
        isinstance(capabilities, dict)
        and capabilities.get("package_dependencies") == 1
    )


def _verify_archive(repository_url, filename, digest):
    archive_url = "%s/%s" % (
        repository_url.rstrip("/"),
        urllib.parse.quote(filename, safe=""),
    )
    target = _Sha1Target()
    try:
        pup_http.copy_url(archive_url, target, timeout=300)
    except pup_http.RequestError as error:
        return "could not download the published archive: %s" % error
    if target.digest.hexdigest() != digest:
        return "the published archive has a different SHA-1 digest"
    return None


def verify_upload(repository_url, package, filename, digest, dependencies):
    last_error = "repository did not expose the uploaded package"
    for attempt in range(VERIFY_ATTEMPTS):
        last_error = _verify_catalog_entry(
            repository_url, package, digest, dependencies
        )
        if last_error is None:
            last_error = _verify_archive(repository_url, filename, digest)
        if last_error is None:
            return None
        if attempt + 1 < VERIFY_ATTEMPTS:
            time.sleep(VERIFY_DELAY_SECONDS)
    return last_error


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
            help="runtime package dependencies",
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

        dependencies = list(dict.fromkeys(args.dependency))

        log.info("register package %s [%s]", package_name, package_file)

        if not config.upload_url:
            print("No upload URL is configured in the config file.")
            return 1
        if not _supports_dependency_metadata(config.upload_url):
            print(
                "The repository does not advertise package dependency "
                "metadata support; nothing was uploaded."
            )
            return 1
        url = f"{config.upload_url.rstrip('/')}/upload"

        h = hashlib.sha1()
        with open(package_file, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
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
            "dependencies": json.dumps(dependencies, separators=(",", ":")),
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

        verification_error = verify_upload(
            config.upload_url,
            {
                "name": args.package,
                "version": args.version,
                "architecture": args.architecture,
            },
            pup_filename,
            digest,
            dependencies,
        )
        if verification_error:
            print(
                f'Package "{package_name}" was uploaded, but repository '
                f"verification failed: {verification_error}."
            )
            return 1

        print(f'Package "{package_name}" has been registered and verified.')
