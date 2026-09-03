import hashlib
import logging
import os
import shlex
import shutil
import subprocess
import tempfile
import urllib.request


log = logging.getLogger(__name__)


AUTOCONF_PATHFLAGS = {
    "prefix": "/usr",
    "exec-prefix": "/usr",
    "bindir": "/usr/bin",
    "sbindir": "/usr/sbin",
    "libexecdir": "/usr/lib/$package",
    "sysconfdir": "/etc",
    "localstatedir": "/var",
    "libdir": "/usr/lib",
    "includedir": "/usr/include",
    "oldincludedir": "/usr/include",
    "datarootdir": "/usr/share",
    "datadir": "/usr/share",
    "mandir": "/usr/share/man",
    "infodir": "/usr/share/info",
    "docdir": "/usr/share/doc/$package",
}


def _redacted_command(command):
    if isinstance(command, str):
        return command
    result = []
    redact_next = False
    for argument in command:
        if redact_next:
            result.append("<redacted>")
            redact_next = False
        elif argument == "--key":
            result.append(argument)
            redact_next = True
        elif isinstance(argument, str) and argument.startswith("--key="):
            result.append("--key=<redacted>")
        else:
            result.append(argument)
    return result


def _file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)


def get_builddir(srcdir, env, inplace):
    if inplace:
        return srcdir
    path = os.path.join(srcdir, "pedigree-build")
    os.makedirs(path, exist_ok=True)
    return path


def cmd(*args, **kwargs):
    log.debug(
        "cmd: %r (cwd=%r)",
        _redacted_command(args[0]),
        kwargs.get("cwd"),
    )
    command_env = kwargs.get("env", {})
    log_path = command_env.get("BUILD_LOG")
    if log_path and "stdout" not in kwargs and "stderr" not in kwargs:
        with open(log_path, "ab") as build_log:
            kwargs["stdout"] = build_log
            kwargs["stderr"] = subprocess.STDOUT
            return subprocess.check_call(*args, **kwargs)
    return subprocess.check_call(*args, **kwargs)


def cmd_output(*args, **kwargs):
    log.debug(
        "cmd: %r (cwd=%r)",
        _redacted_command(args[0]),
        kwargs.get("cwd"),
    )
    return subprocess.check_output(*args, **kwargs)


def libtoolize(srcdir, env, ltdl_dir=None):
    args = [env["LIBTOOLIZE"], "--install", "--verbose", "--force"]
    args.append("--ltdl=%s" % ltdl_dir if ltdl_dir else "--ltdl")
    cmd(args, cwd=srcdir, env=env)


def autoreconf(srcdir, env, extra_flags=()):
    command_env = env.copy()
    command_env["LIBTOOLIZE"] = env["LIBTOOLIZE"]
    flags = list(extra_flags)
    for relative in ("m4", os.path.join("libltdl", "m4")):
        path = os.path.join(srcdir, relative)
        if os.path.isdir(path):
            flags.append("-I" + path)
    cmd(
        [env["AUTORECONF"], "-ifs", "-W", "none"] + flags,
        cwd=srcdir,
        env=command_env,
    )


def autoconf(srcdir, env, aclocal_flags=(), only_aclocal=False):
    cmd([env["ACLOCAL"]] + list(aclocal_flags), cwd=srcdir, env=env)
    if not only_aclocal:
        cmd([env["AUTOCONF"]], cwd=srcdir, env=env)


def patch_libtool_configure(srcdir):
    """Teach generated Libtool configure fragments about Pedigree ELF."""
    for current, _, filenames in os.walk(srcdir):
        if "configure" not in filenames:
            continue

        path = os.path.join(current, "configure")
        try:
            with open(path, encoding="utf-8") as source:
                contents = source.read()
        except UnicodeDecodeError:
            continue

        # These markers keep the rewrite confined to generated Libtool logic.
        if not (
            "lt_cv_deplibs_check_method" in contents
            and "lt_prog_compiler" in contents
        ):
            continue

        changed = False
        result = []
        for line in contents.splitlines(keepends=True):
            case_pattern = line.split(")", 1)[0]
            is_libtool_elf_case = (
                ")" in line
                and "linux*" in case_pattern
                and any(
                    marker in case_pattern
                    for marker in ("k*bsd", "kopensolaris")
                )
            )
            if is_libtool_elf_case and "pedigree*" not in case_pattern:
                if "linux* |" in line:
                    line = line.replace(
                        "linux* |", "linux* | pedigree* |", 1
                    )
                    changed = True
                elif "linux*|" in line:
                    line = line.replace("linux*|", "linux*|pedigree*|", 1)
                    changed = True
            result.append(line)

        if changed:
            with open(path, "w", encoding="utf-8") as destination:
                destination.writelines(result)
            log.debug("enabled Pedigree ELF in generated Libtool: %s", path)


def run_configure(
    package,
    srcdir,
    env,
    inplace=True,
    host=True,
    extra_config=(),
    paths=None,
    not_paths=None,
):
    patch_libtool_configure(srcdir)
    builddir = get_builddir(srcdir, env, inplace)
    command_env = env.copy()
    command_env["CONFIG_SITE"] = env["TARGET_CONFIG_SITE"]
    configure = os.path.join(srcdir, "configure")
    options = [configure]
    if host:
        options.append("--host=%s" % env["CROSS_TARGET"])

    # Libtool otherwise treats absolute /usr/lib references in dependency .la
    # files as host paths instead of resolving them in the staged port sysroot.
    if os.path.isfile(configure):
        with open(configure, encoding="utf-8", errors="ignore") as script:
            if "--with-sysroot" in script.read():
                options.append("--with-sysroot=%s" % env["PORTS_SYSROOT"])

    enabled_paths = set(AUTOCONF_PATHFLAGS) if paths is None else set(paths)
    disabled_paths = set(not_paths or ())
    for option, value in AUTOCONF_PATHFLAGS.items():
        if option not in enabled_paths or option in disabled_paths:
            continue
        options.append(
            "--%s=%s" % (option, value.replace("$package", package.name()))
        )
    options.extend(extra_config)
    cmd(options, cwd=builddir, env=command_env)


def cmake_configure(package, srcdir, env, extra_config=()):
    builddir = get_builddir(srcdir, env, False)
    command_env = env.copy()
    for variable in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS"):
        command_env.pop(variable, None)
    toolchain_file = os.path.join(
        env["APPS_BASE"], "cmake", "PedigreeToolchain.cmake"
    )
    options = [
        env["CMAKE"],
        "-S",
        srcdir,
        "-B",
        builddir,
        "-G",
        "Ninja",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_TOOLCHAIN_FILE=%s" % toolchain_file,
        "-DCMAKE_MODULE_PATH=%s"
        % os.path.join(env["APPS_BASE"], "cmake", "Modules"),
        "-DCMAKE_INSTALL_PREFIX=/usr",
        "-DCMAKE_INSTALL_LIBDIR=lib",
        "-DPEDIGREE_TOOLCHAIN_ROOT=%s" % env["CROSS_BASE"],
        "-DPEDIGREE_PORTS_SYSROOT=%s" % env["PORTS_SYSROOT"],
    ]
    options.extend(extra_config)
    cmd(options, cwd=srcdir, env=command_env)


def cmake_build(srcdir, env, target=None):
    args = [env["CMAKE"], "--build", get_builddir(srcdir, env, False)]
    if target:
        args.extend(("--target", target))
    args.extend(("--parallel", env["MAKEFLAGS"].removeprefix("-j")))
    cmd(args, cwd=srcdir, env=env)


def cmake_install(srcdir, env, deploydir):
    command_env = env.copy()
    command_env["DESTDIR"] = deploydir
    cmd(
        [env["CMAKE"], "--install", get_builddir(srcdir, env, False)],
        cwd=srcdir,
        env=command_env,
    )


def _meson_values(arguments):
    return "[{}]".format(
        ", ".join("'{}'".format(value.replace("'", "\\'")) for value in arguments)
    )


def meson_configure(package, srcdir, env, extra_config=()):
    builddir = get_builddir(srcdir, env, False)
    cross_file = os.path.join(builddir, "pedigree-cross.ini")
    c_args = shlex.split(env.get("CFLAGS", "")) + shlex.split(
        env.get("CPPFLAGS", "")
    )
    cpp_args = shlex.split(env.get("CXXFLAGS", "")) + shlex.split(
        env.get("CPPFLAGS", "")
    )
    link_args = shlex.split(env.get("LDFLAGS", ""))
    # The cross GCC already knows its non-FHS compiler sysroot. Meson's
    # sys_root property would invent a nonexistent <root>/usr/include path.
    with open(cross_file, "w", encoding="utf-8") as config:
        config.write(
            """[binaries]
c = %(c)s
cpp = %(cpp)s
ar = %(ar)s
strip = %(strip)s
pkg-config = %(pkg_config)s

[host_machine]
system = 'pedigree'
cpu_family = 'x86_64'
cpu = 'x86_64'
endian = 'little'

[properties]
needs_exe_wrapper = true

[built-in options]
c_args = %(c_args)s
cpp_args = %(cpp_args)s
c_link_args = %(link_args)s
cpp_link_args = %(link_args)s
"""
            % {
                "c": _meson_values((env["CCACHE"], env["CROSS_CC"])),
                "cpp": _meson_values((env["CCACHE"], env["CROSS_CXX"])),
                "ar": repr(env["CROSS_AR"]),
                "strip": repr(env["CROSS_STRIP"]),
                "pkg_config": repr(env["PKG_CONFIG"]),
                "c_args": _meson_values(c_args),
                "cpp_args": _meson_values(cpp_args),
                "link_args": _meson_values(link_args),
            }
        )

    options = [
        env["MESON"],
        "setup",
        builddir,
        srcdir,
        "--cross-file",
        cross_file,
        "--prefix=/usr",
        "--libdir=lib",
        "--buildtype=release",
        "--wrap-mode=nodownload",
    ]
    options.extend(extra_config)
    cmd(options, cwd=srcdir, env=env)


def meson_build(srcdir, env, target=None):
    args = [
        env["MESON"],
        "compile",
        "-C",
        get_builddir(srcdir, env, False),
        "-j",
        env["MAKEFLAGS"].removeprefix("-j"),
    ]
    if target:
        args.append(target)
    cmd(args, cwd=srcdir, env=env)


def meson_install(srcdir, env, deploydir):
    command_env = env.copy()
    command_env["DESTDIR"] = deploydir
    cmd(
        [env["MESON"], "install", "-C", get_builddir(srcdir, env, False)],
        cwd=srcdir,
        env=command_env,
    )


def make(srcdir, env, target=None, inplace=True, parallel=True, extra_opts=()):
    builddir = get_builddir(srcdir, env, inplace)
    args = [env["MAKE"]]
    command_env = env
    if parallel:
        args.append(env["MAKEFLAGS"])
    else:
        command_env = env.copy()
        command_env["MAKEFLAGS"] = "-j1"
    if target is not None:
        args.append(target)
    args.extend(extra_opts)
    cmd(args, cwd=builddir, env=command_env)


def download(url, target, sha256=None):
    log.info("download %s", url)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    if os.path.isfile(target):
        if not sha256 or _file_sha256(target) == sha256:
            log.debug("using cached download %s", target)
            return
        log.warning("cached download failed SHA-256 verification: %s", target)

    temporary = target + ".part"
    digest = hashlib.sha256()
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "pedigree-apps-builder/1.0"}
        )
        with urllib.request.urlopen(request, timeout=120) as source:
            with open(temporary, "wb") as destination:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    destination.write(chunk)
                    digest.update(chunk)
        if sha256 and digest.hexdigest() != sha256:
            raise RuntimeError(
                "SHA-256 mismatch for %s: expected %s, got %s"
                % (url, sha256, digest.hexdigest())
            )
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def symlinks(deploydir, cross_dir, bins=(), libs=(), headers=()):
    paths = []
    for filename in bins:
        paths.append(("usr/bin", filename))
    for filename in libs:
        paths.append(("usr/lib", filename))
    for filename in headers:
        paths.append(("usr/include", filename))

    for relative, filename in paths:
        source = os.path.join(deploydir, relative, filename)
        target = os.path.join(cross_dir, relative, filename)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if os.path.lexists(target):
            os.unlink(target)
        os.symlink(source, target)


def prepare_package_manager(env):
    os.makedirs(env["BUILD_BASE"], exist_ok=True)
    os.makedirs(env["PACKMAN_REPO"], exist_ok=True)
    with open(env["PACKMAN_CONFIG"], "w", encoding="utf-8") as config:
        config.write(
            """[paths]
installroot=/
localdb=%(PACKMAN_REPO)s

[settings]
arch=%(PACKMAN_TARGET_ARCH)s

[remotes]
server=https://pup.pedigree-project.org
upload=https://pup.pedigree-project.org
"""
            % env
        )


def pup_package(package, deploydir, env, upload=False, upload_key=None):
    config_dir = os.path.dirname(env["PACKMAN_CONFIG"])
    os.makedirs(config_dir, exist_ok=True)
    descriptor, config_path = tempfile.mkstemp(
        prefix="pup-", suffix=".conf", dir=config_dir
    )
    os.close(descriptor)
    command_env = env.copy()
    command_env.pop("UPLOAD_KEY", None)
    command_env["PACKMAN_CONFIG"] = config_path
    prepare_package_manager(command_env)
    command = [env["PACKMAN_SCRIPT"], "--config=" + config_path]
    try:
        if upload:
            dependencies = package.install_deps()
            if not upload_key:
                raise RuntimeError("--upload requires UPLOAD_KEY")
            command_env["PUP_UPLOAD_KEY"] = upload_key
            command.extend(
                (
                    "register",
                    "--package",
                    package.name(),
                    "--version",
                    package.version(),
                    "--architecture",
                    env["PACKMAN_TARGET_ARCH"],
                )
            )
            command.extend(dependencies)
        else:
            command.extend(
                (
                    "create",
                    "--path",
                    deploydir,
                    "--package",
                    package.name(),
                    "--version",
                    package.version(),
                    "--architecture",
                    env["PACKMAN_TARGET_ARCH"],
                )
            )
        cmd(command, cwd=deploydir, env=command_env)
    finally:
        if os.path.exists(config_path):
            os.unlink(config_path)


def create_package(package, deploydir, env):
    pup_package(package, deploydir, env)


def upload_package(package, deploydir, env, upload_key):
    pup_package(
        package,
        deploydir,
        env,
        upload=True,
        upload_key=upload_key,
    )
