
import os
import re

from support import buildsystem
from support import steps


class LibgmpPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibgmpPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'xz'

    def name(self):
        return 'libgmp'

    def version(self):
        return '6.3.0'

    def build_requires(self):
        return []

    def install_deps(self):
        return []

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://gmplib.org/download/gmp/gmp-%s.tar.xz'
            % self.version(),
            target,
            sha256='a3c2b80201b89e68616f4ad30bc66aee4927c3ce50e33929ca819d5c43538898',
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self,
            srcdir,
            env,
            inplace=False,
            extra_config=('--enable-shared', '--enable-static'),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install', inplace=False)

    def postdeploy(self, env, srcdir, deploydir):
        header = os.path.join(deploydir, 'usr', 'include', 'gmp.h')
        if not os.path.isfile(header):
            raise RuntimeError('GMP development metadata was not installed')

        with open(header, encoding='utf-8') as metadata:
            contents = metadata.read()

        compiler = '#define __GMP_CC "%s"' % env['CROSS_CC']
        if contents.count(compiler) != 1:
            raise RuntimeError('GMP compiler metadata was not as expected')

        cflags = re.findall(
            r'^#define __GMP_CFLAGS .+$', contents, re.MULTILINE
        )
        if len(cflags) != 1:
            raise RuntimeError('GMP compiler flags metadata was not installed')

        sanitized = contents.replace(
            compiler, '#define __GMP_CC "gcc"', 1
        )
        if cflags[0] not in sanitized:
            raise RuntimeError('GMP compiler flags metadata changed')

        leaked = [
            value
            for value in (env.get('CROSS_BASE'), env.get('PORTS_SYSROOT'))
            if value and value in sanitized
        ]
        if leaked:
            raise RuntimeError(
                'GMP development metadata contains build paths: %s'
                % ', '.join(leaked)
            )

        with open(header, 'w', encoding='utf-8') as metadata:
            metadata.write(sanitized)
