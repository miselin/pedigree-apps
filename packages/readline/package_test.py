import os
import tempfile
import unittest

from .package import ReadlinePackage


class ReadlinePackageTest(unittest.TestCase):
    def test_postdeploy_creates_shared_library_links(self):
        with tempfile.TemporaryDirectory() as deploydir:
            libdir = os.path.join(deploydir, 'usr', 'lib')
            os.makedirs(libdir)
            for library in ('readline', 'history'):
                with open(
                    os.path.join(libdir, 'lib%s.so.8.3' % library), 'wb'
                ) as shared_library:
                    shared_library.write(b'ELF fixture')

            ReadlinePackage(__file__).postdeploy({}, '', deploydir)

            for library in ('readline', 'history'):
                self.assertEqual(
                    os.readlink(os.path.join(libdir, 'lib%s.so.8' % library)),
                    'lib%s.so.8.3' % library,
                )
                self.assertEqual(
                    os.readlink(os.path.join(libdir, 'lib%s.so' % library)),
                    'lib%s.so.8' % library,
                )

    def test_postdeploy_requires_both_shared_libraries(self):
        with tempfile.TemporaryDirectory() as deploydir:
            libdir = os.path.join(deploydir, 'usr', 'lib')
            os.makedirs(libdir)
            with open(
                os.path.join(libdir, 'libreadline.so.8.3'), 'wb'
            ) as shared_library:
                shared_library.write(b'ELF fixture')

            with self.assertRaisesRegex(RuntimeError, 'libhistory.so.8.3'):
                ReadlinePackage(__file__).postdeploy({}, '', deploydir)


if __name__ == '__main__':
    unittest.main()
