
from support import buildsystem
from support import steps


class DropbearPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(DropbearPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'bz2'

    def name(self):
        return 'dropbear'

    def version(self):
        return '2026.94'

    def release_version(self):
        return self.version() + '.1'

    def build_requires(self):
        return ['zlib']

    def install_deps(self):
        return ['zlib']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://matt.ucc.asn.au/dropbear/releases/'
            'dropbear-%s.tar.bz2' % self.version(),
            target,
            sha256='e098034a843699200c8c977a991fff73159735bf795d5f72ef672c41a6b1ae81',
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self,
            srcdir,
            env,
            inplace=False,
            extra_config=(
                '--enable-zlib',
                '--enable-bundled-libtom',
                # musl exposes utmp interfaces as no-op compatibility stubs;
                # keep accounting disabled until Pedigree implements it.
                '--disable-lastlog',
                '--disable-utmp',
                '--disable-utmpx',
                '--disable-wtmp',
                '--disable-wtmpx',
                '--disable-loginfunc',
                '--disable-pututline',
                '--disable-pututxline',
            ),
        )

    def build(self, env, srcdir):
        steps.make(
            srcdir,
            env,
            inplace=False,
            extra_opts=('PROGRAMS=dropbear dbclient dropbearkey dropbearconvert scp',),
        )

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(
            srcdir,
            env,
            target='install',
            inplace=False,
            extra_opts=('PROGRAMS=dropbear dbclient dropbearkey dropbearconvert scp',),
        )
