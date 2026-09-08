import importlib.util
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("build-codex-app-server.py")
SPEC = importlib.util.spec_from_file_location("build_codex", SCRIPT)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class BuildCodexTest(unittest.TestCase):
    def test_default_outputs_keep_cli_and_app_server_separate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            outputs = []
            jobs = []
            for arguments in ([], ["--component", "cli"], ["--component", "code-mode-host"]):
                with (
                    mock.patch.object(builder, "ROOT", root),
                    mock.patch.object(builder, "build") as build,
                    mock.patch.object(sys, "argv", [str(SCRIPT), "build", *arguments,
                                                  "--cache", str(root / "cache")]),
                ):
                    builder.main()
                outputs.append(build.call_args.args[1])
                jobs.append(build.call_args.args[4])
            self.assertEqual(outputs, [root / ".build/codex-app-server/artifacts",
                                       root / ".build/codex-cli/artifacts",
                                       root / ".build/codex-code-mode-host/artifacts"])
            self.assertEqual(jobs, [4, 1, 1])

    def test_explicit_output_is_retained_for_cli(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            output = root / "custom-artifacts"
            with (
                mock.patch.object(builder, "build") as build,
                mock.patch.object(sys, "argv", [str(SCRIPT), "build", "--component", "cli",
                                              "--cache", str(root / "cache"),
                                              "--output", str(output), "--offline",
                                              "--jobs", "2"]),
            ):
                builder.main()
            self.assertEqual(build.call_args.args[1], output)
            self.assertTrue(build.call_args.args[3])
            self.assertEqual(build.call_args.args[4], 2)

    def test_cli_patch_change_does_not_replace_app_server_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            shared_patch = root / "packages/codex-app-server/patches/pedigree.diff"
            cli_patch = root / "packages/codex-cli/patches/pedigree.diff"
            host_patch = root / "packages/codex-code-mode-host/patches/pedigree.diff"
            for patch in (shared_patch, cli_patch, host_patch):
                patch.parent.mkdir(parents=True)
            shared_patch.write_text("shared patch")
            cli_patch.write_text("CLI patch v1")
            host_patch.write_text("host patch")
            archive = root / "source.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                contents = b"upstream fixture"
                member = tarfile.TarInfo("codex-" + builder.REVISION + "/fixture")
                member.size = len(contents)
                bundle.addfile(member, io.BytesIO(contents))

            def apply_patch(command, *, cwd, check):
                patch = Path(command[-1])
                with (cwd / "fixture").open("a") as fixture:
                    fixture.write("\n" + patch.read_text())

            with (
                mock.patch.object(builder, "ROOT", root),
                mock.patch.object(builder, "PATCH", shared_patch),
                mock.patch.object(builder.rust, "fetch", return_value=archive),
                mock.patch.object(builder.subprocess, "run", side_effect=apply_patch) as patch_run,
            ):
                cache = root / "cache"
                app_source = builder.source_tree(cache, True)
                cli_source = builder.source_tree(cache, True, "cli")
                self.assertNotEqual(app_source, cli_source)
                self.assertEqual((app_source / "fixture").read_text(),
                                 "upstream fixture\nshared patch")
                self.assertEqual((cli_source / "fixture").read_text(),
                                 "upstream fixture\nshared patch\nCLI patch v1")
                patch_run.reset_mock()
                host_source = builder.source_tree(cache, True, "code-mode-host")
                self.assertNotIn(host_source, (app_source, cli_source))
                self.assertEqual((host_source / "fixture").read_text(), "upstream fixture\nhost patch")
                patch_run.assert_called_once()
                patch_run.reset_mock()
                builder.source_tree(cache, True, "cli")
                patch_run.assert_not_called()

                sentinel = app_source / "preserve-app-server"
                sentinel.write_text("existing source")
                cli_patch.write_text("CLI patch v2")
                builder.source_tree(cache, True, "cli")
                self.assertEqual((cli_source / "fixture").read_text(),
                                 "upstream fixture\nshared patch\nCLI patch v2")
                self.assertEqual(sentinel.read_text(), "existing source")
                self.assertEqual((app_source / "fixture").read_text(),
                                 "upstream fixture\nshared patch")


if __name__ == "__main__":
    unittest.main()
