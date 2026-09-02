import os
import tempfile
import unittest
from unittest import mock

from .package import GlibPackage


class GlibPackageTest(unittest.TestCase):
    def test_runtime_dependencies_include_python_tools(self):
        self.assertEqual(
            GlibPackage(__file__).install_deps(),
            ["libffi", "libpcre2", "zlib", "python3"],
        )

    def test_recipe_enables_signal_fallback(self):
        package = GlibPackage(__file__)
        self.assertIn(
            "pedigree-signal-fallback.diff", package.patches({}, "")
        )

    def test_signal_fallback_patch_applies_without_fuzz(self):
        with tempfile.TemporaryDirectory() as srcdir:
            gio = os.path.join(srcdir, "gio")
            os.makedirs(gio)
            connection = os.path.join(gio, "gdbusconnection.c")
            lines = ["\n"] * 937
            lines[94:102] = [
                '#include "config.h"\n',
                "\n",
                "#include <stdlib.h>\n",
                "#include <string.h>\n",
                "\n",
                '#include "gdbusauth.h"\n',
                '#include "gdbusutils.h"\n',
                '#include "gdbusaddress.h"\n',
            ]
            lines[930:937] = [
                "      (flags & FLAG_INITIALIZED) != 0 &&\n",
                "      connection->initialization_error == NULL)\n",
                "    {\n",
                "      raise (SIGTERM);\n",
                "    }\n",
                "}\n",
                "\n",
            ]
            with open(connection, "w", encoding="utf-8") as source:
                source.writelines(lines)

            package = GlibPackage(__file__)
            with mock.patch.object(
                package,
                "patches",
                return_value=["pedigree-signal-fallback.diff"],
            ):
                package.patch({"PATCH": "/usr/bin/patch"}, srcdir)

            with open(connection, encoding="utf-8") as source:
                patched = source.read()
            self.assertIn("#ifdef __pedigree__", patched)
            self.assertIn("#include <unistd.h>", patched)
            self.assertIn("kill (getpid (), SIGTERM);", patched)
            self.assertIn("#else\n      raise (SIGTERM);", patched)


if __name__ == "__main__":
    unittest.main()
