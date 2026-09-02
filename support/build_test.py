
import os
import tarfile
import tempfile
import unittest
from io import BytesIO

from . import build
from . import buildsystem


class BuildTest(unittest.TestCase):
    class FakePackage(buildsystem.Package):
        def name(self):
            return "fake"

        def version(self):
            return "1.0"

        def deploy(self, env, srcdir, deploydir):
            bindir = os.path.join(deploydir, "usr", "bin")
            os.makedirs(bindir)
            with open(os.path.join(bindir, "fake"), "w", encoding="utf-8") as f:
                f.write("fake\n")

        def repository_prep(self, env, srcdir, deploydir):
            pass

    class FailingPackage(FakePackage):
        def deploy(self, env, srcdir, deploydir):
            super().deploy(env, srcdir, deploydir)
            raise RuntimeError("deploy failed")

    def environment(self, temporary):
        return {
            "DOWNLOAD_TEMP": os.path.join(temporary, "downloads"),
            "BUILD_BASE": os.path.join(temporary, "build"),
            "OUTPUT_BASE": os.path.join(temporary, "output"),
        }

    def test_successful_build_commits_root_and_marker(self):
        with tempfile.TemporaryDirectory() as temporary:
            package = self.FakePackage(__file__)
            build.build_package(package, self.environment(temporary))
            deploy_base = os.path.join(temporary, "output", "fake", "1.0")
            self.assertTrue(os.path.isfile(os.path.join(deploy_base, ".complete")))
            self.assertTrue(os.path.isfile(os.path.join(deploy_base, "root", "usr", "bin", "fake")))
            self.assertFalse(os.path.exists(os.path.join(deploy_base, "root.incomplete")))

    def test_failed_build_removes_incomplete_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            package = self.FailingPackage(__file__)
            with self.assertRaisesRegex(RuntimeError, "deploy failed"):
                build.build_package(package, self.environment(temporary))
            deploy_base = os.path.join(temporary, "output", "fake", "1.0")
            self.assertFalse(os.path.exists(os.path.join(deploy_base, "root")))
            self.assertFalse(os.path.exists(os.path.join(deploy_base, "root.incomplete")))

    def test_safe_members_keeps_a_single_top_level_file(self):
        with tempfile.NamedTemporaryFile() as archive_file:
            with tarfile.open(archive_file.name, "w") as archive:
                contents = b"single file\n"
                member = tarfile.TarInfo("README")
                member.size = len(contents)
                archive.addfile(member, BytesIO(contents))

            with tarfile.open(archive_file.name) as archive:
                members = list(build._safe_members(archive))

        self.assertEqual([member.name for member in members], ["README"])


if __name__ == '__main__':
    unittest.main()
