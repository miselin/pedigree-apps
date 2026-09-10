import importlib.util
import logging
import os
import shlex
import stat
import subprocess

from . import steps


log = logging.getLogger(__name__)


# The target image contract requires these two packages before ordinary ports
# are installed. Keeping the baseline narrow avoids cycles such as bash ->
# readline -> ncurses -> /bin/sh while leaving other interpreters as explicit
# runtime dependencies.
BASE_RUNTIME_PACKAGES = ("bash", "coreutils")
_BASE_SCRIPT_INTERPRETERS = {"bash", "sh"}
_SCRIPT_INTERPRETER_PROVIDERS = {
    "awk": "gawk",
    "gawk": "gawk",
    "lua": "lua",
    "perl": "perl",
    "python": "python3",
    "python3": "python3",
    "slsh": "slang",
}


def _interpreter_name(words):
    interpreter_path = words[0]
    if not interpreter_path.startswith(("/bin/", "/usr/bin/")):
        raise RuntimeError(
            "non-FHS executable script interpreter: %s" % interpreter_path
        )
    interpreter = os.path.basename(interpreter_path)
    if interpreter != "env":
        return interpreter

    arguments = words[1:]
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == "--":
            index += 1
            break
        if argument in ("-u", "--unset", "-C", "--chdir"):
            index += 2
            continue
        if argument == "-S" or argument == "--split-string":
            index += 1
            break
        if argument.startswith("-") or (
            "=" in argument and not argument.startswith("/")
        ):
            index += 1
            continue
        break
    if index >= len(arguments):
        raise RuntimeError("/usr/bin/env shebang has no interpreter")
    interpreter_path = arguments[index]
    if "/" in interpreter_path and not interpreter_path.startswith(
        ("/bin/", "/usr/bin/")
    ):
        raise RuntimeError(
            "non-FHS executable script interpreter: %s" % interpreter_path
        )
    return os.path.basename(interpreter_path)


def _script_runtime_provider(first_line):
    try:
        words = shlex.split(first_line[2:].decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise RuntimeError("invalid executable script shebang") from error
    if not words:
        raise RuntimeError("executable script shebang has no interpreter")

    interpreter = _interpreter_name(words)
    if interpreter in _BASE_SCRIPT_INTERPRETERS:
        return None
    if interpreter.startswith("python3.") and interpreter[8:].isdigit():
        return "python3"
    try:
        return _SCRIPT_INTERPRETER_PROVIDERS[interpreter]
    except KeyError as error:
        raise RuntimeError(
            "unsupported executable script interpreter: %s" % interpreter
        ) from error


def check_script_runtime(package, deploydir):
    for root, _, filenames in os.walk(deploydir):
        for filename in filenames:
            path = os.path.join(root, filename)
            if os.path.islink(path):
                continue
            relative = os.path.relpath(path, deploydir).replace(os.sep, "/")
            if relative.startswith("usr/share/doc/"):
                continue
            mode = stat.S_IMODE(os.stat(path).st_mode)
            if not mode & 0o111:
                continue
            with open(path, "rb") as artifact:
                first_line = artifact.readline(4096)
            if not first_line.startswith(b"#!"):
                continue

            try:
                provider = _script_runtime_provider(first_line)
            except RuntimeError as error:
                raise RuntimeError("%s in %s" % (error, relative)) from error
            if (
                provider
                and provider != package.name()
                and provider not in package.install_deps()
            ):
                raise RuntimeError(
                    "executable script %s requires runtime provider %s"
                    % (relative, provider)
                )


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
                    [env["PATCH"], "--batch", "--fuzz=0", "-p1"],
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
            "system",
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

        check_script_runtime(self, deploydir)

        forbidden_paths = tuple(
            path
            for path in (env.get("APPS_BASE"), env.get("CROSS_BASE"))
            if path
        )
        readelf = os.path.join(
            env.get("CROSS_BASE", ""),
            "bin",
            env.get("CROSS_TARGET", "") + "-readelf",
        )
        for root, _, filenames in os.walk(deploydir):
            for filename in filenames:
                path = os.path.join(root, filename)
                if os.path.islink(path):
                    target = os.readlink(path)
                    leaked = [
                        value for value in forbidden_paths if value in target
                    ]
                    if leaked:
                        raise RuntimeError(
                            "package symlink contains build path in %s: %s"
                            % (path, target)
                        )
                    continue
                with open(path, "rb") as artifact:
                    prefix = artifact.read(4)
                metadata = prefix.startswith(b"#!") or (
                    filename.endswith((".la", ".pc", ".cmake"))
                    or filename.endswith("-config")
                )
                if metadata:
                    with open(path, "rb") as artifact:
                        content = artifact.read()
                    leaked = [
                        value for value in forbidden_paths
                        if value.encode() in content
                    ]
                    if leaked:
                        raise RuntimeError(
                            "package metadata contains build paths in %s: %s"
                            % (path, ", ".join(leaked))
                        )

                if not forbidden_paths:
                    continue
                if prefix != b"\x7fELF":
                    continue
                dynamic = subprocess.run(
                    [readelf, "-d", path],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    env=env,
                )
                for line in dynamic.stdout.splitlines():
                    if "(RPATH)" not in line and "(RUNPATH)" not in line:
                        continue
                    leaked = [value for value in forbidden_paths if value in line]
                    if leaked:
                        raise RuntimeError(
                            "package ELF contains build RPATH in %s: %s"
                            % (path, line.strip())
                        )


def package_version(package):
    """Return the immutable PUP release version for a package."""
    release_method = getattr(type(package), "release_version", None)
    if release_method is None:
        return package.version()
    return release_method(package)


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
            log.debug("%s is disabled: %s", entry, disabled_reason)
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
