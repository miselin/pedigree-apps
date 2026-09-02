import os
import unittest
from unittest import mock

from .package import LibffiPackage


class LibffiPackageTest(unittest.TestCase):

    def setUp(self):
        self.package = LibffiPackage(__file__)

    def test_recipe_applies_pedigree_nonexec_stack_patch(self):
        self.assertEqual(
            self.package.patches({}, "/source"),
            ["pedigree-nonexec-stack.diff"],
        )

    @mock.patch("packages.libffi.package.steps.run_configure")
    def test_configure_keeps_shared_and_static_libraries(self, run_configure):
        self.package.configure({}, "/source")

        options = run_configure.call_args.kwargs["extra_config"]
        self.assertIn("--enable-shared", options)
        self.assertIn("--enable-static", options)

    def test_patch_marks_both_active_x86_64_assembly_objects_nonexec(self):
        patch_path = os.path.join(
            os.path.dirname(__file__),
            "patches",
            "pedigree-nonexec-stack.diff",
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        for filename in ("unix64.S", "win64.S"):
            with self.subTest(filename=filename):
                self.assertIn(
                    "diff --git a/src/x86/%s b/src/x86/%s"
                    % (filename, filename),
                    patch,
                )
        pedigree_stack_guard = (
            "+#if defined __ELF__ && (defined __linux__ || "
            "defined __FreeBSD__ || defined __pedigree__)"
        )
        self.assertEqual(patch.count("diff --git"), 2)
        self.assertEqual(patch.count(pedigree_stack_guard), 2)
        self.assertEqual(patch.count('.note.GNU-stack,"",@progbits'), 2)


if __name__ == "__main__":
    unittest.main()
