# coding: utf-8

import os

from support import buildsystem
from support import steps


UPSTREAM_VERSION = '6.0'

DISABLED_REASON = (
    "ISC libbind 6.0 is the final standalone release and duplicates musl's "
    "resolver implementation. Its install replaces global resolv.h, netdb.h, "
    "and arpa/nameser.h headers; no active port requires that conflicting "
    "ABI, so it cannot safely share the target sysroot."
)


class LibBindPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibBindPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'gz'

    def name(self):
        return 'libbind'

    def version(self):
        return UPSTREAM_VERSION

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
