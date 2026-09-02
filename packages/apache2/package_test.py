import os
import tempfile
import unittest
from unittest import mock

from support import steps

from .package import Apache2Package


class Apache2PackageTest(unittest.TestCase):
    def setUp(self):
        self.package = Apache2Package(__file__)

    def test_current_release_and_dependencies(self):
        self.assertEqual(self.package.version(), '2.4.68')
        self.assertEqual(
            self.package.build_requires(),
            ['apr', 'apr-util', 'expat', 'libpcre2'],
        )
        self.assertEqual(
            self.package.install_deps(), self.package.build_requires()
        )

    @mock.patch.object(steps, 'run_configure')
    def test_configure_is_static_prefork_and_fhs(self, run_configure):
        with tempfile.TemporaryDirectory() as tempdir:
            sysroot = os.path.join(tempdir, 'sysroot')
            source = os.path.join(tempdir, 'source')
            libtool_dir = os.path.join(
                sysroot, 'usr', 'share', 'apr-1', 'build'
            )
            os.makedirs(libtool_dir)
            os.makedirs(source)
            with open(
                os.path.join(libtool_dir, 'libtool'),
                'w',
                encoding='utf-8',
            ) as libtool:
                libtool.write(
                    'lt_sysroot=\n'
                    'hardcode_into_libs=yes\n'
                    'hardcode_libdir_flag_spec="\\$wl-rpath '
                    '\\$wl\\$libdir"\n'
                    'hardcode_action=immediate\n'
                )

            env = {'PORTS_SYSROOT': sysroot}
            self.package.configure(env, source)

        options = run_configure.call_args.kwargs['extra_config']
        self.assertEqual(run_configure.call_args.kwargs['paths'], ())
        self.assertIn('--enable-layout=Pedigree', options)
        self.assertIn('--with-mpm=prefork', options)
        self.assertIn('--enable-mods-static=few', options)
        self.assertIn('--disable-so', options)
        self.assertIn('--disable-cgi', options)
        self.assertIn(
            '--with-apr=%s/usr/bin/apr-1-config' % sysroot, options
        )
        self.assertIn(
            '--with-apr-util=%s/usr/bin/apu-1-config' % sysroot, options
        )
        self.assertIn(
            '--with-pcre=%s/usr/bin/pcre2-config' % sysroot, options
        )
        self.assertIn('-D_GNU_SOURCE', env['CPPFLAGS'])

    def test_patch_has_host_generator_and_fhs_layout(self):
        patch_path = os.path.join(
            os.path.dirname(__file__), 'patches', self.package.patches({}, '')[0]
        )
        with open(patch_path, encoding='utf-8') as patch_file:
            patch = patch_file.read()

        self.assertIn('$(CC_FOR_BUILD) $(CFLAGS_FOR_BUILD)', patch)
        self.assertIn('-DCROSS_COMPILE', patch)
        self.assertIn(
            'APR_HAS_THREADS && (APR_HAVE_SIGWAIT || APR_HAVE_SIGSUSPEND)',
            patch,
        )
        self.assertIn('<Layout Pedigree>', patch)
        self.assertIn('sysconfdir:      /etc/apache2', patch)
        self.assertIn('htdocsdir:       /var/www/htdocs', patch)
        self.assertIn(
            'logfiledir:      ${localstatedir}/log/apache2', patch
        )

    def test_postdeploy_enforces_one_prefork_worker(self):
        with tempfile.TemporaryDirectory() as deploydir:
            config_dir = os.path.join(deploydir, 'etc', 'apache2')
            os.makedirs(config_dir)
            config_path = os.path.join(config_dir, 'httpd.conf')
            with open(config_path, 'w', encoding='utf-8') as config:
                config.write(
                    'Listen 80\nUser daemon\nGroup daemon\n'
                )
            for relative in (
                os.path.join('usr', 'include', 'apache2'),
                os.path.join('usr', 'lib', 'apache2', 'modules'),
                os.path.join('usr', 'share', 'apache2', 'build'),
            ):
                path = os.path.join(deploydir, relative)
                os.makedirs(path)
                with open(
                    os.path.join(path, 'stale'), 'w', encoding='utf-8'
                ) as stale:
                    stale.write('/workspace/build metadata')
            apachectl = os.path.join(deploydir, 'usr', 'sbin', 'apachectl')
            os.makedirs(os.path.dirname(apachectl))
            with open(apachectl, 'w', encoding='utf-8') as control:
                control.write('#!/bin/sh\nexec /usr/sbin/httpd -k start\n')

            with mock.patch.object(
                steps, 'get_builddir', return_value='/build/root'
            ):
                self.package.postdeploy({}, '/source/root', deploydir)

            with open(config_path, encoding='utf-8') as config:
                contents = config.read()
            self.assertIn('User #65534', contents)
            self.assertIn('Group #65534', contents)
            self.assertNotIn('User daemon', contents)
            self.assertNotIn('Group daemon', contents)
            self.assertIn(
                '/usr/sbin/httpd -X -f /etc/apache2/httpd.conf',
                contents,
            )
            self.assertIn(
                'Ordinary daemon mode remains unsupported', contents
            )
            for directive in (
                'StartServers 1',
                'MinSpareServers 1',
                'MaxSpareServers 1',
                'ServerLimit 1',
                'MaxRequestWorkers 1',
                'MaxConnectionsPerChild 0',
            ):
                with self.subTest(directive=directive):
                    self.assertEqual(contents.count(directive), 1)
            self.assertFalse(
                os.path.exists(
                    os.path.join(deploydir, 'usr', 'include', 'apache2')
                )
            )
            self.assertFalse(
                os.path.exists(
                    os.path.join(
                        deploydir, 'usr', 'share', 'apache2', 'build'
                    )
                )
            )
            self.assertFalse(os.path.exists(apachectl))

    @mock.patch.object(steps, 'make')
    def test_deploy_serializes_upstream_install_directories(self, make):
        env = {'PORTS_SYSROOT': '/sysroot'}

        with mock.patch.object(
            self.package, '_libtool_path', return_value='/build/libtool'
        ):
            self.package.deploy(env, '/source', '/deploy')

        self.assertEqual(make.call_args.kwargs['target'], 'install')
        self.assertFalse(make.call_args.kwargs['parallel'])

    @mock.patch.object(steps, 'download')
    def test_download_is_official_and_pinned(self, download):
        self.package.download({}, '/archive')

        url, target = download.call_args.args
        self.assertEqual(
            url,
            'https://downloads.apache.org/httpd/httpd-2.4.68.tar.bz2',
        )
        self.assertEqual(target, '/archive')
        self.assertRegex(
            download.call_args.kwargs['sha256'], r'^[0-9a-f]{64}$'
        )


if __name__ == '__main__':
    unittest.main()
