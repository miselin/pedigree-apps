import os
import re

from support import buildsystem
from support import steps


class AprPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(AprPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = 'bz2'

    def name(self):
        return 'apr'

    def version(self):
        return '1.7.6'

    def build_requires(self):
        return []

    def install_deps(self):
        # apr-1-config uses sed to parse command-line assignments.
        return ['sed']

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://downloads.apache.org/apr/apr-%s.tar.bz2'
            % self.version(),
            target,
            sha256=(
                '49030d92d2575da735791b496dc322f3ce5cff9494779ba8cc28c7f46c5deb32'
            ),
        )

    def configure(self, env, srcdir):
        env['CC_FOR_BUILD'] = '/usr/bin/cc'
        env['CFLAGS_FOR_BUILD'] = '-O2'

        # Pedigree provides mmap-backed shared memory, but its process-shared
        # pthread mutexes are not implemented and file locks are currently
        # compatibility stubs.  Select the only compiling Unix backend; APR
        # consumers must avoid inter-process contention until target locking
        # is real.  The Apache port documents its supported `httpd -X` mode.
        env['apr_lock_method'] = 'USE_FCNTL_SERIALIZE'
        env['apr_cv_process_shared_works'] = 'no'
        env['apr_cv_mutex_robust_shared'] = 'no'
        env['apr_cv_tcp_nodelay_with_cork'] = 'no'
        env['ac_cv_o_nonblock_inherited'] = 'no'
        env['ac_cv_tcp_nodelay_inherited'] = 'no'
        env['ac_cv_file__dev_zero'] = 'yes'
        env['ac_cv_mmap__dev_zero'] = 'yes'
        env['ac_cv_strerror_r_rc_int'] = 'yes'

        # APR 1.7 treats the presence of --disable-{posix,sysv}-shm as an
        # enable override.  Cache unavailable shared-memory and locking APIs
        # instead so APR only advertises the mmap and fcntl compatibility
        # paths selected here.
        env['ac_cv_func_shm_open'] = 'no'
        env['ac_cv_func_shm_unlink'] = 'no'
        env['ac_cv_func_shmget'] = 'no'
        env['ac_cv_func_shmat'] = 'no'
        env['ac_cv_func_shmdt'] = 'no'
        env['ac_cv_func_shmctl'] = 'no'
        env['ac_cv_func_flock'] = 'no'
        env['ac_cv_func_semget'] = 'no'
        env['ac_cv_func_semctl'] = 'no'
        env['ac_cv_func_semop'] = 'no'
        env['ac_cv_func_semtimedop'] = 'no'

        steps.run_configure(
            self,
            srcdir,
            env,
            inplace=False,
            extra_config=(
                '--enable-threads',
                '--disable-dso',
                '--disable-ipv6',
                '--disable-timedlocks',
                '--enable-shared',
                '--enable-static',
                '--includedir=/usr/include/apr-1',
                '--with-installbuilddir=/usr/share/apr-1/build',
                '--with-devrandom=/dev/urandom',
            ),
        )

    def build(self, env, srcdir):
        steps.make(
            srcdir,
            env,
            inplace=False,
            extra_opts=(
                'CC_FOR_BUILD=/usr/bin/cc',
                'CFLAGS_FOR_BUILD=-O2',
            ),
        )

    def deploy(self, env, srcdir, deploydir):
        steps.make(
            srcdir,
            env,
            target='install',
            inplace=False,
            extra_opts=('DESTDIR=%s' % deploydir,),
        )

    def postdeploy(self, env, srcdir, deploydir):
        installbuilddir = os.path.join(
            deploydir, 'usr', 'share', 'apr-1', 'build'
        )
        metadata = [
            os.path.join(deploydir, 'usr', 'bin', 'apr-1-config'),
            os.path.join(deploydir, 'usr', 'lib', 'libapr-1.la'),
            os.path.join(
                deploydir, 'usr', 'lib', 'pkgconfig', 'apr-1.pc'
            ),
        ]
        for root, _, filenames in os.walk(installbuilddir):
            metadata.extend(os.path.join(root, name) for name in filenames)

        replacements = []
        for variable in (
            'CROSS_CC',
            'CROSS_CXX',
            'CROSS_CPP',
            'CROSS_AS',
            'CROSS_LD',
            'CROSS_AR',
            'CROSS_RANLIB',
            'CROSS_STRIP',
        ):
            value = env.get(variable)
            if value:
                replacements.append((value, os.path.basename(value)))
        builddir = steps.get_builddir(srcdir, env, False)
        replacements.extend(
            (
                (
                    os.path.realpath(builddir),
                    '/usr/share/apr-1/build',
                ),
                (
                    os.path.realpath(srcdir),
                    '/usr/share/apr-1/build',
                ),
                (builddir, '/usr/share/apr-1/build'),
                (srcdir, '/usr/share/apr-1/build'),
                (env.get('PORTS_SYSROOT', ''), ''),
                (env.get('TARGET_SYSROOT', ''), ''),
                (env.get('APPS_BASE', ''), ''),
                (env.get('CROSS_BASE', ''), '/usr'),
            )
        )

        for path in metadata:
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding='utf-8') as source:
                    contents = source.read()
            except UnicodeDecodeError:
                continue
            for old, new in replacements:
                if old:
                    contents = contents.replace(old, new)
            if path.endswith('.la'):
                contents = contents.replace('//usr/', '/usr/')
                contents = contents.replace('-L/', '-L=/')
                contents = contents.replace('-R/', '-R=/')
                contents = re.sub(
                    r"(?<![=A-Za-z0-9_])/(usr|lib)/([^ \t'\"\n]+\.la)",
                    r'=/\1/\2',
                    contents,
                )
            if os.path.basename(path) == 'libtool':
                contents = re.sub(
                    r'^sys_lib_search_path_spec=.*$',
                    'sys_lib_search_path_spec="/lib /usr/lib"',
                    contents,
                    flags=re.MULTILINE,
                )
            with open(path, 'w', encoding='utf-8') as destination:
                destination.write(contents)
