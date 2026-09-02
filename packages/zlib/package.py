
from support import buildsystem
from support import steps


class ZlibPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(ZlibPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'zlib'

    def version(self):
        return '1.3.2'

    def build_requires(self):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://zlib.net/zlib-%s.tar.xz' % self.version(),
            target,
            sha256='d7a0654783a4da529d1bb793b7ad9c3318020af77667bcae35f95d0e42a792f3',
        )

    def configure(self, env, srcdir):
        env['CC'] = env['CROSS_CC']
        env['LD'] = env['CROSS_LD']
        env['LDSHARED'] = (
            '%s -shared %s -Wl,-soname,libz.so.1,--version-script,zlib.map'
            % (env['CROSS_LD'], env['LDFLAGS'])
        )
        steps.run_configure(self, srcdir, env, host=False,
            paths=('prefix', 'libdir', 'includedir'))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, 'install')

    def links(self, env, deploydir, cross_dir):
        libs = ['libz.a', 'libz.so', 'libz.so.1', 'libz.so.1.3.2']
        headers = ['zconf.h', 'zlib.h']
        steps.symlinks(deploydir, cross_dir, libs=libs, headers=headers)
