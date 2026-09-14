import os
import shutil

from support import buildsystem
from support import steps


SOURCE_VERSION = '10.5p1'
PACKAGE_VERSION = '10.5.1'


class OpenSshSftpServerPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(OpenSshSftpServerPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()

    def name(self):
        return 'openssh-sftp-server'

    def version(self):
        return PACKAGE_VERSION

    def build_requires(self):
        return []

    def install_deps(self):
        return []

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            'https://cdn.openbsd.org/pub/OpenBSD/OpenSSH/portable/'
            'openssh-%s.tar.gz' % SOURCE_VERSION,
            target,
            sha256='d44d28a839ea9daf969cc69150fde59910b2b39361dad81a3bd6cbd19218db11',
        )

    def configure(self, env, srcdir):
        steps.run_configure(
            self,
            srcdir,
            env,
            not_paths=('libexecdir', 'sysconfdir'),
            extra_config=(
                '--libexecdir=/usr/libexec',
                '--sysconfdir=/etc/ssh',
                '--without-openssl',
                '--without-zlib',
                '--with-sandbox=no',
                '--disable-security-key',
                # musl exposes these as no-op compatibility interfaces.
                '--disable-lastlog',
                '--disable-utmp',
                '--disable-utmpx',
                '--disable-wtmp',
                '--disable-wtmpx',
                '--disable-pututline',
                '--disable-pututxline',
                '--without-shadow',
            ),
        )

    def build(self, env, srcdir):
        steps.make(srcdir, env, target='sftp-server')

    def deploy(self, env, srcdir, deploydir):
        libexecdir = os.path.join(deploydir, 'usr/libexec')
        mandir = os.path.join(deploydir, 'usr/share/man/man8')
        docdir = os.path.join(
            deploydir, 'usr/share/doc/openssh-sftp-server'
        )
        os.makedirs(libexecdir)
        os.makedirs(mandir)
        os.makedirs(docdir)
        shutil.copy2(
            os.path.join(srcdir, 'sftp-server'),
            os.path.join(libexecdir, 'sftp-server'),
        )
        shutil.copy2(os.path.join(srcdir, 'sftp-server.8'), mandir)
        shutil.copy2(os.path.join(srcdir, 'LICENCE'), docdir)
