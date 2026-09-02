
from support import buildsystem
from support import steps


class LibiconvPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibiconvPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'libiconv'

    def version(self):
        return '1.19'

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'https://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(
            url, target,
            sha256='88dd96a8c0464eca144fc791ae60cd31cd8ee78321e67397e25fc095c4a19aa6')

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, extra_config=(
            '--disable-shared', '--enable-static',
            '--enable-cross-guesses=conservative'), inplace=False)

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, 'install', inplace=False)

    def links(self, env, deploydir, cross_dir):
        libs = ['libcharset.a', 'libiconv.a']
        headers = ['libcharset.h', 'localcharset.h', 'iconv.h']

        steps.symlinks(deploydir, cross_dir, libs=libs, headers=headers)
