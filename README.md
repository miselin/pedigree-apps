pedigree-apps
=

The purpose for pedigree-apps is mainly to provide a central location for all files and folders relating to ported applications for Pedigree (https://www.pedigree-project.org)

A buildbot (http://build.pedigree-project.org) builds this repository nightly, deploying built packages to the main pup repository at http://pup.pedigree-project.org.

The layout of this repository is as follows:

- packages
    - Package definitions and scripts.
- newpacks
    - Output from builds will go here, under an architecture-specific directory.
- downloads
    - Download cache - delete a file if it exists here to force a redownload for
    the next build.
- environment.py
    - Standard environment configuration.

Each package contains a single script, `package.py`, in which hooks are defined for each particular build phase. The `package.py` also describes additional steps such as the download of the package's source archive, and metadata such as the package name and version (and dependencies).

Builds are performed in a chroot and therefore dependencies should be listed correctly to ensure the necessary headers and libraries for your packages are present at the time of your build.

Getting Started
=

You'll need the following to make `pedigree-apps` work:

* Python `virtualenv` (check for system packages or otherwise `pip install virtualenv`).
* A working Pedigree installation, that builds in full. This is needed to extract `libc` and other libraries from the build.
* libfakechroot.so

First-time installation may need to create a file, `local_environment.py`, alongside `environment.py`; this might look like:

```
import functools

from support.util import expand


def modify_environment(env):
    _expand = functools.partial(expand, env)

    env['PEDIGREE_BASE'] = _expand('$HOME/stuff/pedigree')
    env['APPS_BASE'] = _expand('$HOME/stuff/pedigree-apps')

    env['UNPRIVILEGED_UID'] = '10000'
    env['UNPRIVILEGED_GID'] = '10000'

    env['CCACHE_TARGET_DIR'] = '/mnt/ram/ccache'
```

This is simply overriding the defaults set in `environment.py` with the correct configuration for your environment.

You will also need a virtualenv:

`$ virtualenv venv --system-site-packages`

Then, you simply need to:

```
$ source venv/bin/activate
$ ./buildPackages.sh [target]
```

`[target]` can be `amd64` or `arm`, the support for which depends on which architecture your Pedigree build was made for.

This will:

* Install needed Python packages (via `pip`, in the virtualenv - this doesn't touch your system Python)
* Install `pup` to the virtualenv for package creation and registration
* Create a build chroot (this step requires `sudo` elevation)
* Perform the build

The build itself will figure out what to build and build packages. If you have `pydot` installed, this will emit `dependencies.dot` which shows the dependencies between packages.

Each built package will have the general form `$package-$version.pup` and be deposited in `pup/package_repo`, alongside a `packages.pupdb` database which stores metadata about packages. The `package_repo` directory is designed to be able to be published via HTTP and then used as a repository for `pup` installations.

pup
=

This repository also contains the main source for the Pedigree UPdater, or pup for short. pup provides a cross-platform way to install packages, and is especially useful for creating disk images for Pedigree cross-builds with.

A utility script, `run_pup.sh`, is provided to facilitate running `pup` by hand.

Python tests
=
Much of pedigree-apps is implemented using custom Python scripts. These can be tested by running `./runtests.sh` which will also do a full lint of the Python source code.

SUPPORT
=

For support with the pedigree-apps repository, add a tracker item at http://www.pedigree-project.org/projects/pedigree-apps or alternatively raise your question in `#pedigree` on irc.freenode.net.
