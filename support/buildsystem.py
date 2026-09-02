import importlib.util
import logging
import os
import subprocess

from . import steps


log = logging.getLogger(__name__)


class OptionalError(NotImplementedError):
    pass


class Options:
    __anything__ = object()
    __opts__ = {
        "tarfile_format": ("bz2", "gz", "xz", "bare", "none"),
        "always_download": (True, False),
    }

    def __init__(self):
        self.tarfile_format = "gz"
        self.always_download = False

    def __setattr__(self, key, value):
        valid = self.__opts__.get(key, self.__anything__)
        if valid is not self.__anything__ and value not in valid:
            raise ValueError("bad value for %r: %r" % (key, value))
        super().__setattr__(key, value)


class Package:
    """Package metadata and build hooks used by the local ports builder."""

    def __init__(self, package_py_path):
        self._path = os.path.dirname(package_py_path)

    def name(self):
        raise NotImplementedError()

    def version(self):
        raise NotImplementedError()

    def build_requires(self):
        return []

    def install_deps(self):
        return []

    def patches(self, env, srcdir):
        raise OptionalError()

    def options(self):
        return Options()

    def download(self, env, target):
        raise OptionalError()

    def patch(self, env, srcdir):
        for patch in self.patches(env, srcdir):
            patch_path = os.path.join(self._path, "patches", patch)
            with open(patch_path, "rb") as patch_file:
                subprocess.check_call(
                    [env["PATCH"], "-p1"],
                    stdin=patch_file,
                    cwd=srcdir,
                    env=env,
                )

    def prebuild(self, env, srcdir):
        raise OptionalError()

    def configure(self, env, srcdir):
        raise OptionalError()

    def build(self, env, srcdir):
        raise OptionalError()

    def deploy(self, env, srcdir, deploydir):
        raise OptionalError()

    def postdeploy(self, env, srcdir, deploydir):
        raise OptionalError()

    def repository_prep(self, env, srcdir, deploydir):
        steps.create_package(self, deploydir, env)

    def repository(self, env, srcdir, deploydir):
        steps.upload_package(self, deploydir, env)

    def links(self, env, deploydir, cross_dir):
        raise OptionalError()

    def pkgconfig(self, env, deploydir, cross_dir):
        target_path = env["PKG_CONFIG_LIBDIR"].split(os.pathsep)[0]
        os.makedirs(target_path, exist_ok=True)
        for search_path in ("usr/lib", "usr/share"):
            deploy_path = os.path.join(deploydir, search_path, "pkgconfig")
            if not os.path.isdir(deploy_path):
                continue
            for filename in os.listdir(deploy_path):
                if not filename.endswith(".pc"):
                    continue
                source = os.path.join(deploy_path, filename)
                target = os.path.join(target_path, filename)
                if os.path.lexists(target):
                    os.unlink(target)
                os.symlink(source, target)

    def check(self, env, srcdir, deploydir):
        legacy_roots = {
            "applications",
            "config",
            "doc",
            "docs",
            "include",
            "libraries",
            "support",
        }
        found_legacy = legacy_roots.intersection(os.listdir(deploydir))
        if found_legacy:
            raise RuntimeError(
                "package installed legacy top-level paths: %s"
                % ", ".join(sorted(found_legacy))
            )

        usr_dir = os.path.join(deploydir, "usr")
        if os.path.isdir(usr_dir):
            found_legacy_usr = {"doc", "info", "man"}.intersection(
                os.listdir(usr_dir)
            )
            if found_legacy_usr:
                raise RuntimeError(
                    "package installed non-FHS /usr paths: %s"
                    % ", ".join(sorted(found_legacy_usr))
                )

def load_packages(env):
    packages = {}
    packages_dir = env["SOURCE_BASE"]
    for entry in sorted(os.listdir(packages_dir)):
        package_path = os.path.join(packages_dir, entry, "package.py")
        if not os.path.isfile(package_path):
            continue

        module_name = "pedigree_package_%s" % entry.replace("-", "_")
        spec = importlib.util.spec_from_file_location(module_name, package_path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as error:
            log.warning("%s is disabled: %s", entry, error)
            log.debug("disabled package traceback", exc_info=True)
            continue

        disabled_reason = getattr(module, "DISABLED_REASON", None)
        if disabled_reason:
            log.warning("%s is disabled: %s", entry, disabled_reason)
            continue

        candidates = [(value, False) for value in vars(module).values()]
        extra_types = getattr(module, "extra_types", {})
        if isinstance(extra_types, dict):
            candidates.extend((value, True) for value in extra_types.values())

        seen_types = set()
        for value, explicitly_exported in candidates:
            if not isinstance(value, type) or value is Package:
                continue
            if value in seen_types or not issubclass(value, Package):
                continue
            if not explicitly_exported and value.__module__ != module_name:
                continue
            seen_types.add(value)
            package = value(package_path)
            name = package.name()
            if not name:
                continue
            if name in packages:
                raise ValueError(
                    "duplicate package name %r in %s and %s"
                    % (name, packages[name]._path, package._path)
                )
            packages[name] = package

    return packages
