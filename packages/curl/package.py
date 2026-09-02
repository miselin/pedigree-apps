import os
import re

from support import buildsystem
from support import steps


class CurlPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(CurlPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'xz'

    def name(self):
        return 'curl'

    def version(self):
        return '8.22.0'

    def build_requires(self):
        return ['ca-certificates', 'zlib', 'openssl']

    def install_deps(self):
        return self.build_requires()

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://curl.se/download/curl-%s.tar.xz' % self.version(),
            target,
            sha256='f7ef3ae8a22e521f289803fe93543eb64c329b58aa73a9e224dfd915a2a5f4f7',
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self,
            srcdir,
            env,
            inplace=False,
            extra_config=(
                '--enable-shared',
                '--enable-static',
                '--disable-docs',
                '--disable-manual',
                '--disable-ldap',
                '--disable-ldaps',
                '--disable-threaded-resolver',
                '--with-openssl',
                '--with-zlib',
                '--without-brotli',
                '--without-zstd',
                '--without-libpsl',
                '--without-libidn2',
                '--without-nghttp2',
                '--without-ngtcp2',
                '--without-nghttp3',
                '--without-quiche',
                '--without-libssh2',
                '--without-gssapi',
                '--with-ca-bundle=/etc/ssl/cert.pem',
                '--without-ca-path',
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install', inplace=False)

    def postdeploy(self, env, srcdir, deploydir):
        config = os.path.join(deploydir, 'usr', 'bin', 'curl-config')
        with open(config, encoding='utf-8') as source:
            contents = source.read()

        target_sysroot = os.path.normpath(env['TARGET_SYSROOT'])
        ports_sysroot = os.path.normpath(env['PORTS_SYSROOT'])
        staged_lib = os.path.join(ports_sysroot, 'usr', 'lib')
        sanitized = contents
        for variable, native_tool in (
            ('CROSS_CC', 'gcc'),
            ('CROSS_CXX', 'g++'),
            ('CROSS_CPP', 'cpp'),
            ('CROSS_AS', 'as'),
            ('CROSS_LD', 'ld'),
            ('CROSS_AR', 'ar'),
            ('CROSS_RANLIB', 'ranlib'),
            ('CROSS_STRIP', 'strip'),
        ):
            cross_tool = env.get(variable)
            if cross_tool:
                sanitized = sanitized.replace(cross_tool, native_tool)
        for option in (
            '--with-sysroot=%s' % ports_sysroot,
            '--sysroot=%s' % target_sysroot,
        ):
            sanitized = re.sub(
                r'(?P<quote>[\'\"]?)%s(?P=quote)'
                % re.escape(option),
                '',
                sanitized,
            )
        sanitized = re.sub(
            r'(?<![^\s\'\"=])%s(?=$|\s|[\'\"])'
            % re.escape('-Wl,-rpath-link,%s' % staged_lib),
            '',
            sanitized,
        )
        # Keep dependency search flags useful to native target consumers.
        sanitized = sanitized.replace(ports_sysroot, '')
        sanitized = sanitized.replace(target_sysroot, '')

        forbidden_paths = tuple(
            path
            for path in (
                env.get('APPS_BASE'),
                env.get('CROSS_BASE'),
                ports_sysroot,
                target_sysroot,
            )
            if path
        )
        leaked = [path for path in forbidden_paths if path in sanitized]
        if leaked:
            raise RuntimeError(
                'curl-config contains cross-build paths: %s'
                % ', '.join(leaked)
            )
        with open(config, 'w', encoding='utf-8') as destination:
            destination.write(sanitized)

        for relative_path in (
            os.path.join('usr', 'lib', 'pkgconfig', 'libcurl.pc'),
            os.path.join('usr', 'lib', 'libcurl.la'),
        ):
            metadata_path = os.path.join(deploydir, relative_path)
            with open(metadata_path, encoding='utf-8') as source:
                metadata = source.read()
            metadata_sanitized = re.sub(
                r'(?<![^\s\'"=])%s(?=$|\s|[\'\"])'
                % re.escape('-Wl,-rpath-link,%s' % staged_lib),
                '',
                metadata,
            )
            metadata_sanitized = metadata_sanitized.replace(
                ports_sysroot, '')
            metadata_sanitized = metadata_sanitized.replace(
                target_sysroot, '')
            leaked = [
                path for path in forbidden_paths
                if path in metadata_sanitized
            ]
            if leaked:
                raise RuntimeError(
                    '%s contains cross-build paths: %s'
                    % (relative_path, ', '.join(leaked))
                )
            with open(metadata_path, 'w', encoding='utf-8') as destination:
                destination.write(metadata_sanitized)
