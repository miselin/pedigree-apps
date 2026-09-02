
from support import buildsystem
from support import steps


class AutoconfPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(AutoconfPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'xz'

    def name(self):
        return 'autoconf'

    def version(self):
        return '2.73'

    def install_deps(self):
        return ['m4', 'perl']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'https://ftp.gnu.org/gnu/autoconf/autoconf-%s.tar.xz' % (
            self.version(),)
        steps.download(
            url, target,
            sha256='9fd672b1c8425fac2fa67fa0477b990987268b90ff36d5f016dae57be0d6b52e')

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, inplace=False)

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False, parallel=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install', inplace=False, parallel=False)
