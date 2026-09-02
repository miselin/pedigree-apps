
from support import buildsystem
from support import steps


class Sqlite(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(Sqlite, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'gz'

    def name(self):
        return 'sqlite'

    def version(self):
        return '3.53.4'

    def build_requires(self):
        return []

    def install_deps(self):
        return []

    def patches(self, env, srcdir):
        return ['pedigree-cli-syscalls.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        source_version = '3530400'
        steps.download(
            'https://www.sqlite.org/2026/sqlite-autoconf-%s.tar.gz'
            % source_version,
            target,
            sha256='0e9483900e92cd5de8fd48d16bf9200145a61f7fd5be542a5ac81d8a9516eb9c',
        )

    def configure(self, env, srcdir):
        env['CC_FOR_BUILD'] = 'gcc'
        steps.run_configure(
            self,
            srcdir,
            env,
            inplace=False,
            paths=('prefix',),
            extra_config=(
                '--disable-readline',
                '--enable-shared',
                '--enable-static',
                '--soname=legacy',
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install', inplace=False)
