
import os
import requests
import shutil

from support import buildsystem
from support import steps


class PerlPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(PerlPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'perl'

    def version(self):
        return '5.16.3'

    def build_requires(self):
        return []

    def patches(self, env, srcdir):
        return []

    def options(self):
        return self._options

    def download(self, env, target):
        url = 'http://www.cpan.org/src/5.0/%(package)s-%(version)s.tar.gz' % {
            'package': self.name(),
            'version': self.version(),
        }
        steps.download(url, target)

    def prebuild(self, env, srcdir):
        # Download perlcross to perform the build.
        remote_url = 'https://github.com/arsv/perl-cross/raw/releases/perl-%(version)s-cross-0.7.4.tar.gz' % {
            'version': self.version()
        }

        resp = requests.get(remote_url, stream=True)
        if resp.status_code != 200:
            raise Exception('could not download from %r (%r)' % (
                remote_url, resp))

        perlcross = os.path.join(srcdir, 'perlcross.tar.gz')
        with open(perlcross, 'wb') as f:
            resp.raw.decode_content = True
            shutil.copyfileobj(resp.raw, f)

        # Extract the newly-created tarball.
        steps.cmd(['tar', '--strip-components=1', '-xf', perlcross], cwd=srcdir, env=env)

    def configure(self, env, srcdir):
        steps.run_configure(self, srcdir, env, paths=('prefix',),extra_config=(
            '--mode=cross', '--target=%s' % env['CROSS_TARGET']))

    def build(self, env, srcdir):
        steps.make(srcdir, env, target='perl', parallel=False)

    def deploy(self, env, srcdir, deploydir):
        steps.make(srcdir, env, target='install', parallel=False,
                   extra_opts=('DESTDIR=%s' % deploydir, '-i', '-k'))
