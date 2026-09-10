import unittest

from .package import GlibPackage


class GlibPackageTest(unittest.TestCase):
    def test_runtime_dependencies_include_python_tools(self):
        self.assertEqual(
            GlibPackage(__file__).install_deps(),
            ["libffi", "libpcre2", "zlib", "python3"],
        )


if __name__ == "__main__":
    unittest.main()
