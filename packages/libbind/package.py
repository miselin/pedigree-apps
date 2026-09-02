# coding: utf-8

import os

from support import buildsystem
from support import steps


DISABLED_REASON = (
    "ISC libbind duplicates musl's resolver API and the forced global FHS "
    "paths would overwrite musl and BIND headers; no active port depends on "
    "it. Revive only for a concrete legacy consumer with namespaced headers "
    "and target resolver validation."
)


class LibBindPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibBindPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'gz'

    def name(self):
        return 'libbind'

    def version(self):
        return '6.0'

    def patches(self, env, srcdir):
        # resolv.h comes out by default with no #include for netinet/in.h, which
        # breaks in fun ways if it's not included by something that has already
        # included that.
        return ['resolv.h.diff']

    def build_requires(self):
        return []

    def install_deps(self):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://downloads.isc.org/isc/libbind/%s/libbind-%s.tar.gz'
            % (self.version(), self.version()),
            target,
            sha256='b98b6aa6e7c403f5a6522ffb68325785a87ea8b13377ada8ba87953a3e8cb29d',
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self,
            srcdir,
            env,
            inplace=False,
            extra_config=(
                '--with-randomdev=/dev/urandom',
                '--with-pic',
                '--with-libtool',
                '--enable-shared',
                '--enable-static',
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, inplace=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, 'install', inplace=False)
