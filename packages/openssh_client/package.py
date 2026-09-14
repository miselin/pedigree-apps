import os
import shutil

from support import buildsystem
from support import steps


SOURCE_VERSION = '10.5p1'
PACKAGE_VERSION = '10.5.1'
PROGRAMS = (
    'ssh',
    'scp',
    'sftp',
    'ssh-add',
    'ssh-agent',
    'ssh-keygen',
    'ssh-keyscan',
)
MANPAGES = (
    ('ssh.1.out', 'man1/ssh.1'),
    ('scp.1.out', 'man1/scp.1'),
    ('sftp.1.out', 'man1/sftp.1'),
    ('ssh-add.1.out', 'man1/ssh-add.1'),
    ('ssh-agent.1.out', 'man1/ssh-agent.1'),
    ('ssh-keygen.1.out', 'man1/ssh-keygen.1'),
    ('ssh-keyscan.1.out', 'man1/ssh-keyscan.1'),
    ('ssh_config.5.out', 'man5/ssh_config.5'),
)
BUILD_TARGETS = PROGRAMS + tuple(source for source, _ in MANPAGES) + (
    'ssh_config.out',
)


class OpenSshClientPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(OpenSshClientPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()

    def name(self):
        return 'openssh-client'

    def version(self):
        return PACKAGE_VERSION

    def build_requires(self):
        return ['openssl', 'zlib']

    def install_deps(self):
        return self.build_requires()

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
                '--with-zlib',
                '--with-sandbox=no',
                '--disable-pkcs11',
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
        steps.make(srcdir, env, extra_opts=BUILD_TARGETS)

    def deploy(self, env, srcdir, deploydir):
        bindir = os.path.join(deploydir, 'usr/bin')
        mandir = os.path.join(deploydir, 'usr/share/man')
        docdir = os.path.join(deploydir, 'usr/share/doc/openssh-client')
        sysconfdir = os.path.join(deploydir, 'etc/ssh')
        os.makedirs(bindir)
        os.makedirs(docdir)
        os.makedirs(sysconfdir)
        for program in PROGRAMS:
            shutil.copy2(os.path.join(srcdir, program), bindir)
        for source, destination in MANPAGES:
            target = os.path.join(mandir, destination)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(os.path.join(srcdir, source), target)
        shutil.copy2(
            os.path.join(srcdir, 'ssh_config.out'),
            os.path.join(sysconfdir, 'ssh_config'),
        )
        shutil.copy2(os.path.join(srcdir, 'LICENCE'), docdir)
