
import os
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from . import deps


class DepsTest(unittest.TestCase):

    def setUp(self):
        self.env = {
            'PACKMAN_TARGET_ARCH': 'amd64',
            'PACKMAN_REPO': 'packman',
            'CHROOT_BASE': 'chroot',
        }

    def test_simple_deps(self):
        package1 = mock.MagicMock()
        package2 = mock.MagicMock()

        package1.name.return_value = 'package1'
        package1.build_requires.return_value = []

        package2.name.return_value = 'package2'
        package2.build_requires.return_value = ['package1']

        packages = {
            'package1': package1,
            'package2': package2,
        }

        sorted_deps = [first for first, _ in deps.sort_dependencies(packages)]
        self.assertEqual(sorted_deps, ['package1', 'package2'])

    def test_no_deps(self):
        package1 = mock.MagicMock()
        package2 = mock.MagicMock()

        package1.name.return_value = 'package1'
        package1.build_requires.return_value = []

        package2.name.return_value = 'package2'
        package2.build_requires.return_value = []

        packages = {
            'package1': package1,
            'package2': package2,
        }

        actual = set([first for first, _ in deps.sort_dependencies(packages)])
        desired = set(['package1', 'package2'])
        self.assertEqual(actual & desired, desired)

    def test_cyclic_deps(self):
        package1 = mock.MagicMock()
        package2 = mock.MagicMock()

        package1.name.return_value = 'package1'
        package1.build_requires.return_value = ['package2']

        package2.name.return_value = 'package2'
        package2.build_requires.return_value = ['package1']

        packages = {
            'package1': package1,
            'package2': package2,
        }

        with self.assertRaises(Exception):
            deps.sort_dependencies(packages)

    def test_implicit_deps(self):
        package1 = mock.MagicMock()
        package2 = mock.MagicMock()
        package3 = mock.MagicMock()

        package1.name.return_value = 'package1'
        package1.build_requires.return_value = []

        package2.name.return_value = 'package2'
        package2.build_requires.return_value = ['package1']

        package3.name.return_value = 'package3'
        package3.build_requires.return_value = ['package2']

        packages = {
            'package1': package1,
            'package2': package2,
            'package3': package3,
        }

        sorted_deps = [first for first, _ in deps.sort_dependencies(packages)]
        self.assertEqual(sorted_deps, ['package1', 'package2', 'package3'])

    def test_dependent_extract(self):
        package1 = mock.MagicMock()
        package2 = mock.MagicMock()

        package1.name.return_value = 'package1'
        package1.version.return_value = '1.0'
        package1.build_requires.return_value = []

        package2.name.return_value = 'package2'
        package2.build_requires.return_value = ['package1']

        packages = {
            'package1': package1,
            'package2': package2,
        }

        with mock.patch('support.deps.tarfile') as mock_tarfile:
            opened = mock.MagicMock()
            mock_tarfile.open.return_value = opened

            deps.install_dependent_packages(packages, package2, self.env)

            mock_tarfile.open.assert_called_once_with(
                os.path.join(self.env['PACKMAN_REPO'], 'package1-1.0-amd64.pup'))
            opened.extractall.assert_called_once_with(path=self.env['CHROOT_BASE'])

        sorted_deps = [first for first, _ in deps.sort_dependencies(packages)]
        self.assertEqual(sorted_deps, ['package1', 'package2'])


if __name__ == '__main__':
    unittest.main()
