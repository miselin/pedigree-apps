import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from . import sync


class SyncCommandTest(unittest.TestCase):
    @staticmethod
    def database(name="example", version="1.2"):
        return {
            "%s-amd64" % name: {
                "name": name,
                "version": version,
                "architecture": "amd64",
                "sha1": "legacy-digest",
            }
        }

    @staticmethod
    def configuration(cache, repositories, created=False):
        return SimpleNamespace(
            local_cache=cache,
            repo_urls=repositories,
            created=created,
        )

    @staticmethod
    def write_database(path, database):
        with open(path, "w", encoding="utf-8") as database_file:
            json.dump(database, database_file)

    def test_invalid_database_preserves_last_known_good_database(self):
        with tempfile.TemporaryDirectory() as cache:
            target = os.path.join(cache, "packages.pupdb")
            old_database = self.database(version="1.1")
            self.write_database(target, old_database)

            with (
                mock.patch.object(
                    sync.pup_http,
                    "copy_url",
                    side_effect=lambda url, output: output.write(b"not json"),
                ),
                mock.patch("builtins.print"),
            ):
                result = sync.SyncCommand().run(
                    SimpleNamespace(config="/unused"),
                    self.configuration(cache, ["https://bad.example"]),
                )

            self.assertEqual(result, 1)
            with open(target, encoding="utf-8") as database_file:
                self.assertEqual(json.load(database_file), old_database)
            self.assertFalse(
                os.path.exists(os.path.join(cache, "packages_new.pupdb"))
            )

    def test_invalid_json_and_wrong_shape_fall_back(self):
        invalid_responses = (
            b"{",
            b"[]",
            b'{"example-amd64": []}',
        )
        for invalid_response in invalid_responses:
            with self.subTest(
                invalid_response=invalid_response
            ), tempfile.TemporaryDirectory() as cache:
                target = os.path.join(cache, "packages.pupdb")
                self.write_database(target, self.database(version="1.1"))
                replacement = self.database(version="1.2")
                replacement_bytes = json.dumps(replacement).encode("utf-8")

                def download(url, output):
                    output.write(
                        invalid_response
                        if url.startswith("https://bad.example/")
                        else replacement_bytes
                    )

                with (
                    mock.patch.object(
                        sync.pup_http, "copy_url", side_effect=download
                    ) as copy_url,
                    mock.patch("builtins.print"),
                ):
                    result = sync.SyncCommand().run(
                        SimpleNamespace(config="/unused"),
                        self.configuration(
                            cache,
                            ["https://bad.example", "https://good.example"],
                        ),
                    )

                self.assertIsNone(result)
                self.assertEqual(
                    [call.args[0] for call in copy_url.call_args_list],
                    [
                        "https://bad.example/packages.pupdb",
                        "https://good.example/packages.pupdb",
                    ],
                )
                with open(target, encoding="utf-8") as database_file:
                    self.assertEqual(json.load(database_file), replacement)

    def test_valid_database_replaces_old_and_stops_after_first_repository(self):
        with tempfile.TemporaryDirectory() as cache:
            target = os.path.join(cache, "packages.pupdb")
            self.write_database(target, self.database(version="1.1"))
            replacement = self.database(version="1.2")
            replacement_bytes = json.dumps(replacement).encode("utf-8")

            with (
                mock.patch.object(
                    sync.pup_http,
                    "copy_url",
                    side_effect=lambda url, output: output.write(
                        replacement_bytes
                    ),
                ) as copy_url,
                mock.patch("builtins.print"),
            ):
                result = sync.SyncCommand().run(
                    SimpleNamespace(config="/unused"),
                    self.configuration(
                        cache,
                        ["https://good.example", "https://unused.example"],
                    ),
                )

            self.assertIsNone(result)
            copy_url.assert_called_once()
            self.assertEqual(
                copy_url.call_args.args[0],
                "https://good.example/packages.pupdb",
            )
            with open(target, encoding="utf-8") as database_file:
                self.assertEqual(json.load(database_file), replacement)

    def test_stale_candidate_is_discarded_before_failed_sync(self):
        with tempfile.TemporaryDirectory() as cache:
            target = os.path.join(cache, "packages.pupdb")
            candidate = os.path.join(cache, "packages_new.pupdb")
            old_database = self.database(version="1.1")
            self.write_database(target, old_database)
            self.write_database(candidate, self.database(version="0.9"))

            with (
                mock.patch.object(
                    sync.pup_http,
                    "copy_url",
                    side_effect=sync.pup_http.RequestError("network failed"),
                ),
                mock.patch("builtins.print"),
            ):
                result = sync.SyncCommand().run(
                    SimpleNamespace(config="/unused"),
                    self.configuration(cache, ["https://bad.example"]),
                )

            self.assertEqual(result, 1)
            self.assertFalse(os.path.exists(candidate))
            with open(target, encoding="utf-8") as database_file:
                self.assertEqual(json.load(database_file), old_database)

    def test_dependency_metadata_is_optional_and_validated(self):
        with tempfile.TemporaryDirectory() as cache:
            database_path = os.path.join(cache, "packages.pupdb")

            legacy_database = self.database()
            self.write_database(database_path, legacy_database)
            self.assertTrue(sync._valid_package_database(database_path))

            database = self.database()
            database["example-amd64"]["dependencies"] = [
                "first",
                "second",
            ]
            self.write_database(database_path, database)
            self.assertTrue(sync._valid_package_database(database_path))

            for dependencies in (
                "first",
                ["first", ""],
                ["first", 2],
                None,
            ):
                with self.subTest(dependencies=dependencies):
                    database["example-amd64"]["dependencies"] = dependencies
                    self.write_database(database_path, database)
                    self.assertFalse(sync._valid_package_database(database_path))


if __name__ == "__main__":
    unittest.main()
