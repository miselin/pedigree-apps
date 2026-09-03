import base64
import json
import unittest
from types import SimpleNamespace
from unittest import mock

from pup_http import views

_MISSING = object()


class QueryResult:
    def __init__(self, items=(), result=None):
        self.items = list(items)
        self.result = result

    def __iter__(self):
        return iter(self.items)

    def iter(self):
        return iter(self.items)

    def fetch(self, _limit):
        return list(self.items)

    def get(self):
        return self.result

    def order(self, _order):
        return self


def package(
    name,
    architecture,
    version,
    sha1="digest",
    uploaded_at=None,
    dependencies=_MISSING,
):
    result = SimpleNamespace(
        package_name=name,
        architecture=architecture,
        version=version,
        sha1=sha1,
        fullname=f"{name}-{version}-{architecture}.pup",
        uploaded_at=uploaded_at,
    )
    if dependencies is not _MISSING:
        result.dependencies = dependencies
    return result


class VersionTests(unittest.TestCase):
    def test_numeric_versions_are_compared_by_component(self):
        self.assertGreater(views.version_cmp("1.10", "1.9"), 0)
        self.assertEqual(views.version_cmp("1.2", "1.2.0"), 0)

    def test_sqlite_compact_versions_are_compared_as_grouped_components(self):
        self.assertGreater(
            views.version_cmp("3.53.4", "3090200", package_name="sqlite"),
            0,
        )
        self.assertEqual(
            views.version_cmp("3.53.4", "3530400", package_name="sqlite"),
            0,
        )

    def test_legacy_suffix_versions_use_natural_component_order(self):
        comparisons = (
            ("9.20.13", "9.10.2-P3"),
            ("2.9.2", "2.8.8rel.2"),
            ("3.5.3", "1.0.1g"),
            ("1.0.1h", "1.0.1g"),
        )
        for current, historical in comparisons:
            with self.subTest(current=current, historical=historical):
                self.assertGreater(views.version_cmp(current, historical), 0)

    def test_arbitrary_legacy_versions_do_not_raise(self):
        result = views.version_cmp("release-next", "release-old")

        self.assertIsInstance(result, int)

    def test_dedup_keeps_latest_per_architecture(self):
        packages = [
            package("zlib", "amd64", "1.9"),
            package("zlib", "amd64", "1.10"),
            package("zlib", "arm", "1.2"),
            package("bash", "amd64", "4.1"),
        ]

        result = views.dedup_packages(packages)

        self.assertEqual(
            [(item.package_name, item.architecture, item.version) for item in result],
            [
                ("bash", "amd64", "4.1"),
                ("zlib", "amd64", "1.10"),
                ("zlib", "arm", "1.2"),
            ],
        )

    def test_dedup_uses_package_specific_sqlite_comparison(self):
        packages = [
            package("sqlite", "amd64", "3090200"),
            package("sqlite", "amd64", "3.53.4"),
        ]

        self.assertEqual(views.dedup_packages(packages)[0].version, "3.53.4")


class DependencyTests(unittest.TestCase):
    def test_json_dependencies_are_normalised_without_reordering(self):
        self.assertEqual(
            views.parse_uploaded_dependencies('["zlib", " ca-certificates ", "zlib"]'),
            ["zlib", "ca-certificates"],
        )

    def test_missing_dependency_metadata_is_distinct_from_an_empty_list(self):
        self.assertIsNone(views.parse_uploaded_dependencies(None))
        self.assertEqual(views.parse_uploaded_dependencies("[]"), [])

    def test_malformed_dependency_metadata_is_rejected(self):
        invalid_values = (
            "not-json",
            '"zlib"',
            '["zlib", 3]',
            '["../zlib"]',
            json.dumps(["dep"] * 257),
        )
        for value in invalid_values:
            with self.subTest(value=value[:40]):
                with self.assertRaises(ValueError):
                    views.parse_uploaded_dependencies(value)

    def test_legacy_datastore_dependency_strings_remain_readable(self):
        stored_package = package(
            "example",
            "amd64",
            "1.0",
            dependencies="zlib, ca-certificates,zlib",
        )

        self.assertEqual(
            views.package_dependencies(stored_package),
            ["zlib", "ca-certificates"],
        )


class RouteTests(unittest.TestCase):
    def setUp(self):
        views.flask_app.config.update(TESTING=True)
        self.client = views.flask_app.test_client()

    def test_catalog_contract(self):
        packages = [
            package("zlib", "amd64", "1.9", sha1="old"),
            package(
                "zlib",
                "amd64",
                "1.10",
                sha1="new",
                dependencies=["ca-certificates"],
            ),
        ]
        with mock.patch.object(
            views.Package,
            "query",
            return_value=QueryResult(items=packages),
        ):
            response = self.client.get("/packages.pupdb")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(
            json.loads(response.data),
            {
                "zlib-amd64": {
                    "architecture": "amd64",
                    "version": "1.10",
                    "name": "zlib",
                    "sha1": "new",
                    "dependencies": ["ca-certificates"],
                }
            },
        )

    def test_catalog_emits_empty_dependencies_for_legacy_entities(self):
        stored_package = package("zlib", "amd64", "1.2.8")
        with mock.patch.object(
            views.Package,
            "query",
            return_value=QueryResult(items=[stored_package]),
        ):
            response = self.client.get("/packages.pupdb")

        self.assertEqual(
            json.loads(response.data)["zlib-amd64"]["dependencies"],
            [],
        )

    def test_capabilities_advertise_dependency_aware_catalog(self):
        response = self.client.get("/capabilities.json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(
            json.loads(response.data),
            {
                "package_database": 1,
                "package_dependencies": 1,
            },
        )

    def test_index_keeps_existing_template(self):
        packages = [package("zlib", "amd64", "1.2.8")]
        package_queries = [
            QueryResult(items=[SimpleNamespace(architecture="amd64")]),
            QueryResult(items=packages),
        ]
        dependency_query = QueryResult(items=[SimpleNamespace(deps_arch="amd64")])

        with (
            mock.patch.object(
                views.Package,
                "query",
                side_effect=package_queries,
            ),
            mock.patch.object(
                views.DepsModel,
                "query",
                return_value=dependency_query,
            ),
        ):
            response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"The Pedigree UPdater", response.data)
        self.assertIn(b"zlib-1.2.8-amd64.pup", response.data)
        self.assertIn(b"deps-amd64.svg", response.data)

    def test_index_filename_alias_is_preserved(self):
        package_queries = [
            QueryResult(items=[]),
            QueryResult(items=[]),
        ]
        with (
            mock.patch.object(
                views.Package,
                "query",
                side_effect=package_queries,
            ),
            mock.patch.object(
                views.DepsModel,
                "query",
                return_value=QueryResult(items=[]),
            ),
        ):
            response = self.client.get("/index.html")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"The Pedigree UPdater", response.data)

    def test_current_wheel_and_release_are_served_unchanged(self):
        latest = SimpleNamespace(pup_version=9, pup_contents=b"wheel bytes")
        query = QueryResult(result=latest)
        with mock.patch.object(views.PupModel, "query", return_value=query):
            version_response = self.client.get("/pup-version")
            wheel_response = self.client.get("/pup.whl")

        self.assertEqual(version_response.data, b"9")
        self.assertEqual(version_response.content_type, "text/plain")
        self.assertEqual(wheel_response.data, b"wheel bytes")
        self.assertEqual(wheel_response.content_type, "application/octet-stream")

    def test_package_download_uses_blobstore_response_header(self):
        stored_package = SimpleNamespace(blob="blob-key")
        blob_info = object()
        query = QueryResult(result=stored_package)
        with (
            mock.patch.object(views.Package, "query", return_value=query),
            mock.patch.object(views.blobstore, "get", return_value=blob_info),
            mock.patch.object(
                views.blobstore.BlobstoreDownloadHandler,
                "send_blob",
                return_value={"X-AppEngine-BlobKey": "blob-key"},
            ),
        ):
            response = self.client.get("/zlib-1.2.8-amd64.pup")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-AppEngine-BlobKey"], "blob-key")
        self.assertEqual(response.content_type, "application/octet-stream")

    def test_dependency_graph_route_wins_over_package_fallback(self):
        dependency = SimpleNamespace(deps_contents=b"<svg></svg>")
        query = QueryResult(result=dependency)
        with mock.patch.object(views.DepsModel, "query", return_value=query):
            response = self.client.get("/deps-amd64.svg")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "image/svg+xml")
        self.assertEqual(response.data, b"<svg></svg>")

    def test_upload_routes_reject_missing_credentials(self):
        self.assertEqual(self.client.get("/upload").status_code, 403)
        self.assertEqual(self.client.post("/pup.whl").status_code, 403)
        self.assertEqual(self.client.post("/deps-amd64.svg").status_code, 403)

    def test_authenticated_package_upload_url_is_preserved(self):
        credential = SimpleNamespace(key_value="secret", allowed=True)
        query = QueryResult(result=credential)
        with (
            mock.patch.object(views.Authorisation, "query", return_value=query),
            mock.patch.object(
                views.blobstore,
                "create_upload_url",
                return_value="https://upload.example/blobstore",
            ) as create_upload_url,
        ):
            response = self.client.get(
                "/upload",
                query_string={"key": "upload", "key_value": "secret"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"https://upload.example/blobstore")
        create_upload_url.assert_called_once_with("/blobstore")

    def test_package_upload_callback_preserves_package_schema(self):
        uploaded = SimpleNamespace(key=lambda: "new-blob-key")
        package_model = mock.MagicMock()
        package_model.query.return_value = QueryResult(result=None)
        created = package_model.return_value

        with (
            mock.patch.object(views, "Package", package_model),
            mock.patch.object(
                views.blobstore.BlobstoreUploadHandler,
                "get_uploads",
                return_value=[uploaded],
            ),
        ):
            response = self.client.post(
                "/blobstore",
                data={
                    "name": "zlib",
                    "arch": "amd64",
                    "vers": "1.2.8",
                    "sha1": "digest",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"ok")
        package_model.assert_called_once_with(
            fullname="zlib-1.2.8-amd64.pup",
            package_name="zlib",
            architecture="amd64",
            version="1.2.8",
            sha1="digest",
            dependencies=[],
            blob="new-blob-key",
        )
        created.put.assert_called_once_with()

    def test_package_upload_stores_dependency_order(self):
        uploaded = SimpleNamespace(key=lambda: "new-blob-key")
        package_model = mock.MagicMock()
        package_model.query.return_value = QueryResult(result=None)

        with (
            mock.patch.object(views, "Package", package_model),
            mock.patch.object(
                views.blobstore.BlobstoreUploadHandler,
                "get_uploads",
                return_value=[uploaded],
            ),
        ):
            response = self.client.post(
                "/blobstore",
                data={
                    "name": "example",
                    "arch": "amd64",
                    "vers": "1.0",
                    "sha1": "digest",
                    "dependencies": '["zlib", "ca-certificates"]',
                },
            )

        self.assertEqual(response.status_code, 200)
        package_model.assert_called_once_with(
            fullname="example-1.0-amd64.pup",
            package_name="example",
            architecture="amd64",
            version="1.0",
            sha1="digest",
            dependencies=["zlib", "ca-certificates"],
            blob="new-blob-key",
        )

    def test_idempotent_upload_discards_new_blob(self):
        uploaded = SimpleNamespace(key=lambda: "new-blob-key")
        new_blob = mock.Mock()
        known_package = package(
            "example",
            "amd64",
            "1.0",
            sha1="digest",
            dependencies=["zlib"],
        )

        with (
            mock.patch.object(
                views.Package,
                "query",
                return_value=QueryResult(result=known_package),
            ),
            mock.patch.object(
                views.blobstore.BlobstoreUploadHandler,
                "get_uploads",
                return_value=[uploaded],
            ),
            mock.patch.object(
                views.blobstore,
                "get",
                return_value=new_blob,
            ) as get_blob,
        ):
            response = self.client.post(
                "/blobstore",
                data={
                    "name": "example",
                    "arch": "amd64",
                    "vers": "1.0",
                    "sha1": "digest",
                    "dependencies": '["zlib"]',
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"ok")
        get_blob.assert_called_once_with("new-blob-key")
        new_blob.delete.assert_called_once_with()

    def test_legacy_idempotent_upload_preserves_known_dependencies(self):
        uploaded = SimpleNamespace(key=lambda: "new-blob-key")
        new_blob = mock.Mock()
        known_package = package(
            "example",
            "amd64",
            "1.0",
            sha1="digest",
            dependencies=["zlib"],
        )

        with (
            mock.patch.object(
                views.Package,
                "query",
                return_value=QueryResult(result=known_package),
            ),
            mock.patch.object(
                views.blobstore.BlobstoreUploadHandler,
                "get_uploads",
                return_value=[uploaded],
            ),
            mock.patch.object(views.blobstore, "get", return_value=new_blob),
        ):
            response = self.client.post(
                "/blobstore",
                data={
                    "name": "example",
                    "arch": "amd64",
                    "vers": "1.0",
                    "sha1": "digest",
                },
            )

        self.assertEqual(response.status_code, 200)
        new_blob.delete.assert_called_once_with()

    def test_conflicting_upload_preserves_published_version(self):
        known_package = package(
            "example",
            "amd64",
            "1.0",
            sha1="published-digest",
            dependencies=["zlib"],
        )
        conflicts = (
            ("different-digest", '["zlib"]'),
            ("published-digest", '["libffi"]'),
        )

        for digest, dependencies in conflicts:
            with self.subTest(digest=digest, dependencies=dependencies):
                uploaded = SimpleNamespace(key=lambda: "rejected-blob-key")
                rejected_blob = mock.Mock()
                with (
                    mock.patch.object(
                        views.Package,
                        "query",
                        return_value=QueryResult(result=known_package),
                    ),
                    mock.patch.object(
                        views.blobstore.BlobstoreUploadHandler,
                        "get_uploads",
                        return_value=[uploaded],
                    ),
                    mock.patch.object(
                        views.blobstore,
                        "get",
                        return_value=rejected_blob,
                    ),
                ):
                    response = self.client.post(
                        "/blobstore",
                        data={
                            "name": "example",
                            "arch": "amd64",
                            "vers": "1.0",
                            "sha1": digest,
                            "dependencies": dependencies,
                        },
                    )

                self.assertEqual(response.status_code, 409)
                rejected_blob.delete.assert_called_once_with()

    def test_malformed_dependencies_delete_uploaded_blob(self):
        uploaded = SimpleNamespace(key=lambda: "rejected-blob-key")
        rejected_blob = mock.Mock()
        with (
            mock.patch.object(
                views.blobstore.BlobstoreUploadHandler,
                "get_uploads",
                return_value=[uploaded],
            ),
            mock.patch.object(
                views.blobstore,
                "get",
                return_value=rejected_blob,
            ),
            mock.patch.object(views.Package, "query") as package_query,
        ):
            response = self.client.post(
                "/blobstore",
                data={
                    "name": "example",
                    "arch": "amd64",
                    "vers": "1.0",
                    "sha1": "digest",
                    "dependencies": '{"not": "an array"}',
                },
            )

        self.assertEqual(response.status_code, 400)
        rejected_blob.delete.assert_called_once_with()
        package_query.assert_not_called()

    def test_malformed_blobstore_callback_is_rejected(self):
        with mock.patch.object(
            views.blobstore.BlobstoreUploadHandler,
            "get_uploads",
            side_effect=views.blobstore.BlobInfoParseError("bad upload"),
        ):
            response = self.client.post(
                "/blobstore",
                data={
                    "name": "zlib",
                    "arch": "amd64",
                    "vers": "1.2.8",
                    "sha1": "digest",
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, b"Incorrect parameters.")

    def test_wheel_upload_preserves_release_schema(self):
        credential = SimpleNamespace(
            key_value="secret",
            allowed=True,
        )
        authorisation_query = QueryResult(result=credential)
        pup_model = mock.MagicMock()
        pup_model.query.return_value = QueryResult(result=None)
        created = pup_model.return_value

        with (
            mock.patch.object(
                views.Authorisation,
                "query",
                return_value=authorisation_query,
            ),
            mock.patch.object(views, "PupModel", pup_model),
        ):
            response = self.client.post(
                "/pup.whl",
                data={
                    "key": "upload",
                    "key_value": "secret",
                    "version": "10",
                    "blob": base64.b64encode(b"new wheel").decode("ascii"),
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"ok")
        pup_model.assert_called_once_with(
            pup_version=10,
            pup_contents=b"new wheel",
        )
        created.put.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
