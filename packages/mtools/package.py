
from support import buildsystem
from support import steps


class MtoolsPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(MtoolsPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'gz'

    def name(self):
        return 'mtools'

    def version(self):
        return '4.0.49'

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
            'https://ftp.gnu.org/gnu/mtools/mtools-%s.tar.gz'
            % self.version(),
            target,
            sha256='10cd1111da87bf2400a380c1639a6cba8bfb937a24f9c51f5f88d393ae5f6f76',
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self,
            srcdir,
            env,
            inplace=False,
            extra_config=(
                '--disable-xdf',
                '--disable-vold',
                '--disable-new-vold',
                '--disable-floppyd',
                '--without-x',
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(
            srcdir,
            env,
            target='install',
            inplace=False,
            parallel=False,
        )
