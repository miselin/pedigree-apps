import os
import shutil

from support import buildsystem
from support import steps


class Apache2Package(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(Apache2Package, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'bz2'

    def name(self):
        return 'apache2'

    def version(self):
        return '2.4.68'

    def build_requires(self):
        return ['apr', 'apr-util', 'expat', 'libpcre2']

    def install_deps(self):
        return self.build_requires()

    def patches(self, env, srcdir):
        return ['pedigree-fhs-cross.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://downloads.apache.org/httpd/httpd-%s.tar.bz2'
            % self.version(),
            target,
            sha256=(
                '68c74d4df38c26bed4dfbdb8f3baf1eb532f3872357becc1bba5d136f6b63c06'
            ),
        )

    def configure(self, env, srcdir):
        sysroot = env['PORTS_SYSROOT']
        # These run-time probes cannot execute while cross compiling. The
        # selected results match the current Pedigree libc ABI.
        env['ap_cv_void_ptr_lt_long'] = 'no'
        env['ac_cv_func_setpgrp_void'] = 'yes'
        env['CC_FOR_BUILD'] = '/usr/bin/cc'
        env['CFLAGS_FOR_BUILD'] = '-O2'
        env['CPPFLAGS'] = (
            env.get('CPPFLAGS', '') + ' -D_GNU_SOURCE'
        ).strip()

        steps.run_configure(
            self,
            srcdir,
            env,
            inplace=False,
            paths=(),
            extra_config=(
                '--enable-layout=Pedigree',
                '--with-apr=%s/usr/bin/apr-1-config' % sysroot,
                '--with-apr-util=%s/usr/bin/apu-1-config' % sysroot,
                '--with-pcre=%s/usr/bin/pcre2-config' % sysroot,
                '--with-mpm=prefork',
                '--enable-mods-static=few',
                '--disable-so',
                '--disable-cgi',
                '--disable-cgid',
                '--disable-status',
                '--disable-suexec',
                '--disable-pie',
                '--with-port=80',
            ),
        )
        self._prepare_libtool(env, srcdir)

    def build(self, env, srcdir):
        steps.make(
            srcdir,
            env,
            inplace=False,
            extra_opts=(
                'CC_FOR_BUILD=/usr/bin/cc',
                'CFLAGS_FOR_BUILD=-O2',
            ) + self._make_options(env, srcdir),
        )

    def deploy(self, env, srcdir, deploydir):
        steps.make(
            srcdir,
            env,
            target='install',
            inplace=False,
            parallel=False,
            extra_opts=(
                'DESTDIR=%s' % deploydir,
                'CC_FOR_BUILD=/usr/bin/cc',
                'CFLAGS_FOR_BUILD=-O2',
            ) + self._make_options(env, srcdir),
        )

    @staticmethod
    def _libtool_path(srcdir, env):
        return os.path.join(
            steps.get_builddir(srcdir, env, False), 'pedigree-libtool'
        )

    def _prepare_libtool(self, env, srcdir):
        source_path = os.path.join(
            env['PORTS_SYSROOT'],
            'usr',
            'share',
            'apr-1',
            'build',
            'libtool',
        )
        with open(source_path, encoding='utf-8') as source:
            contents = source.read()
        replacements = (
            (
                'lt_sysroot=\n',
                "lt_sysroot='%s'\n" % env['PORTS_SYSROOT'],
            ),
            ('hardcode_into_libs=yes', 'hardcode_into_libs=no'),
            ('hardcode_libdir_flag_spec="\\$wl-rpath \\$wl\\$libdir"',
             'hardcode_libdir_flag_spec=""'),
            ('hardcode_action=immediate', 'hardcode_action=unsupported'),
        )
        for old, new in replacements:
            if old not in contents:
                raise RuntimeError('APR libtool is missing setting: %s' % old)
            contents = contents.replace(old, new, 1)
        with open(
            self._libtool_path(srcdir, env), 'w', encoding='utf-8'
        ) as destination:
            destination.write(contents)

    def _make_options(self, env, srcdir):
        return ('LIBTOOL=/bin/sh %s' % self._libtool_path(srcdir, env),)

    def postdeploy(self, env, srcdir, deploydir):
        # The static target profile cannot load third-party modules, so its
        # incomplete build metadata and headers would be misleading.
        for relative in (
            os.path.join('usr', 'include', 'apache2'),
            os.path.join('usr', 'lib', 'apache2', 'modules'),
            os.path.join('usr', 'share', 'apache2', 'build'),
        ):
            path = os.path.join(deploydir, relative)
            if os.path.isdir(path):
                shutil.rmtree(path)

        # apxs and dbmmanage are development/admin Perl programs. apachectl
        # starts the unsupported multi-process daemon mode, so the bounded
        # target profile exposes httpd directly instead.
        for relative in (
            os.path.join('usr', 'bin', 'apxs'),
            os.path.join('usr', 'bin', 'dbmmanage'),
            os.path.join('usr', 'sbin', 'apachectl'),
        ):
            path = os.path.join(deploydir, relative)
            if os.path.lexists(path):
                os.unlink(path)

        config_path = os.path.join(
            deploydir, 'etc', 'apache2', 'httpd.conf'
        )
        with open(config_path, encoding='utf-8') as config:
            config_contents = config.read()
        config_contents = config_contents.replace(
            'User daemon\n', 'User #65534\n'
        ).replace('Group daemon\n', 'Group #65534\n')
        config_contents += (
            '\n# Pedigree file locking is not process-safe. Run this profile as:\n'
            '# /usr/sbin/httpd -X -f /etc/apache2/httpd.conf\n'
            '# Ordinary daemon mode remains unsupported until locking works.\n'
            'StartServers 1\n'
            'MinSpareServers 1\n'
            'MaxSpareServers 1\n'
            'ServerLimit 1\n'
            'MaxRequestWorkers 1\n'
            'MaxConnectionsPerChild 0\n'
        )
        with open(config_path, 'w', encoding='utf-8') as config:
            config.write(config_contents)

        for root, _, filenames in os.walk(deploydir):
            for filename in filenames:
                path = os.path.join(root, filename)
                if os.path.islink(path):
                    continue
                try:
                    with open(path, encoding='utf-8') as source:
                        contents = source.read()
                except (UnicodeDecodeError, OSError):
                    continue
                sanitized = contents
                for build_path in (
                    os.path.realpath(
                        steps.get_builddir(srcdir, env, False)
                    ),
                    os.path.realpath(srcdir),
                    steps.get_builddir(srcdir, env, False),
                    srcdir,
                    env.get('PORTS_SYSROOT', ''),
                    env.get('TARGET_SYSROOT', ''),
                    env.get('APPS_BASE', ''),
                    env.get('CROSS_BASE', ''),
                ):
                    if build_path:
                        sanitized = sanitized.replace(build_path, '')
                if sanitized != contents:
                    with open(path, 'w', encoding='utf-8') as destination:
                        destination.write(sanitized)
