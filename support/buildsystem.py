

class OptionalError(NotImplementedError):
    pass


class Options(object):
    """Custom object for options with validation."""
    __anything__ = object()
    __opts__ = {
        'tarball_format': ('bz2', 'gz', 'xz', 'bare', 'none'),
    }

    def __init__(self):
        # Set sensible defaults.
        self.tarball_format = 'gz'

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

    def patch(self, env, target):
        """Apply patches to the source tree.

        Automatically uses the patches from patches()."""
        pass  # Do this.

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

    def links(self, env, deploydir, cross_dir):
        """Performs steps needed to link headers and libraries into the
        cross-compiler tree for future builds to access."""
        raise OptionalError()
