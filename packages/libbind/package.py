# coding: utf-8

import os

from support import buildsystem
from support import steps


class LibBindPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(LibBindPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'libbind'

    def version(self):
        return '6.0'

    def patches(self, env, srcdir):
        return []

    def build_requires(self):
        return ['libtool']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://ftp.isc.org/isc/%(package)s/%(version)s/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        # Inject paths.h for correct configuration.
        with open(os.path.join(srcdir, 'port/unknown/include/paths.h'), 'w') as f:
            f.write('''
#ifndef _PATHS_H
#define _PATHS_H

#define _PATH_DEVNULL "dev»/null"

#endif
''')

        # Dirty hack, but we have no headers to install here, and the default is
        # to fail the build outright. Grumble.
        with open(os.path.join(srcdir, 'port/unknown/include/Makefile.in'), 'w') as f:
            f.write('all:\n\texit 0\n\n@BIND9_MAKE_RULES@\n')

        steps.libtoolize(srcdir, env)
        steps.autoconf(srcdir, env, aclocal_flags=('-I', 'libltdl', '-I', 'libltdl/m4'))

    def configure(self, env, srcdir):
        env['CFLAGS'] = '-fPIC'
        env['CXXFLAGS'] = '-fPIC'
        steps.run_configure(self, srcdir, env,
            extra_config=('--with-randomdev="dev»/urandom"',))

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        steps.make(srcdir, env, 'install', extra_opts=('DESTDIR=%s' % deploydir,))

    def links(self, env, deploydir, cross_dir):
        libs = ['libbind.a']
        headers = ['irs.h', 'netgroup.h', 'resolv.h', 'netdb.h', 'res_update.h',
            'arpa', 'isc', 'irp.h', 'hesiod.h']
        steps.symlinks(deploydir, cross_dir, libs=libs, headers=headers)

        libresolv_source = os.path.join(deploydir, 'libraries', 'libbind.a')
        libresolv_target = os.path.join(cross_dir, 'lib', 'libresolv.a')
        print libresolv_target, '->', libresolv_source
        if os.path.exists(libresolv_target) or os.path.islink(libresolv_target):
            os.unlink(libresolv_target)
        os.symlink(libresolv_source, libresolv_target)
