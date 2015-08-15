
import collections
import os
import tarfile


def collect_dependences(known_packages, package):
    """Collect dependencies for the given package.

    Returns:
        A list of Package objects that are required for the given package.
    """
    # Traverse the dependency chain, pulling in dependencies of our dependencies
    # and so on. This is important as we may have implicit dependencies.
    def traverse_depends(depends, pkg):
        package_depends = pkg.build_requires()
        for dependency in package_depends:
            dependent_package = known_packages[dependency]
            depends.append(dependent_package)
            traverse_depends(depends, dependent_package)

    depends = []
    traverse_depends(depends, package)

    return depends


def install_dependent_packages(all_packages, package, env):
    """Installs dependent packages into env['CHROOT_BASE']."""
    depends = collect_dependences(all_packages, package)

    # Now, create all the dependent links.
    for package in depends:
        package_filename = '%s-%s-%s.pup' % (package.name(), package.version(), env['PACKMAN_TARGET_ARCH'])
        package_path = os.path.join(env['PACKMAN_REPO'], package_filename)

        tar = tarfile.open(package_path)
        tar.extractall(path=env['CHROOT_BASE'])
        tar.close()


def sort_dependencies(packages):
    """Sorts the given packages based on dependencies.

    Returns:
        An iterable of (package_name, package) tuples.
    """

    tree = collections.defaultdict(list)
    for package_name, package in packages.items():
        _ = tree[package_name]
        for depends in package.build_requires():
            tree[depends].append(package_name)

    # Tree is now a set of <package> -> <things depending on package> pairs.
    # We need to sort the list so the package appears before everything that
    # depends on it.
    # TODO(miselin): this needs substantially more testing
    seen = set()
    result = []
    for package, deps in tree.items():
        insert = False
        for dep in deps:
            if dep in seen:
                insert = True
                break

        insertion = (package, packages[package])

        if insert:
            result.insert(0, insertion)
        else:
            result.append(insertion)

        seen.add(package)

    return result
