
import os
import networkx
import tarfile


def collect_dependences(known_packages, package):
    """Collect dependencies for the given package.

    Returns:
        A list of Package objects that are required for the given package.
    """
    # Traverse the dependency chain, pulling in dependencies of our
    # dependencies and so on. This is important as we may have implicit
    # dependencies.
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
        package_filename = '%s-%s-%s.pup' % (package.name(), package.version(),
                                             env['PACKMAN_TARGET_ARCH'])
        package_path = os.path.join(env['PACKMAN_REPO'], package_filename)

        tar = tarfile.open(package_path)
        tar.extractall(path=env['CHROOT_BASE'])
        tar.close()


def build_package_graph(packages):
    """Build a networkx.DiGraph from the given set of packages."""
    graph = networkx.DiGraph()

    for package_name, package in packages.items():
        requires = package.build_requires()
        if not requires:
            graph.add_node(package_name)

        for dependency in requires:
            graph.add_edge(package_name, dependency)

    return graph


def sort_dependencies(packages):
    """Sorts the given packages based on dependencies.

    Returns:
        An iterable of (package_name, package) tuples.
    """
    graph = build_package_graph(packages)

    # Write out a nice dot graph if we can.
    try:
        networkx.write_dot(graph, 'dependencies.dot')
    except:
        pass

    # Walk the tree to figure out the correct dependency order.
    result = networkx.topological_sort(graph, reverse=True)
    return [(package, packages[package]) for package in result]


def get_final_packages(packages):
    """Gets the list of packages that nothing depends upon.

    Returns:
        An iterable of package name strings.
    """
    graph = build_package_graph(packages)

    for node in graph.nodes():
        if not graph.predecessors(node):
            yield node
