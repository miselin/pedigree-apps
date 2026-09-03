import base64
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from urllib.error import HTTPError

from scripts import migrate_package_blobs as migration


class Response(io.BytesIO):
    def __init__(self, body=b"", status=200, headers=None):
        super().__init__(body)
        self.status = status
        self.headers = headers or {}

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def package_entity(identity, fullname, sha1, blob_key):
    return {
        "key": {"path": [{"kind": "Package", "id": identity}]},
        "properties": {
            "fullname": {"stringValue": fullname},
            "sha1": {"stringValue": sha1},
            "blob": {"stringValue": blob_key},
        },
    }


def blob_entity(blob_key, size):
    return {
        "key": {"path": [{"kind": "__BlobInfo__", "name": blob_key}]},
        "properties": {"size": {"integerValue": str(size)}},
    }


def object_metadata(artifact, contents, bucket="test-bucket"):
    return {
        "bucket": bucket,
        "name": artifact.fullname,
        "size": str(len(contents)),
        "contentType": "application/octet-stream",
        "cacheControl": migration.IMMUTABLE_CACHE_CONTROL,
        "md5Hash": base64.b64encode(
            hashlib.md5(contents, usedforsecurity=False).digest()
        ).decode("ascii"),
        "metadata": {"sha1": hashlib.sha1(contents).hexdigest()},
    }


class ManifestTest(unittest.TestCase):
    def test_builds_manifest_from_package_and_blob_info(self):
        contents = b"package"
        sha1 = hashlib.sha1(contents).hexdigest()
        manifest = migration.build_manifest(
            [package_entity(1, "demo-1-amd64.pup", sha1, "blob-one")],
            [blob_entity("blob-one", len(contents)), blob_entity("orphan", 99)],
        )

        self.assertEqual(
            manifest,
            [migration.PackageArtifact("demo-1-amd64.pup", sha1, "blob-one", 7)],
        )

    def test_rejects_duplicate_and_conflicting_fullnames(self):
        sha1 = "a" * 40
        packages = [
            package_entity(1, "duplicate-1-amd64.pup", sha1, "same"),
            package_entity(2, "duplicate-1-amd64.pup", sha1, "same"),
            package_entity(3, "conflict-1-amd64.pup", sha1, "one"),
            package_entity(4, "conflict-1-amd64.pup", "b" * 40, "two"),
        ]

        with self.assertRaises(migration.MigrationError) as raised:
            migration.build_manifest(packages, [])

        self.assertIn("duplicate fullnames: duplicate-1-amd64.pup", str(raised.exception))
        self.assertIn("conflicting fullnames: conflict-1-amd64.pup", str(raised.exception))

    def test_rejects_missing_blob_info(self):
        package = package_entity(1, "demo-1-amd64.pup", "a" * 40, "missing")
        with self.assertRaisesRegex(migration.MigrationError, "missing __BlobInfo__"):
            migration.build_manifest([package], [])

    def test_final_snapshot_rejects_package_published_during_migration(self):
        initial_package = package_entity(
            1, "initial-1-amd64.pup", "a" * 40, "initial-blob"
        )
        added_package = package_entity(
            2, "added-1-amd64.pup", "b" * 40, "added-blob"
        )
        initial = migration.snapshot_manifest(
            [initial_package], [blob_entity("initial-blob", 10)]
        )
        final = migration.snapshot_manifest(
            [initial_package, added_package],
            [blob_entity("initial-blob", 10), blob_entity("added-blob", 20)],
        )

        with self.assertRaisesRegex(
            migration.MigrationError,
            r"added added-1-amd64\.pup.*rerun",
        ):
            migration.verify_manifest_stable(initial, final)

    def test_final_snapshot_accepts_same_entities_in_a_different_order(self):
        packages = [
            package_entity(1, "one-1-amd64.pup", "a" * 40, "one-blob"),
            package_entity(2, "two-1-amd64.pup", "b" * 40, "two-blob"),
        ]
        blobs = [blob_entity("one-blob", 10), blob_entity("two-blob", 20)]
        initial = migration.snapshot_manifest(packages, blobs)
        final = migration.snapshot_manifest(reversed(packages), reversed(blobs))

        migration.verify_manifest_stable(initial, final)


class DatastoreClientTest(unittest.TestCase):
    def test_query_follows_end_cursor(self):
        requests = []
        responses = iter(
            [
                {
                    "batch": {
                        "entityResults": [{"entity": {"key": {"path": []}}}],
                        "moreResults": "NOT_FINISHED",
                        "endCursor": "next-page",
                    }
                },
                {"batch": {"entityResults": [], "moreResults": "NO_MORE_RESULTS"}},
            ]
        )

        def opener(request, timeout):
            requests.append(json.loads(request.data))
            return Response(json.dumps(next(responses)).encode())

        client = migration.DatastoreClient(
            "test-project", "secret-token", opener=opener, sleep=lambda _delay: None
        )
        entities = client.query_all("Package")

        self.assertEqual(len(entities), 1)
        self.assertNotIn("startCursor", requests[0]["query"])
        self.assertEqual(requests[1]["query"]["startCursor"], "next-page")


class DownloadTest(unittest.TestCase):
    def test_downloads_exact_origin_path_and_verifies_both_metadata_checks(self):
        contents = b"verified package bytes"
        artifact = migration.PackageArtifact(
            "demo-1-amd64.pup",
            hashlib.sha1(contents).hexdigest(),
            "blob",
            len(contents),
        )
        seen = []

        def opener(request, timeout):
            seen.append((request.full_url, request.get_header("Accept-encoding")))
            return Response(contents, headers={"Content-Length": str(len(contents))})

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "payload"
            downloaded = migration.download_and_verify(
                artifact, "https://origin.example", target, opener=opener
            )

        self.assertEqual(
            seen, [("https://origin.example/demo-1-amd64.pup", "identity")]
        )
        self.assertEqual(downloaded.size, len(contents))
        self.assertEqual(downloaded.sha1, artifact.sha1)

    def test_rejects_content_length_before_accepting_payload(self):
        contents = b"package"
        artifact = migration.PackageArtifact(
            "demo-1-amd64.pup", hashlib.sha1(contents).hexdigest(), "blob", 99
        )
        opener = lambda request, timeout: Response(
            contents, headers={"Content-Length": str(len(contents))}
        )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(migration.MigrationError, "Content-Length"):
                migration.download_and_verify(
                    artifact, "https://origin.example", Path(directory) / "payload", opener=opener
                )


class GcsClientTest(unittest.TestCase):
    def test_resumable_upload_is_create_only_and_resumes_after_transient_error(self):
        contents = b"x" * (512 * 1024)
        artifact = migration.PackageArtifact(
            "demo-1-amd64.pup", hashlib.sha1(contents).hexdigest(), "blob", len(contents)
        )
        calls = []
        data_puts = 0

        def opener(request, timeout):
            nonlocal data_puts
            calls.append(request)
            if request.method == "POST":
                return Response(headers={"Location": "https://upload.example/session"})
            content_range = request.get_header("Content-range")
            if content_range == f"bytes */{len(contents)}":
                return Response(status=308, headers={"Range": "bytes=0-262143"})
            data_puts += 1
            if data_puts == 1:
                raise HTTPError(request.full_url, 503, "retry", {}, io.BytesIO())
            return Response(b"{}", status=200)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload"
            path.write_bytes(contents)
            downloaded = migration.DownloadedArtifact(
                path,
                len(contents),
                artifact.sha1,
                base64.b64encode(
                    hashlib.md5(contents, usedforsecurity=False).digest()
                ).decode("ascii"),
            )
            client = migration.GcsClient(
                "test-bucket", "secret", opener=opener, sleep=lambda _delay: None
            )
            client.upload(artifact, downloaded, chunk_size=256 * 1024)

        initiation = calls[0]
        self.assertIn("uploadType=resumable", initiation.full_url)
        self.assertIn("ifGenerationMatch=0", initiation.full_url)
        sent_metadata = json.loads(initiation.data)
        self.assertEqual(sent_metadata["metadata"]["sha1"], artifact.sha1)
        self.assertEqual(sent_metadata["cacheControl"], migration.IMMUTABLE_CACHE_CONTROL)
        self.assertEqual(
            calls[-1].get_header("Content-range"),
            f"bytes 262144-524287/{len(contents)}",
        )
        self.assertEqual(
            calls[-1].get_header("X-goog-hash"),
            "md5="
            + base64.b64encode(
                hashlib.md5(contents, usedforsecurity=False).digest()
            ).decode("ascii"),
        )

    def test_resumable_upload_bounds_retries_without_progress(self):
        contents = b"x"
        artifact = migration.PackageArtifact(
            "demo-1-amd64.pup",
            hashlib.sha1(contents).hexdigest(),
            "blob",
            len(contents),
        )
        data_attempts = 0

        def opener(request, timeout):
            nonlocal data_attempts
            if request.method == "POST":
                return Response(headers={"Location": "https://upload.example/session"})
            if request.get_header("Content-range") == "bytes */1":
                return Response(status=308)
            data_attempts += 1
            raise HTTPError(request.full_url, 503, "retry", {}, io.BytesIO())

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload"
            path.write_bytes(contents)
            downloaded = migration.DownloadedArtifact(
                path,
                1,
                artifact.sha1,
                base64.b64encode(
                    hashlib.md5(contents, usedforsecurity=False).digest()
                ).decode("ascii"),
            )
            client = migration.GcsClient(
                "test-bucket", "secret", opener=opener, sleep=lambda _delay: None
            )
            with self.assertRaisesRegex(migration.MigrationError, "made no progress"):
                client.upload(artifact, downloaded)

        self.assertEqual(data_attempts, migration.MAX_STALLED_UPLOAD_ATTEMPTS)

    def test_metadata_verification_rejects_wrong_object(self):
        contents = b"package"
        artifact = migration.PackageArtifact(
            "demo-1-amd64.pup", hashlib.sha1(contents).hexdigest(), "blob", len(contents)
        )
        downloaded = migration.DownloadedArtifact(
            Path("unused"), len(contents), artifact.sha1, "wrong-md5"
        )
        metadata = object_metadata(artifact, contents)

        with self.assertRaisesRegex(migration.MigrationError, "md5Hash"):
            migration.verify_gcs_metadata(metadata, artifact, downloaded, "test-bucket")


class MigrationTest(unittest.TestCase):
    def test_dry_run_never_uploads(self):
        contents = b"package"
        artifact = migration.PackageArtifact(
            "demo-1-amd64.pup", hashlib.sha1(contents).hexdigest(), "blob", len(contents)
        )

        class FakeGcs:
            bucket = "test-bucket"

            def get_metadata(self, _name):
                return None

            def upload(self, *_args):
                raise AssertionError("dry run attempted an upload")

        opener = lambda request, timeout: Response(
            contents, headers={"Content-Length": str(len(contents))}
        )
        results = migration.migrate_all(
            [artifact],
            "https://origin.example",
            FakeGcs(),
            apply=False,
            workers=1,
            opener=opener,
        )
        self.assertEqual(results[0].action, "would-upload")

    def test_apply_verifies_metadata_after_upload(self):
        contents = b"package"
        artifact = migration.PackageArtifact(
            "demo-1-amd64.pup", hashlib.sha1(contents).hexdigest(), "blob", len(contents)
        )

        class FakeGcs:
            bucket = "test-bucket"

            def __init__(self):
                self.metadata = None
                self.uploads = 0

            def get_metadata(self, _name):
                return self.metadata

            def upload(self, uploaded_artifact, _downloaded):
                self.uploads += 1
                self.metadata = object_metadata(uploaded_artifact, contents)

        gcs = FakeGcs()
        opener = lambda request, timeout: Response(
            contents, headers={"Content-Length": str(len(contents))}
        )
        results = migration.migrate_all(
            [artifact],
            "https://origin.example",
            gcs,
            apply=True,
            workers=1,
            opener=opener,
        )
        self.assertEqual(gcs.uploads, 1)
        self.assertEqual(results[0].action, "uploaded")

    def test_default_mode_is_dry_run(self):
        self.assertFalse(migration.parse_args([]).apply)
        self.assertTrue(migration.parse_args(["--apply"]).apply)

    def test_access_token_is_captured_not_printed(self):
        with mock.patch.object(
            migration.subprocess,
            "run",
            return_value=SimpleNamespace(stdout="secret-token\n"),
        ) as run, mock.patch("sys.stdout", new_callable=io.StringIO) as output:
            token = migration.active_gcloud_token("custom-gcloud")

        self.assertEqual(token, "secret-token")
        self.assertEqual(output.getvalue(), "")
        self.assertTrue(run.call_args.kwargs["capture_output"])

    def test_main_requeries_manifest_after_migration(self):
        contents = b"package"
        package = package_entity(
            1,
            "demo-1-amd64.pup",
            hashlib.sha1(contents).hexdigest(),
            "blob",
        )
        blob = blob_entity("blob", len(contents))
        events = []

        class FakeDatastore:
            def query_all(self, kind):
                events.append(f"query-{kind}")
                return [package] if kind == "Package" else [blob]

        with (
            mock.patch.object(migration, "active_gcloud_token", return_value="token"),
            mock.patch.object(migration, "DatastoreClient", return_value=FakeDatastore()),
            mock.patch.object(
                migration,
                "GcsClient",
                return_value=SimpleNamespace(bucket="test-bucket"),
            ),
            mock.patch.object(
                migration,
                "migrate_all",
                side_effect=lambda *_args, **_kwargs: events.append("migrate") or [],
            ),
            mock.patch("sys.stdout", new_callable=io.StringIO),
        ):
            migration.main(["--workers", "1"])

        self.assertEqual(
            events,
            [
                "query-Package",
                "query-__BlobInfo__",
                "migrate",
                "query-__BlobInfo__",
                "query-Package",
            ],
        )


if __name__ == "__main__":
    unittest.main()
