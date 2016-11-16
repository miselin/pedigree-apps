
import os
import shutil

from support import buildsystem
from support import steps


class PedigreeUpdaterPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super(PedigreeUpdaterPackage, self).__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self.tarfile_format = 'gz'

    def name(self):
        return 'pedigree-updater'

    def version(self):
        return '0.1'

    def prebuild(self, env, srcdir):
        pup_source = os.path.join(env['APPS_BASE'], 'pup')
        shutil.rmtree(srcdir)
        shutil.copytree(pup_source, srcdir)

    def build(self, env, srcdir):
        steps.cmd(['python', 'setup.py', 'build'], cwd=srcdir, env=env)

    def deploy(self, env, srcdir, deploydir):
        site_packages = os.path.join(deploydir, 'libraries', 'python2.7', 'site-packages')
        apps_dir = os.path.join(deploydir, 'applications')
        pup_dir = os.path.join(deploydir, 'support', 'pup')

        for path in (site_packages, apps_dir, pup_dir):
            if not os.path.isdir(path):
                os.makedirs(path)

        env['PYTHONPATH'] = site_packages
        steps.cmd(['python', 'setup.py', 'install',
                   '--prefix', deploydir,
                   '--install-lib', site_packages,
                   '--install-scripts', apps_dir,
                   '--install-data', pup_dir],
                  cwd=srcdir, env=env)
