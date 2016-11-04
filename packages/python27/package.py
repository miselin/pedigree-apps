
import os
import shutil

from support import buildsystem
from support import steps


class Python27Package(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(Python27Package, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'python27'

    def version(self):
        return '2.7.3'

    def build_requires(self):
        return ['libtool', 'gettext', 'libiconv', 'curl', 'openssl', 'glib',
                'zlib', 'sqlite', 'readline', 'ncurses', 'gdbm']

    def patches(self, env, srcdir):
        # posix_close patch comes from http://bugs.python.org/issue20594
        return ['Makefile.pre.in.diff', 'configure.in.diff', 'setup.py.diff',
                'posix_close.patch']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://python.org/ftp/python/%(version)s/%(urlpackage)s-%(version)s.tar.xz' % {
            'package': self.name(),
            'version': self.version(),
            'urlpackage': 'Python',
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        steps.autoreconf(srcdir, env)

        # Platform-specific modules directory, empty for us.
        os.makedirs(os.path.join(srcdir, 'Lib', 'plat-pedigree'))

        # Build host pgen and python.
        steps.run_configure(self, srcdir, env, inplace=False, host=False)
        steps.make(srcdir, env, target='Parser/pgen', inplace=False)
        steps.make(srcdir, env, target='python', inplace=False)

        pgen_source = os.path.join(steps.get_builddir(srcdir, env, False), 'Parser', 'pgen')
        python_source = os.path.join(steps.get_builddir(srcdir, env, False), 'python')

        steps.cmd(['mv', pgen_source, os.path.join(srcdir, 'hostpgen')])
        steps.cmd(['mv', python_source, os.path.join(srcdir, 'hostpython')])

        # No need for this build directory anymore.
        shutil.rmtree(steps.get_builddir(srcdir, env, False))

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env,
                            extra_config=('--without-pydebug',))

    def build(self, env, srcdir):
        hostpython = os.path.join(srcdir, 'hostpython')
        hostpgen = os.path.join(srcdir, 'hostpgen')

        steps.make(srcdir, env, extra_opts=(
            'HOSTPYTHON=' + hostpython, 'HOSTPGEN=' + hostpgen,
            'CROSS_COMPILING=yes', 'MACHDEP=pedigree',
            'BLDSHARED=%s -shared' % env['CROSS_CC']), parallel=False)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir

        hostpython = os.path.join(srcdir, 'hostpython')
        hostpgen = os.path.join(srcdir, 'hostpgen')

        steps.make(srcdir, env, target='install', extra_opts=(
            'HOSTPYTHON=' + hostpython, 'HOSTPGEN=' + hostpgen,
            'CROSS_COMPILING=yes', 'MACHDEP=pedigree',
            'BLDSHARED=%s -shared' % env['CROSS_CC']), parallel=False)
