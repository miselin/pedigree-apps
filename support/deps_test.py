
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

        deps._pup = mock.MagicMock()
        deps._pup.return_value = None

        deps.install_dependent_packages(packages, package2, self.env)

        deps._pup.assert_has_calls([
            mock.call(self.env, 'sync'),
            mock.call(self.env, 'install', 'package1'),
        ])

        sorted_deps = [first for first, _ in deps.sort_dependencies(packages)]
        self.assertEqual(sorted_deps, ['package1', 'package2'])


if __name__ == '__main__':
    unittest.main()
