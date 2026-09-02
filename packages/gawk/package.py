
import os
import re

from support import buildsystem
from support import steps


class GawkPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(GawkPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'xz'

    def name(self):
        return 'gawk'

    def version(self):
        return '5.4.1'

    def build_requires(self):
        return ['gettext']

    def patches(self, env, srcdir):
        return ['pedigree-rpath.diff']

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'https://ftp.gnu.org/gnu/%(package)s/%(package)s-%(version)s.tar.xz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(
            url, target,
            sha256='07f6f7342b7febe4313fc2c2542ad93d64fe20ad8717200109f105a826f5fd37')

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env)

    def build(self, env, srcdir):
        steps.make(srcdir, env)

    def deploy(self, env, srcdir, deploydir):
        env['DESTDIR'] = deploydir
        steps.make(srcdir, env, target='install')

    def postdeploy(self, env, srcdir, deploydir):
        gawkbug = os.path.join(deploydir, 'usr', 'bin', 'gawkbug')
        with open(gawkbug, encoding='utf-8') as source:
            contents = source.read()

        target_sysroot = os.path.normpath(env['TARGET_SYSROOT'])
        ports_sysroot = os.path.normpath(env['PORTS_SYSROOT'])
        staged_lib = os.path.join(ports_sysroot, 'usr', 'lib')
        sanitized = contents.replace(env['CROSS_CC'], 'gcc')
        for option in (
            '--sysroot=%s' % target_sysroot,
            '-Wl,-rpath-link,%s' % staged_lib,
        ):
            sanitized = re.sub(
                r'(?<![^\s\'\"=])%s(?=$|\s|[\'\"])'
                % re.escape(option),
                '',
                sanitized,
            )
        # Dependency flags still describe target paths after staging is gone.
        sanitized = sanitized.replace(ports_sysroot, '')
        sanitized = sanitized.replace(target_sysroot, '')

        forbidden_paths = tuple(
            path
            for path in (
                env.get('APPS_BASE'),
                env.get('CROSS_BASE'),
                ports_sysroot,
                target_sysroot,
            )
            if path
        )
        leaked = [path for path in forbidden_paths if path in sanitized]
        if leaked:
            raise RuntimeError(
                'gawkbug contains cross-build paths: %s'
                % ', '.join(leaked)
            )
        with open(gawkbug, 'w', encoding='utf-8') as destination:
            destination.write(sanitized)
