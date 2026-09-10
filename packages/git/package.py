
import pathlib

from support import buildsystem
from support import steps


MAKE_OPTIONS = (
    'FSMONITOR_DAEMON_BACKEND=',
    'FSMONITOR_OS_SETTINGS=',
    'NO_GETTEXT=YesPlease',
    'NO_PERL=YesPlease',
    'NO_PYTHON=YesPlease',
    'NO_RUST=YesPlease',
    'NO_TCLTK=YesPlease',
)


def _make_options(env):
    curl_config = pathlib.Path(
        env["PORTS_SYSROOT"], "usr", "bin", "curl-config"
    )
    return MAKE_OPTIONS + ("CURL_CONFIG=%s" % curl_config,)


class GitPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(GitPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'xz'

    def name(self):
        return 'git'

    def version(self):
        return '2.55.0'

    def build_requires(self):
        return ['zlib', 'libiconv', 'curl', 'openssl', 'expat']

    def install_deps(self):
        return self.build_requires()

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://www.kernel.org/pub/software/scm/git/'
            'git-%s.tar.xz' % self.version(),
            target,
            sha256='457fdb04dc8728e007d4688695e6912e6f680727920f2a40bf11eacc17505357',
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self,
            srcdir,
            env,
            extra_config=(
                'ac_cv_fread_reads_directories=no',
                'ac_cv_iconv_omits_bom=no',
                'ac_cv_snprintf_returns_bogus=no',
                '--without-tcltk',
                '--with-openssl',
                '--with-curl',
                '--with-expat',
                '--with-iconv',
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, extra_opts=_make_options(env))

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(
            srcdir,
            env,
            target='install',
            extra_opts=_make_options(env),
        )

    def postdeploy(self, env, srcdir, deploydir):
        pathlib.Path(
            deploydir,
            "usr/share/git-core/templates/hooks/fsmonitor-watchman.sample",
        ).unlink(missing_ok=True)
