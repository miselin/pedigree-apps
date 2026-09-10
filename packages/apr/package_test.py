import os
import tempfile
import unittest
from unittest import mock

from support import steps

from .package import AprPackage


class AprPackageTest(unittest.TestCase):
    def setUp(self):
        self.package = AprPackage(__file__)

    def test_current_release_and_dependencies(self):
        self.assertEqual(self.package.version(), '1.7.6')
        self.assertEqual(self.package.build_requires(), [])
        self.assertEqual(self.package.install_deps(), ['sed'])

    @mock.patch.object(steps, 'run_configure')
    def test_configure_matches_pedigree_runtime(self, run_configure):
        env = {}

        self.package.configure(env, '/source')

        options = run_configure.call_args.kwargs['extra_config']
        self.assertIn('--enable-threads', options)
        self.assertNotIn('--disable-posix-shm', options)
        self.assertNotIn('--disable-sysv-shm', options)
        self.assertIn('--disable-dso', options)
        self.assertIn('--includedir=/usr/include/apr-1', options)
        self.assertEqual(env['ac_cv_file__dev_zero'], 'yes')
        self.assertEqual(env['ac_cv_strerror_r_rc_int'], 'yes')
        for function in (
            'shm_open',
            'shm_unlink',
        ):
            self.assertEqual(env['ac_cv_func_%s' % function], 'no')
        for function in (
            'shmget',
            'shmat',
            'shmdt',
            'shmctl',
            'semget',
            'semctl',
            'semop',
            'semtimedop',
        ):
            self.assertNotIn('ac_cv_func_%s' % function, env)

    @mock.patch.object(steps, 'download')
    def test_download_is_official_and_pinned(self, download):
        self.package.download({}, '/archive')

        url, target = download.call_args.args
        self.assertEqual(
            url, 'https://downloads.apache.org/apr/apr-1.7.6.tar.bz2'
        )
        self.assertEqual(target, '/archive')
        self.assertRegex(
            download.call_args.kwargs['sha256'], r'^[0-9a-f]{64}$'
        )

    def test_postdeploy_keeps_libtool_dependencies_sysroot_relocatable(self):
        with tempfile.TemporaryDirectory() as deploydir:
            libdir = os.path.join(deploydir, 'usr', 'lib')
            os.makedirs(libdir)
            metadata = os.path.join(libdir, 'libapr-1.la')
            with open(metadata, 'w', encoding='utf-8') as archive:
                archive.write(
                    "dependency_libs=' -L/sysroot/usr/lib "
                    "/sysroot/usr/lib/libdependency.la'\n"
                    "libdir='/usr/lib'\n"
                )

            with mock.patch.object(steps, 'get_builddir', return_value='/b'):
                self.package.postdeploy(
                    {'PORTS_SYSROOT': '/sysroot'}, '/source', deploydir
                )

            with open(metadata, encoding='utf-8') as archive:
                contents = archive.read()
            self.assertIn(
                "dependency_libs=' -L=/usr/lib "
                "=/usr/lib/libdependency.la'",
                contents,
            )
            self.assertIn("libdir='/usr/lib'", contents)


if __name__ == '__main__':
    unittest.main()
