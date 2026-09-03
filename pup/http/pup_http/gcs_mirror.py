import hashlib
import logging
import os
import uuid

from google.api_core.exceptions import PreconditionFailed
from google.appengine.ext import blobstore
from google.cloud import storage

_BUCKET_ENVIRONMENT_VARIABLE = "PUP_PACKAGE_BUCKET"
_BLOBSTORE_BUFFER_SIZE = 1024 * 1024
_GCS_UPLOAD_CHUNK_SIZE = 8 * 1024 * 1024
_IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"

logger = logging.getLogger(__name__)


class MirrorError(RuntimeError):
    pass


class MirrorConflict(MirrorError):
    pass


class MirrorDigestMismatch(MirrorError):
    pass


class DigestingReader:
    """Hash a Blobstore stream while Cloud Storage consumes it."""

    def __init__(self, source):
        self.source = source
        self.sha1 = hashlib.sha1()
        self.bytes_read = 0

    def read(self, size=-1):
        contents = self.source.read(size)
        self.sha1.update(contents)
        self.bytes_read += len(contents)
        return contents

    def tell(self):
        return self.source.tell()


def _object_matches(existing, sha1, size):
    metadata = existing.metadata or {}
    return (
        metadata.get("sha1") == sha1
        and existing.size is not None
        and int(existing.size) == size
    )


def mirror_package(
    upload,
    fullname,
    expected_sha1,
    client=None,
    bucket_name=None,
    verify_source=True,
):
    """Copy an uploaded Blobstore package to an immutable Cloud Storage name."""
    bucket_name = bucket_name or os.environ.get(_BUCKET_ENVIRONMENT_VARIABLE)
    if not bucket_name:
        raise MirrorError(
            f"{_BUCKET_ENVIRONMENT_VARIABLE} is required for package uploads"
        )

    size = int(upload.size)
    client = client or storage.Client()
    bucket = client.bucket(bucket_name)

    if not verify_source:
        existing = bucket.get_blob(fullname)
        if existing:
            if _object_matches(existing, expected_sha1, size):
                return
            raise MirrorConflict(
                f"Cloud Storage object {fullname} already has different contents"
            )

    staging = bucket.blob(f".pup-incoming/{uuid.uuid4().hex}")
    staging.cache_control = _IMMUTABLE_CACHE_CONTROL
    staging.chunk_size = _GCS_UPLOAD_CHUNK_SIZE
    staging.content_encoding = None
    staging.content_type = "application/octet-stream"
    staging.metadata = {"sha1": expected_sha1}
    staging_uploaded = False

    try:
        with blobstore.BlobReader(
            upload,
            buffer_size=_BLOBSTORE_BUFFER_SIZE,
        ) as source:
            digesting_source = DigestingReader(source)
            staging.upload_from_file(
                digesting_source,
                size=size,
                content_type="application/octet-stream",
                if_generation_match=0,
                checksum="auto",
            )
        staging_uploaded = True

        actual_sha1 = digesting_source.sha1.hexdigest()
        if digesting_source.bytes_read != size or actual_sha1 != expected_sha1:
            raise MirrorDigestMismatch(
                f"uploaded package SHA-1 is {actual_sha1}, expected {expected_sha1}"
            )

        try:
            bucket.copy_blob(
                staging,
                bucket,
                new_name=fullname,
                source_generation=staging.generation,
                if_generation_match=0,
                if_source_generation_match=staging.generation,
            )
        except PreconditionFailed as error:
            existing = bucket.get_blob(fullname)
            if not existing or not _object_matches(existing, expected_sha1, size):
                raise MirrorConflict(
                    f"Cloud Storage object {fullname} already has different contents"
                ) from error
    finally:
        if staging_uploaded:
            try:
                staging.delete(if_generation_match=staging.generation)
            except Exception:
                # A lifecycle rule is the final guard for abandoned staging objects.
                logger.exception("failed to delete package mirror staging object")
