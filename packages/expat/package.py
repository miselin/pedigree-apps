
from support import buildsystem
from support import steps


class ExpatPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(ExpatPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'xz'

    def name(self):
        return 'expat'

    def version(self):
        return '2.8.4'

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
            'https://github.com/libexpat/libexpat/releases/download/'
            'R_2_8_4/expat-2.8.4.tar.xz',
            target,
            sha256='656ae1cc8da3b4ea513bb4e254f33e6243938084c0ec6239da873376b09985a7',
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self,
            srcdir,
            env,
            inplace=False,
            extra_config=(
                '--without-tests',
                '--without-examples',
                '--without-docbook',
                '--enable-shared',
                '--enable-static',
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install', inplace=False)
