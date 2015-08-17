from __future__ import print_function

import imp
import os
import subprocess
import sys

from . import steps


class OptionalError(NotImplementedError):
    pass


class Options(object):
    """Custom object for options with validation."""
    __anything__ = object()
    __opts__ = {
        'tarfile_format': ('bz2', 'gz', 'xz', 'bare', 'none'),
    }

    def __init__(self):
        # Set sensible defaults.
        self.tarfile_format = 'gz'

    def __setattr__(self, key, value):
        obj = Options.__opts__.get(key, Options.__anything__)
        if obj is None:
            super(Options, self).__setattr__(key, value)
        else:
            if obj is not Options.__anything__:
                if value not in obj:
                    raise ValueError('bad value for %r: %r' % (key, value))

            super(Options, self).__setattr__(key, value)


class Package(object):
    """Presents package information and hooks for each step of a build process.

    Some methods are optional, others are not.
    """

    def __init__(self, package_py_path):
        self._path = os.path.dirname(package_py_path)

    def name(self):
        """Returns the name of the package (eg, "zlib")."""
        raise NotImplementedError()

    def version(self):
        """Returns the version of the package (eg, "1.2.3")."""
        raise NotImplementedError()

    def build_requires(self):
        """Returns an iterable of packages that must build before this one."""
        return []

    def install_deps(self):
        """Returns an iterable of packages that this package should trigger an
        install for at install time."""
        return []

    def patches(self, env, srcdir):
        """Returns a list of patches that need to be applied for this build."""
        raise OptionalError()

    def options(self):
        """Returns an Options object detailing build options."""
        return Options()

    def download(self, env, target):
        """Download the source tarball to the given file."""
        raise OptionalError()

    def patch(self, env, srcdir):
        """Apply patches to the source tree.

        Automatically uses the patches from patches()."""
        patches = self.patches(env, srcdir)
        for patch in patches:
            real_patch = os.path.join('/', 'patches', patch)
            with open(real_patch, 'r') as f:
                subprocess.check_call([env['PATCH'], '-p1'], stdin=f,
                    cwd=srcdir, env=env)

    def prebuild(self, env, srcdir):
        """Performs steps needed to prepare the build."""
        raise OptionalError()

    def configure(self, env, srcdir):
        """Performs steps needed to configure the build system."""
        raise OptionalError()

    def build(self, env, srcdir):
        """Performs steps needed to actually build."""
        raise OptionalError()

    def deploy(self, env, srcdir, deploydir):
        """Performs steps needed to deploy into a target directory."""
        raise OptionalError()

    def postdeploy(self, env, srcdir, deploydir):
        """Performs steps needed after deployment completes."""
        raise OptionalError()

    def repository(self, env, srcdir, deploydir):
        """Creates a package from the deploydir."""
        steps.create_package(self, deploydir, env)

    def links(self, env, deploydir, cross_dir):
        """Performs steps needed to link headers and libraries into the
        cross-compiler tree for future builds to access."""
        raise OptionalError()

    def pkgconfig(self, env, deploydir, cross_dir):
        """Links any found pkgconfig files for the cross-toolchain."""
        target_path = env['PKG_CONFIG_LIBDIR']
        if not os.path.isdir(target_path):
            os.makedirs(target_path)

        search_paths = ['libraries', 'lib', os.path.join('usr', 'lib')]
        for search_path in search_paths:
            deploy_path = os.path.join(deploydir, search_path, 'pkgconfig')
            if not os.path.isdir(deploy_path):
                continue

            for pcfile in os.listdir(deploy_path):
                if not pcfile.endswith('.pc'):
                    continue
                pcfile_path = os.path.join(deploy_path, pcfile)
                if not os.path.isfile(pcfile_path):
                    continue

                target_pcfile_path = os.path.join(target_path, pcfile)
                if os.path.isfile(target_pcfile_path) or os.path.islink(target_pcfile_path):
                    os.unlink(target_pcfile_path)

                print(target_pcfile_path, '->', pcfile_path)
                os.symlink(pcfile_path, target_pcfile_path)


def load_packages(env):
    """Collects packages that exist.

    This is done by traversing the packages directory to find package.py files,
    importing them, and then collecting all Package subclasses.
    """
    all_packages = {}
    packages_dir = env['SOURCE_BASE']
    for entry in os.listdir(packages_dir):
        entry_path = os.path.join(packages_dir, entry)
        if not os.path.isdir(entry_path):
            continue

        module = os.path.join(entry_path, 'package.py')
        if os.path.exists(module):
            try:
                loaded = imp.load_source('pedigree_%s' % entry, module)
            except Exception as e:
                print('%s failed to load (%s), ignoring.' % (entry, e), file=sys.stderr)

    # Collect subclasses of packages.
    collected_packages = Package.__subclasses__()
    for package_cls in collected_packages:
        package = package_cls(sys.modules[package_cls.__module__].__file__)
        if package.name():
            all_packages[package.name()] = package

    return all_packages
