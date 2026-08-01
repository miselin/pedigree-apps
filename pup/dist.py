import argparse
import base64
import hashlib
import os
import subprocess
import zipfile
from pathlib import Path
from urllib.parse import urljoin

import requests

DEFAULT_PROJECT = "the-pedigree-project"
DEFAULT_REPOSITORY = "https://pup.pedigree-project.org/"
REPOSITORY_HEADERS = {"User-Agent": "pup-release/1.0"}


def upload_key_from_datastore(project):
    token = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not token:
        raise RuntimeError("gcloud did not return an access token")

    query = {
        "query": {
            "kind": [{"name": "Authorisation"}],
            "filter": {
                "propertyFilter": {
                    "property": {"name": "key_name"},
                    "op": "EQUAL",
                    "value": {"stringValue": "upload"},
                }
            },
        }
    }
    response = requests.post(
        f"https://datastore.googleapis.com/v1/projects/{project}:runQuery",
        headers={"Authorization": f"Bearer {token}"},
        json=query,
        timeout=30,
    )
    response.raise_for_status()

    entities = [
        item["entity"]
        for item in response.json().get("batch", {}).get("entityResults", [])
    ]
    enabled_keys = []
    for entity in entities:
        properties = entity.get("properties", {})
        allowed = properties.get("allowed", {}).get("booleanValue", True)
        key_value = properties.get("key_value", {}).get("stringValue")
        if allowed and key_value:
            enabled_keys.append(key_value)

    if len(enabled_keys) != 1:
        raise RuntimeError(
            "expected exactly one enabled Datastore upload credential, "
            f"found {len(enabled_keys)}"
        )
    return enabled_keys[0]


def current_release(repository):
    response = requests.get(
        urljoin(repository, "pup-version"),
        headers=REPOSITORY_HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return int(response.text.strip())


def validate_wheel(wheel_path):
    if wheel_path.suffix != ".whl":
        raise ValueError(f"not a wheel file: {wheel_path}")
    if not zipfile.is_zipfile(wheel_path):
        raise ValueError(f"wheel is not a ZIP archive: {wheel_path}")
    return wheel_path.read_bytes()


def upload_wheel(repository, key, wheel_path, release):
    contents = validate_wheel(wheel_path)
    response = requests.post(
        urljoin(repository, "pup.whl"),
        headers=REPOSITORY_HEADERS,
        data={
            "version": str(release),
            "blob": base64.b64encode(contents).decode("ascii"),
            "key": "upload",
            "key_value": key,
        },
        timeout=120,
    )
    response.raise_for_status()
    if response.text.strip() != "ok":
        raise RuntimeError(f"upload failed: {response.text.strip()}")


def verify_release(repository, wheel_path, release):
    if current_release(repository) != release:
        raise RuntimeError("repository did not publish the requested release serial")

    response = requests.get(
        urljoin(repository, "pup.whl"),
        headers=REPOSITORY_HEADERS,
        timeout=120,
    )
    response.raise_for_status()
    local_digest = hashlib.sha256(wheel_path.read_bytes()).digest()
    remote_digest = hashlib.sha256(response.content).digest()
    if local_digest != remote_digest:
        raise RuntimeError("published wheel does not match the local wheel")


def parse_args():
    parser = argparse.ArgumentParser(description="Release a PUP wheel.")
    parser.add_argument("wheel", type=Path, help="wheel file to publish")
    parser.add_argument("release", type=int, help="monotonically increasing release")
    parser.add_argument(
        "--project",
        default=DEFAULT_PROJECT,
        help="GCP project containing the legacy upload credential",
    )
    parser.add_argument(
        "--repository",
        default=DEFAULT_REPOSITORY,
        help="PUP repository base URL",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.wheel.is_file():
        raise SystemExit(f"wheel does not exist: {args.wheel}")

    repository = args.repository.rstrip("/") + "/"
    published_release = current_release(repository)
    if args.release <= published_release:
        raise SystemExit(
            f"release must be newer than {published_release}; got {args.release}"
        )

    key = os.environ.get("PUP_UPLOAD_KEY")
    if key is None:
        key = upload_key_from_datastore(args.project)

    upload_wheel(repository, key, args.wheel, args.release)
    verify_release(repository, args.wheel, args.release)
    print(f"Published and verified {args.wheel.name} as PUP release {args.release}.")


if __name__ == "__main__":
    main()
