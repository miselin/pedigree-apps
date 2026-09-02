import os
import shutil


def collect_dependencies(known_packages, package):
    result = []
    visited = set()

    def visit(name):
        if name in visited:
            return
        if name not in known_packages:
            raise KeyError(
                'package "%s" requires unknown package "%s"'
                % (package.name(), name)
            )
        visited.add(name)
        dependency = known_packages[name]
        for child in dependency.build_requires():
            visit(child)
        result.append(dependency)

    for dependency_name in package.build_requires():
        visit(dependency_name)
    return result


def sort_dependencies(packages):
    result = []
    permanent = set()
    temporary = []

    def visit(name):
        if name in permanent:
            return
        if name in temporary:
            cycle = temporary[temporary.index(name) :] + [name]
            raise ValueError("dependency cycle: %s" % " -> ".join(cycle))
        if name not in packages:
            raise KeyError('unknown package dependency "%s"' % name)

        temporary.append(name)
        for dependency in packages[name].build_requires():
            visit(dependency)
        temporary.pop()
        permanent.add(name)
        result.append((name, packages[name]))

    for package_name in sorted(packages):
        visit(package_name)
    return result


def select_with_dependencies(packages, requested):
    selected = set()
    for name in requested:
        if name not in packages:
            raise KeyError('unknown package "%s"' % name)
        selected.add(name)
        selected.update(dep.name() for dep in collect_dependencies(packages, packages[name]))
    return [item for item in sort_dependencies(packages) if item[0] in selected]


def prepare_sysroot(known_packages, package, env):
    sysroot = os.path.join(env["BUILD_BASE"], "sysroots", package.name())
    shutil.rmtree(sysroot, ignore_errors=True)
    os.makedirs(sysroot)

    for dependency in collect_dependencies(known_packages, package):
        package_root = os.path.join(
            env["OUTPUT_BASE"], dependency.name(), dependency.version(), "root"
        )
        completion_marker = os.path.join(
            os.path.dirname(package_root), ".complete"
        )
        if not os.path.isdir(package_root) or not os.path.isfile(completion_marker):
            raise RuntimeError(
                'dependency "%s" has not completed a build; expected %s and %s'
                % (dependency.name(), package_root, completion_marker)
            )
        shutil.copytree(
            package_root, sysroot, dirs_exist_ok=True, symlinks=True
        )

    result = env.copy()
    result["PORTS_SYSROOT"] = sysroot
    include_dir = os.path.join(sysroot, "usr", "include")
    library_dir = os.path.join(sysroot, "usr", "lib")
    result["CPPFLAGS"] = "-I%s" % include_dir
    result["LDFLAGS"] = "%s -L%s -Wl,-rpath-link,%s" % (
        env["LDFLAGS"],
        library_dir,
        library_dir,
    )
    result["PKG_CONFIG_SYSROOT_DIR"] = sysroot
    result["PKG_CONFIG_LIBDIR"] = os.pathsep.join(
        (
            os.path.join(library_dir, "pkgconfig"),
            os.path.join(sysroot, "usr", "share", "pkgconfig"),
        )
    )
    return result


def get_final_packages(packages):
    dependencies = {
        dependency
        for package in packages.values()
        for dependency in package.build_requires()
    }
    for name in sorted(set(packages) - dependencies):
        yield name
