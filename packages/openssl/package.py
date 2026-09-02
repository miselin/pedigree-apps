
import os

from support import buildsystem
from support import steps


class OpensslPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(OpensslPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'gz'

    def name(self):
        return 'openssl'

    def version(self):
        # OpenSSL 3.5 is the current LTS line and retains the mature 3.x ABI.
        return '3.5.8'

    def build_requires(self):
        return ['zlib']

    def install_deps(self):
        # c_rehash, CA.pl, and tsget.pl are installed Perl utilities.
        return ['zlib', 'perl']

    def patches(self, env, srcdir):
        return ['pedigree-target.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://www.openssl.org/source/openssl-%s.tar.gz'
            % self.version(),
            target,
            sha256='a8f84a39918ec6415ce765d9b429d313ba97b8143169c172e734b9514464f5b2',
        )

    def configure(self, env, srcdir):
        env['CC'] = env['CROSS_CC']
        env['AR'] = env['CROSS_AR']
        env['RANLIB'] = env['CROSS_RANLIB']
        steps.cmd(
            [
                os.path.join(srcdir, 'Configure'),
                'pedigree-x86_64',
                'threads',
                'shared',
                'zlib',
                'no-async',
                'no-secure-memory',
                'no-tests',
                'no-docs',
                '--prefix=/usr',
                '--openssldir=/etc/ssl',
                '--libdir=lib',
            ],
            cwd=srcdir,
            env=env,
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        destdir = ('DESTDIR=%s' % deploydir,)
        steps.make(
            srcdir, env, target='install_sw', parallel=False,
            extra_opts=destdir)
        steps.make(
            srcdir, env, target='install_ssldirs', parallel=False,
            extra_opts=destdir)

    def postdeploy(self, env, srcdir, deploydir):
        libcrypto = os.path.join(
            deploydir, 'usr', 'lib', 'libcrypto.so.3'
        )
        if not os.path.isfile(libcrypto):
            raise RuntimeError('OpenSSL build metadata was not installed')

        with open(libcrypto, 'rb') as library:
            contents = library.read()

        marker = b'compiler: '
        if contents.count(marker) != 1:
            raise RuntimeError(
                'OpenSSL compiler diagnostic was not generated as expected'
            )
        start = contents.index(marker)
        end = contents.find(b'\0', start)
        if end < 0:
            raise RuntimeError(
                'OpenSSL compiler diagnostic was not terminated'
            )
        diagnostic = contents[start:end]

        leaked = [
            value
            for value in (env.get('CROSS_BASE'), env.get('PORTS_SYSROOT'))
            if value and value.encode() in diagnostic
        ]
        if leaked:
            raise RuntimeError(
                'OpenSSL compiler diagnostic contains build paths: %s'
                % ', '.join(leaked)
            )
        if diagnostic != b'compiler: gcc':
            raise RuntimeError(
                'OpenSSL compiler diagnostic was not target-safe: %s'
                % diagnostic.decode('utf-8', errors='replace')
            )
