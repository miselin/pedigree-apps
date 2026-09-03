import hashlib
import io
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from google.api_core.exceptions import PreconditionFailed
from pup_http import gcs_mirror


class FakeBlob:
    def __init__(self, name):
        self.name = name
        self.cache_control = None
        self.chunk_size = None
        self.content_encoding = "unexpected"
        self.content_type = None
        self.metadata = None
        self.generation = None
        self.upload = None
        self.deleted_with = None

    def upload_from_file(self, source, **kwargs):
        chunks = []
        while True:
            chunk = source.read(3)
            if not chunk:
                break
            chunks.append(chunk)
        self.upload = (b"".join(chunks), kwargs)
        self.generation = 7

    def delete(self, **kwargs):
        self.deleted_with = kwargs


class FakeBucket:
    def __init__(self, existing=None, conflict=False):
        self.staging = None
        self.existing = existing
        self.conflict = conflict
        self.copy = None

    def blob(self, name):
        self.staging = FakeBlob(name)
        return self.staging

    def copy_blob(self, source, destination, **kwargs):
        self.copy = (source, destination, kwargs)
        if self.conflict:
            raise PreconditionFailed("already exists")
        return SimpleNamespace(generation=8)

    def get_blob(self, name):
        if self.existing and self.existing.name == name:
            return self.existing
        return None


class FakeClient:
    def __init__(self, bucket):
        self.requested_bucket = None
        self.result = bucket

    def bucket(self, name):
        self.requested_bucket = name
        return self.result


class MirrorTests(unittest.TestCase):
    def mirror(self, contents, expected_sha1=None, bucket=None):
        bucket = bucket or FakeBucket()
        client = FakeClient(bucket)
        upload = SimpleNamespace(size=len(contents))
        expected_sha1 = expected_sha1 or hashlib.sha1(contents).hexdigest()
        with mock.patch.object(
            gcs_mirror.blobstore,
            "BlobReader",
            return_value=io.BytesIO(contents),
        ):
            gcs_mirror.mirror_package(
                upload,
                "example-1.0-amd64.pup",
                expected_sha1,
                client=client,
                bucket_name="packages",
            )
        return client, bucket

    def test_streams_once_then_publishes_with_create_only_preconditions(self):
        contents = b"package contents"

        client, bucket = self.mirror(contents)

        self.assertEqual(client.requested_bucket, "packages")
        self.assertTrue(bucket.staging.name.startswith(".pup-incoming/"))
        self.assertEqual(bucket.staging.upload[0], contents)
        self.assertEqual(
            bucket.staging.upload[1],
            {
                "size": len(contents),
                "content_type": "application/octet-stream",
                "if_generation_match": 0,
                "checksum": "auto",
            },
        )
        self.assertEqual(
            bucket.staging.cache_control,
            "public, max-age=31536000, immutable",
        )
        self.assertEqual(bucket.staging.chunk_size, 8 * 1024 * 1024)
        self.assertEqual(bucket.staging.content_type, "application/octet-stream")
        self.assertIsNone(bucket.staging.content_encoding)
        self.assertEqual(
            bucket.staging.metadata,
            {"sha1": hashlib.sha1(contents).hexdigest()},
        )
        self.assertEqual(
            bucket.copy[2],
            {
                "new_name": "example-1.0-amd64.pup",
                "source_generation": 7,
                "if_generation_match": 0,
                "if_source_generation_match": 7,
            },
        )
        self.assertEqual(bucket.staging.deleted_with, {"if_generation_match": 7})

    def test_digest_mismatch_never_publishes_final_name(self):
        bucket = FakeBucket()

        with self.assertRaises(gcs_mirror.MirrorDigestMismatch):
            self.mirror(b"wrong contents", expected_sha1="expected", bucket=bucket)

        self.assertIsNone(bucket.copy)
        self.assertEqual(bucket.staging.deleted_with, {"if_generation_match": 7})

    def test_matching_existing_object_makes_retry_idempotent(self):
        contents = b"package contents"
        digest = hashlib.sha1(contents).hexdigest()
        existing = SimpleNamespace(
            name="example-1.0-amd64.pup",
            metadata={"sha1": digest},
            size=len(contents),
        )
        bucket = FakeBucket(existing=existing, conflict=True)

        client = FakeClient(bucket)
        upload = SimpleNamespace(size=len(contents))

        gcs_mirror.mirror_package(
            upload,
            "example-1.0-amd64.pup",
            digest,
            client=client,
            bucket_name="packages",
            verify_source=False,
        )

        self.assertIsNone(bucket.staging)

    def test_verified_retry_accepts_matching_object_after_copy_race(self):
        contents = b"package contents"
        digest = hashlib.sha1(contents).hexdigest()
        existing = SimpleNamespace(
            name="example-1.0-amd64.pup",
            metadata={"sha1": digest},
            size=len(contents),
        )
        bucket = FakeBucket(existing=existing, conflict=True)

        self.mirror(contents, bucket=bucket)

        self.assertEqual(bucket.staging.deleted_with, {"if_generation_match": 7})

    def test_different_existing_object_is_never_overwritten(self):
        contents = b"package contents"
        existing = SimpleNamespace(
            name="example-1.0-amd64.pup",
            metadata={"sha1": "different"},
            size=len(contents),
        )
        bucket = FakeBucket(existing=existing, conflict=True)

        client = FakeClient(bucket)
        upload = SimpleNamespace(size=len(contents))

        with self.assertRaises(gcs_mirror.MirrorConflict):
            gcs_mirror.mirror_package(
                upload,
                "example-1.0-amd64.pup",
                hashlib.sha1(contents).hexdigest(),
                client=client,
                bucket_name="packages",
                verify_source=False,
            )

        self.assertIsNone(bucket.staging)

    def test_bucket_configuration_is_required(self):
        with (
            mock.patch.dict("os.environ", {}, clear=True),
            self.assertRaisesRegex(
                gcs_mirror.MirrorError,
                "PUP_PACKAGE_BUCKET",
            ),
        ):
            gcs_mirror.mirror_package(
                SimpleNamespace(size=1),
                "example-1.0-amd64.pup",
                "digest",
            )


class ServiceConfigurationTests(unittest.TestCase):
    def test_worker_timeout_covers_large_package_mirroring(self):
        app_yaml = (Path(__file__).parents[1] / "app.yaml").read_text()
        self.assertIn("--timeout 600", app_yaml)


if __name__ == "__main__":
    unittest.main()
