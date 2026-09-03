import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("publish-packages.py")
SPEC = importlib.util.spec_from_file_location("publish_packages", SCRIPT)
publish_packages = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publish_packages)


class PublishPackagesTest(unittest.TestCase):
    def test_all_audits_before_loading_key_and_uploading(self):
        events = []

        def run(command, **kwargs):
            events.append((command[-1], kwargs["env"].get("UPLOAD_KEY")))

        def load_key(project):
            events.append(("load-key", project))
            return "secret"

        with (
            mock.patch.object(sys, "argv", [str(SCRIPT), "--all"]),
            mock.patch.dict(os.environ, {"UPLOAD_KEY": ""}, clear=False),
            mock.patch.object(publish_packages.subprocess, "run", side_effect=run),
            mock.patch.object(
                publish_packages,
                "upload_key_from_datastore",
                side_effect=load_key,
            ),
        ):
            publish_packages.main()

        self.assertEqual(
            events,
            [
                ("--audit-only", None),
                ("load-key", publish_packages.DEFAULT_PROJECT),
                ("--upload-only", "secret"),
            ],
        )

    def test_named_packages_use_the_same_selection_for_audit_and_upload(self):
        with (
            mock.patch.object(
                sys,
                "argv",
                [str(SCRIPT), "runtime", "application"],
            ),
            mock.patch.dict(
                os.environ, {"UPLOAD_KEY": "existing-secret"}, clear=False
            ),
            mock.patch.object(
                publish_packages.subprocess, "run"
            ) as run,
            mock.patch.object(
                publish_packages, "upload_key_from_datastore"
            ) as load_key,
        ):
            publish_packages.main()

        expected_selection = ["--only", "runtime", "application"]
        self.assertEqual(run.call_count, 2)
        self.assertEqual(
            run.call_args_list[0].args[0][1:],
            expected_selection + ["--audit-only"],
        )
        self.assertEqual(
            run.call_args_list[1].args[0][1:],
            expected_selection + ["--upload-only"],
        )
        self.assertNotIn("UPLOAD_KEY", run.call_args_list[0].kwargs["env"])
        self.assertEqual(
            run.call_args_list[1].kwargs["env"]["UPLOAD_KEY"],
            "existing-secret",
        )
        load_key.assert_not_called()


if __name__ == "__main__":
    unittest.main()
