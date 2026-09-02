import os
import tarfile
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from . import create


class CreatePackageCommandTest(unittest.TestCase):
    def arguments(self, source):
        return SimpleNamespace(
            package="example",
            version="1.0",
            architecture="amd64",
            path=source,
        )

    def test_archive_members_are_root_owned(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = os.path.join(temporary, "root")
            cache = os.path.join(temporary, "cache")
            os.makedirs(os.path.join(source, "usr", "bin"))
            with open(
                os.path.join(source, "usr", "bin", "example"),
                "w",
                encoding="utf-8",
            ) as executable:
                executable.write("example\n")

            config = SimpleNamespace(local_cache=cache)
            with mock.patch("builtins.print"):
                create.CreatePackageCommand().run(self.arguments(source), config)

            archive_path = os.path.join(cache, "example-1.0-amd64.pup")
            with tarfile.open(archive_path) as archive:
                for member in archive.getmembers():
                    self.assertEqual(member.uid, 0)
                    self.assertEqual(member.gid, 0)
                    self.assertEqual(member.uname, "root")
                    self.assertEqual(member.gname, "root")

    def test_failed_archive_creation_preserves_previous_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = os.path.join(temporary, "root")
            cache = os.path.join(temporary, "cache")
            os.makedirs(source)
            os.makedirs(cache)
            with open(os.path.join(source, "entry"), "w", encoding="utf-8") as entry:
                entry.write("new\n")
            archive_path = os.path.join(cache, "example-1.0-amd64.pup")
            with open(archive_path, "wb") as archive:
                archive.write(b"previous")

            with mock.patch(
                "pup.pedigree_updater.commands.create.tarfile.open",
                side_effect=OSError("archive failed"),
            ):
                with self.assertRaisesRegex(OSError, "archive failed"):
                    create.CreatePackageCommand().run(
                        self.arguments(source), SimpleNamespace(local_cache=cache)
                    )

            with open(archive_path, "rb") as archive:
                self.assertEqual(archive.read(), b"previous")
            self.assertFalse(os.path.exists(archive_path + ".tmp"))


if __name__ == "__main__":
    unittest.main()
