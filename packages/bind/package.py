
import os

from support import buildsystem
from support import steps


class BindPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(BindPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'gz'

    def name(self):
        return 'bind'

    def version(self):
        # BIND 9.16 and newer require libuv. 9.11.37 is the final release
        # compatible with the dependencies currently available on Pedigree.
        return '9.11.37'

    def build_requires(self):
        return ['zlib']

    def install_deps(self):
        return ['zlib']

    def patches(self, env, srcdir):
        return ['pedigree-truncate.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://downloads.isc.org/isc/bind9/%s/bind-%s.tar.gz'
            % (self.version(), self.version()),
            target,
            sha256='0d8efbe7ec166ada90e46add4267b7e7c934790cba9bd5af6b8380a4fbfb5aff',
        )

    def configure(self, env, srcdir):
        env['BUILD_CC'] = 'gcc'
        # BIND's probe links musl's GNU-only strcasestr without checking that
        # the normal target feature profile declares it. Select BIND's bundled
        # portable implementation instead.
        env['ac_cv_func_strcasestr'] = 'no'
        # BIND retries sigwait() through several libraries after the normal
        # function probe.  Musl exposes wrappers for these signal waits, but
        # Pedigree cannot translate the backing syscalls yet.
        env['ac_cv_func_sigwait'] = 'no'
        env['ac_cv_lib_c_sigwait'] = 'no'
        env['ac_cv_lib_pthread_sigwait'] = 'no'
        env['ac_cv_lib_pthread__Psigwait'] = 'no'
        env['ac_cv_lib_c_r_sigwait'] = 'no'
        steps.run_configure(
            self,
            srcdir,
            env,
            inplace=False,
            extra_config=(
                # Pedigree does not yet implement sigwait() or sigsuspend().
                # BIND's supported non-threaded event loop handles signals
                # without either interface.
                '--disable-threads',
                '--disable-atomic',
                '--disable-linux-caps',
                '--with-randomdev=/dev/urandom',
                '--without-python',
                '--without-openssl',
                '--with-zlib=%s/usr' % env['PORTS_SYSROOT'],
                '--with-geoip=no',
                '--with-geoip2=no',
                '--with-gssapi=no',
                '--with-lmdb=no',
                '--with-libxml2=no',
                '--with-libjson=no',
                '--with-readline=no',
                '--with-idnkit=no',
                '--with-libidn2=no',
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        steps.make(
            srcdir,
            env,
            target='install',
            inplace=False,
            extra_opts=('DESTDIR=%s' % deploydir,),
        )

    def postdeploy(self, env, srcdir, deploydir):
        config = os.path.join(deploydir, 'usr', 'bin', 'isc-config.sh')
        with open(config, encoding='utf-8') as source:
            contents = source.read()
        contents = contents.replace(env['PORTS_SYSROOT'], '')
        with open(config, 'w', encoding='utf-8') as destination:
            destination.write(contents)
