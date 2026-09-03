#!/usr/bin/env python3

"""Audit and migrate legacy PUP Blobstore package payloads into GCS."""

import argparse
import base64
import hashlib
import http.client
import json
import re
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


DEFAULT_PROJECT = "the-pedigree-project"
DEFAULT_BUCKET = "the-pedigree-project--pup"
DEFAULT_ORIGIN = "https://the-pedigree-project.appspot.com"
DEFAULT_WORKERS = 4
DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024
MAX_STALLED_UPLOAD_ATTEMPTS = 5
IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"
TRANSIENT_HTTP_STATUSES = {408, 429, 500, 502, 503, 504}
SHA1_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")


class MigrationError(RuntimeError):
    pass


class ApiError(MigrationError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status

    @property
    def transient(self):
        return self.status in TRANSIENT_HTTP_STATUSES


class PreconditionFailed(ApiError):
    pass


@dataclass(frozen=True)
class PackageArtifact:
    fullname: str
    sha1: str
    blob_key: str
    size: int


@dataclass(frozen=True)
class DownloadedArtifact:
    path: Path
    size: int
    sha1: str
    md5: str


@dataclass(frozen=True)
class MigrationResult:
    fullname: str
    action: str


@dataclass(frozen=True)
class DatastoreManifest:
    artifacts: tuple
    package_keys: tuple
    blob_inventory: tuple


def active_gcloud_token(gcloud="gcloud", impersonate_service_account=None):
    """Return the active gcloud access token without exposing it to output."""
    command = [gcloud, "auth", "print-access-token"]
    if impersonate_service_account:
        command.append(
            "--impersonate-service-account=" + impersonate_service_account
        )
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", "") or ""
        detail = detail.strip() or "gcloud access-token request failed"
        raise MigrationError(detail) from error
    token = result.stdout.strip()
    if not token:
        raise MigrationError("gcloud did not return an access token")
    return token


def _response_status(response):
    status = getattr(response, "status", None)
    return status if status is not None else response.getcode()


def _request_bytes(
    request,
    *,
    opener=urlopen,
    sleep=time.sleep,
    attempts=3,
    accepted=(200,),
    timeout=120,
):
    last_error = None
    for attempt in range(attempts):
        try:
            with opener(request, timeout=timeout) as response:
                status = _response_status(response)
                body = response.read()
                headers = response.headers
            if status not in accepted:
                raise ApiError(f"unexpected HTTP status {status}", status)
            return status, headers, body
        except HTTPError as error:
            if error.code in accepted:
                body = error.read()
                error.close()
                return error.code, error.headers, body
            if error.code == 412:
                error.close()
                raise PreconditionFailed("GCS create-only precondition failed", 412)
            status = error.code
            error.close()
            last_error = ApiError(f"HTTP request failed with status {status}", status)
        except (URLError, TimeoutError, ConnectionError, OSError) as error:
            last_error = ApiError(f"HTTP request failed: {error}")

        if not last_error.transient and last_error.status is not None:
            raise last_error
        if attempt + 1 < attempts:
            sleep(2**attempt)
    raise last_error


def _decode_json(body, context):
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise MigrationError(f"{context} returned invalid JSON") from error


class DatastoreClient:
    def __init__(self, project, token, *, opener=urlopen, sleep=time.sleep):
        self.project = project
        self.token = token
        self.opener = opener
        self.sleep = sleep

    def query_all(self, kind, page_size=500):
        entities = []
        cursor = None
        while True:
            query = {"kind": [{"name": kind}], "limit": page_size}
            if cursor:
                query["startCursor"] = cursor
            request = Request(
                "https://datastore.googleapis.com/v1/projects/"
                f"{quote(self.project, safe='')}:runQuery",
                data=json.dumps({"query": query}).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            _, _, body = _request_bytes(
                request,
                opener=self.opener,
                sleep=self.sleep,
                timeout=60,
            )
            result = _decode_json(body, f"Datastore {kind} query")
            batch = result.get("batch", {})
            entities.extend(
                item["entity"]
                for item in batch.get("entityResults", [])
                if "entity" in item
            )
            more = batch.get("moreResults", "NO_MORE_RESULTS")
            if more == "NO_MORE_RESULTS":
                return entities
            next_cursor = batch.get("endCursor")
            if not next_cursor or next_cursor == cursor:
                raise MigrationError(
                    f"Datastore {kind} query did not make cursor progress"
                )
            cursor = next_cursor


def _entity_identity(entity):
    path = entity.get("key", {}).get("path", [])
    if not path:
        return "<missing key>"
    key = path[-1]
    return str(key.get("name", key.get("id", "<missing id>")))


def _string_property(entity, name):
    value = entity.get("properties", {}).get(name, {})
    result = value.get("stringValue")
    return result if isinstance(result, str) else None


def _blob_key_property(entity, name="blob"):
    value = entity.get("properties", {}).get(name, {})
    for field in ("stringValue", "blobKeyValue"):
        result = value.get(field)
        if isinstance(result, str) and result:
            return result
    path = value.get("keyValue", {}).get("path", [])
    if path:
        result = path[-1].get("name", path[-1].get("id"))
        if result is not None:
            return str(result)
    return None


def _integer_property(entity, name):
    value = entity.get("properties", {}).get(name, {}).get("integerValue")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_manifest(package_entities, blob_entities):
    """Validate Datastore metadata and build an unambiguous package manifest."""
    blobs = {}
    duplicate_blob_keys = []
    for entity in blob_entities:
        key = _entity_identity(entity)
        if key in blobs:
            duplicate_blob_keys.append(key)
        blobs[key] = entity
    if duplicate_blob_keys:
        raise MigrationError(
            "duplicate __BlobInfo__ keys: " + ", ".join(sorted(set(duplicate_blob_keys)))
        )

    packages_by_name = {}
    malformed = []
    for entity in package_entities:
        fullname = _string_property(entity, "fullname")
        sha1 = _string_property(entity, "sha1")
        blob_key = _blob_key_property(entity)
        identity = _entity_identity(entity)
        if not fullname or not fullname.endswith(".pup") or "/" in fullname:
            malformed.append(f"{identity}: invalid fullname")
            continue
        if not sha1 or not SHA1_PATTERN.fullmatch(sha1):
            malformed.append(f"{identity}: invalid sha1")
            continue
        if not blob_key:
            malformed.append(f"{identity}: missing blob key")
            continue
        packages_by_name.setdefault(fullname, []).append(
            (identity, sha1.lower(), blob_key)
        )

    duplicates = []
    conflicts = []
    for fullname, records in packages_by_name.items():
        if len(records) < 2:
            continue
        signatures = {(sha1, blob_key) for _, sha1, blob_key in records}
        target = duplicates if len(signatures) == 1 else conflicts
        target.append(fullname)

    problems = list(malformed)
    if duplicates:
        problems.append("duplicate fullnames: " + ", ".join(sorted(duplicates)))
    if conflicts:
        problems.append("conflicting fullnames: " + ", ".join(sorted(conflicts)))
    if problems:
        raise MigrationError("invalid Package metadata:\n  " + "\n  ".join(problems))

    manifest = []
    for fullname, records in packages_by_name.items():
        _, sha1, blob_key = records[0]
        blob = blobs.get(blob_key)
        if blob is None:
            raise MigrationError(f"{fullname} references missing __BlobInfo__ {blob_key}")
        size = _integer_property(blob, "size")
        if size is None or size < 0:
            raise MigrationError(f"{fullname} has invalid __BlobInfo__ size")
        manifest.append(PackageArtifact(fullname, sha1, blob_key, size))
    return sorted(manifest, key=lambda artifact: artifact.fullname)


def snapshot_manifest(package_entities, blob_entities):
    """Capture payload metadata and entity identities for a stability check."""
    package_entities = list(package_entities)
    blob_entities = list(blob_entities)
    artifacts = tuple(build_manifest(package_entities, blob_entities))
    package_keys = tuple(
        sorted(
            json.dumps(entity.get("key", {}), sort_keys=True, separators=(",", ":"))
            for entity in package_entities
        )
    )
    blob_inventory = tuple(
        sorted(
            (_entity_identity(entity), _integer_property(entity, "size"))
            for entity in blob_entities
        )
    )
    return DatastoreManifest(artifacts, package_keys, blob_inventory)


def verify_manifest_stable(initial, final):
    if initial == final:
        return

    initial_artifacts = {
        artifact.fullname: artifact for artifact in initial.artifacts
    }
    final_artifacts = {artifact.fullname: artifact for artifact in final.artifacts}
    added = sorted(final_artifacts.keys() - initial_artifacts.keys())
    removed = sorted(initial_artifacts.keys() - final_artifacts.keys())
    changed = sorted(
        fullname
        for fullname in initial_artifacts.keys() & final_artifacts.keys()
        if initial_artifacts[fullname] != final_artifacts[fullname]
    )
    details = []
    if added:
        details.append("added " + ", ".join(added))
    if removed:
        details.append("removed " + ", ".join(removed))
    if changed:
        details.append("changed " + ", ".join(changed))
    if not details:
        details.append("Datastore entity identities changed")
    raise MigrationError(
        "Datastore package manifest changed during migration ("
        + "; ".join(details)
        + "); rerun the migration"
    )


def download_and_verify(
    artifact,
    origin,
    target,
    *,
    opener=urlopen,
    sleep=time.sleep,
    attempts=3,
):
    url = f"{origin.rstrip('/')}/{quote(artifact.fullname, safe='')}"
    request = Request(
        url,
        headers={
            "Accept-Encoding": "identity",
            "User-Agent": "pup-gcs-migration/1.0",
        },
    )
    last_error = None
    for attempt in range(attempts):
        try:
            with opener(request, timeout=300) as response:
                if _response_status(response) != 200:
                    raise MigrationError(
                        f"{artifact.fullname}: origin returned HTTP "
                        f"{_response_status(response)}"
                    )
                length_header = response.headers.get("Content-Length")
                if length_header is not None:
                    try:
                        content_length = int(length_header)
                    except ValueError as error:
                        raise MigrationError(
                            f"{artifact.fullname}: origin returned an invalid "
                            "Content-Length"
                        ) from error
                    if content_length != artifact.size:
                        raise MigrationError(
                            f"{artifact.fullname}: Content-Length {content_length} does "
                            f"not match __BlobInfo__ size {artifact.size}"
                        )

                sha1 = hashlib.sha1(usedforsecurity=False)
                md5 = hashlib.md5(usedforsecurity=False)
                size = 0
                with target.open("wb") as output:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)
                        sha1.update(chunk)
                        md5.update(chunk)
                        size += len(chunk)
            if size != artifact.size:
                raise MigrationError(
                    f"{artifact.fullname}: downloaded {size} bytes, expected {artifact.size}"
                )
            actual_sha1 = sha1.hexdigest()
            if actual_sha1 != artifact.sha1:
                raise MigrationError(
                    f"{artifact.fullname}: SHA-1 {actual_sha1} does not match "
                    f"Package metadata {artifact.sha1}"
                )
            return DownloadedArtifact(
                target,
                size,
                actual_sha1,
                base64.b64encode(md5.digest()).decode("ascii"),
            )
        except HTTPError as error:
            status = error.code
            error.close()
            last_error = ApiError(
                f"{artifact.fullname}: origin returned HTTP {status}", status
            )
        except (
            URLError,
            TimeoutError,
            ConnectionError,
            OSError,
            http.client.IncompleteRead,
        ) as error:
            last_error = ApiError(f"{artifact.fullname}: origin download failed: {error}")

        if not last_error.transient and last_error.status is not None:
            raise last_error
        if attempt + 1 < attempts:
            sleep(2**attempt)
    raise last_error


class GcsClient:
    def __init__(self, bucket, token, *, opener=urlopen, sleep=time.sleep):
        self.bucket = bucket
        self.token = token
        self.opener = opener
        self.sleep = sleep

    def _headers(self, extra=None):
        headers = {"Authorization": f"Bearer {self.token}"}
        headers.update(extra or {})
        return headers

    def get_metadata(self, name):
        url = (
            "https://storage.googleapis.com/storage/v1/b/"
            f"{quote(self.bucket, safe='')}/o/{quote(name, safe='')}"
        )
        request = Request(url, headers=self._headers())
        status, _, body = _request_bytes(
            request,
            opener=self.opener,
            sleep=self.sleep,
            accepted=(200, 404),
            timeout=60,
        )
        return None if status == 404 else _decode_json(body, f"GCS object {name}")

    def _begin_upload(self, artifact):
        query = urlencode(
            {
                "uploadType": "resumable",
                "name": artifact.fullname,
                "ifGenerationMatch": "0",
            }
        )
        url = (
            "https://storage.googleapis.com/upload/storage/v1/b/"
            f"{quote(self.bucket, safe='')}/o?{query}"
        )
        metadata = {
            "name": artifact.fullname,
            "contentType": "application/octet-stream",
            "cacheControl": IMMUTABLE_CACHE_CONTROL,
            "metadata": {"sha1": artifact.sha1},
        }
        request = Request(
            url,
            data=json.dumps(metadata).encode("utf-8"),
            headers=self._headers(
                {
                    "Content-Type": "application/json; charset=UTF-8",
                    "X-Upload-Content-Type": "application/octet-stream",
                    "X-Upload-Content-Length": str(artifact.size),
                }
            ),
            method="POST",
        )
        _, headers, _ = _request_bytes(
            request,
            opener=self.opener,
            sleep=self.sleep,
            accepted=(200, 201),
        )
        location = headers.get("Location")
        if not location:
            raise MigrationError(f"{artifact.fullname}: GCS omitted resumable URL")
        return location

    def _upload_request(
        self,
        location,
        data,
        content_range,
        attempts=1,
        checksum=None,
    ):
        headers = {
            "Content-Length": str(len(data)),
            "Content-Range": content_range,
            "Content-Type": "application/octet-stream",
        }
        if checksum:
            headers["X-Goog-Hash"] = f"md5={checksum}"
        request = Request(
            location,
            data=data,
            headers=self._headers(headers),
            method="PUT",
        )
        return _request_bytes(
            request,
            opener=self.opener,
            sleep=self.sleep,
            attempts=attempts,
            accepted=(200, 201, 308),
            timeout=300,
        )

    def _query_offset(self, location, total):
        status, headers, _ = self._upload_request(
            location,
            b"",
            f"bytes */{total}",
            attempts=3,
        )
        if status in (200, 201):
            return total
        acknowledged = headers.get("Range")
        if not acknowledged:
            return 0
        match = re.fullmatch(r"bytes=0-([0-9]+)", acknowledged)
        if not match:
            raise MigrationError(f"GCS returned invalid resumable Range {acknowledged!r}")
        return int(match.group(1)) + 1

    def upload(self, artifact, downloaded, chunk_size=DEFAULT_CHUNK_SIZE):
        if chunk_size <= 0 or chunk_size % (256 * 1024):
            raise ValueError("GCS chunk size must be a positive multiple of 256 KiB")
        location = self._begin_upload(artifact)
        offset = 0
        stalled_attempts = 0
        with downloaded.path.open("rb") as source:
            while offset < downloaded.size:
                previous_offset = offset
                source.seek(offset)
                data = source.read(min(chunk_size, downloaded.size - offset))
                end = offset + len(data) - 1
                try:
                    status, headers, _ = self._upload_request(
                        location,
                        data,
                        f"bytes {offset}-{end}/{downloaded.size}",
                        checksum=(
                            downloaded.md5 if end + 1 == downloaded.size else None
                        ),
                    )
                except ApiError as error:
                    if not error.transient and error.status is not None:
                        raise
                    offset = self._query_offset(location, downloaded.size)
                else:
                    if status in (200, 201):
                        offset = downloaded.size
                    else:
                        acknowledged = headers.get("Range")
                        if not acknowledged:
                            offset = self._query_offset(location, downloaded.size)
                        else:
                            match = re.fullmatch(r"bytes=0-([0-9]+)", acknowledged)
                            if not match:
                                raise MigrationError(
                                    "GCS returned invalid resumable Range "
                                    f"{acknowledged!r}"
                                )
                            offset = int(match.group(1)) + 1

                if offset < previous_offset:
                    raise MigrationError("GCS resumable upload offset moved backwards")
                if offset == previous_offset:
                    stalled_attempts += 1
                    if stalled_attempts >= MAX_STALLED_UPLOAD_ATTEMPTS:
                        raise MigrationError("GCS resumable upload made no progress")
                    self.sleep(2 ** (stalled_attempts - 1))
                else:
                    stalled_attempts = 0

        if downloaded.size == 0:
            self._upload_request(
                location,
                b"",
                "bytes */0",
                checksum=downloaded.md5,
            )


def verify_gcs_metadata(metadata, artifact, downloaded, bucket):
    problems = []
    expected = {
        "bucket": bucket,
        "name": artifact.fullname,
        "size": str(downloaded.size),
        "contentType": "application/octet-stream",
        "cacheControl": IMMUTABLE_CACHE_CONTROL,
        "md5Hash": downloaded.md5,
    }
    for field, value in expected.items():
        if metadata.get(field) != value:
            problems.append(f"{field}={metadata.get(field)!r}, expected {value!r}")
    remote_sha1 = metadata.get("metadata", {}).get("sha1")
    if remote_sha1 != downloaded.sha1:
        problems.append(f"metadata.sha1={remote_sha1!r}, expected {downloaded.sha1!r}")
    if problems:
        raise MigrationError(
            f"{artifact.fullname}: GCS metadata mismatch: " + "; ".join(problems)
        )


def migrate_one(artifact, origin, gcs, temp_dir, apply, *, opener=urlopen):
    target = Path(temp_dir) / hashlib.sha256(artifact.fullname.encode()).hexdigest()
    try:
        downloaded = download_and_verify(artifact, origin, target, opener=opener)
        metadata = gcs.get_metadata(artifact.fullname)
        if metadata is not None:
            verify_gcs_metadata(metadata, artifact, downloaded, gcs.bucket)
            return MigrationResult(artifact.fullname, "verified-existing")
        if not apply:
            return MigrationResult(artifact.fullname, "would-upload")
        action = "uploaded"
        try:
            gcs.upload(artifact, downloaded)
        except PreconditionFailed:
            # Another retry or operator may have completed the create first.
            action = "verified-existing"
        metadata = gcs.get_metadata(artifact.fullname)
        if metadata is None:
            raise MigrationError(f"{artifact.fullname}: GCS object missing after upload")
        verify_gcs_metadata(metadata, artifact, downloaded, gcs.bucket)
        return MigrationResult(artifact.fullname, action)
    finally:
        target.unlink(missing_ok=True)


def migrate_all(
    manifest,
    origin,
    gcs,
    *,
    apply=False,
    workers=DEFAULT_WORKERS,
    opener=urlopen,
    progress=None,
):
    if not 1 <= workers <= 32:
        raise ValueError("workers must be between 1 and 32")
    results = []
    failures = []
    with tempfile.TemporaryDirectory(prefix="pup-gcs-migration-") as temp_dir:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    migrate_one,
                    artifact,
                    origin,
                    gcs,
                    temp_dir,
                    apply,
                    opener=opener,
                ): artifact
                for artifact in manifest
            }
            for future in as_completed(futures):
                artifact = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    if progress:
                        progress(result)
                except Exception as error:
                    failures.append(f"{artifact.fullname}: {error}")
    if failures:
        raise MigrationError("migration failures:\n  " + "\n  ".join(sorted(failures)))
    return sorted(results, key=lambda result: result.fullname)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Audit and migrate legacy PUP package blobs into GCS."
    )
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--origin", default=DEFAULT_ORIGIN)
    parser.add_argument("--gcloud", default="gcloud")
    parser.add_argument(
        "--gcs-impersonate-service-account",
        help="use a separate, bucket-limited service account for GCS access",
    )
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="audit source and existing destination objects without writing (default)",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="create missing objects after the full Datastore preflight",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not 1 <= args.workers <= 32:
        raise SystemExit("--workers must be between 1 and 32")
    datastore_token = active_gcloud_token(args.gcloud)
    gcs_token = datastore_token
    if args.gcs_impersonate_service_account:
        gcs_token = active_gcloud_token(
            args.gcloud,
            args.gcs_impersonate_service_account,
        )
    datastore = DatastoreClient(args.project, datastore_token)
    packages = datastore.query_all("Package")
    blobs = datastore.query_all("__BlobInfo__")
    initial_manifest = snapshot_manifest(packages, blobs)
    manifest = initial_manifest.artifacts
    print(
        f"Preflight found {len(manifest)} packages and {len(blobs)} BlobInfo entities."
    )
    gcs = GcsClient(args.bucket, gcs_token)
    results = migrate_all(
        manifest,
        args.origin,
        gcs,
        apply=args.apply,
        workers=args.workers,
        progress=lambda result: print(f"{result.action}: {result.fullname}"),
    )
    final_blobs = datastore.query_all("__BlobInfo__")
    final_packages = datastore.query_all("Package")
    final_manifest = snapshot_manifest(final_packages, final_blobs)
    verify_manifest_stable(initial_manifest, final_manifest)
    counts = {
        action: sum(result.action == action for result in results)
        for action in ("uploaded", "verified-existing", "would-upload")
    }
    if args.apply:
        print(
            f"Migration complete: {len(results)} sources and destinations verified; "
            f"{counts['uploaded']} created, {counts['verified-existing']} already present."
        )
    else:
        print(
            f"Dry-run audit complete: {len(results)} sources verified; "
            f"{counts['verified-existing']} destinations verified, "
            f"{counts['would-upload']} missing."
        )


if __name__ == "__main__":
    try:
        main()
    except MigrationError as error:
        raise SystemExit(str(error)) from error
