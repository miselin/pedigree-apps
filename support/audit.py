import hashlib
import logging
import os
import re
import shlex
import stat
import subprocess
import tarfile
from dataclasses import dataclass
from pathlib import PurePosixPath

from . import buildsystem


log = logging.getLogger(__name__)


FHS_TOP_LEVEL = {
    "bin",
    "boot",
    "dev",
    "etc",
    "home",
    "lib",
    "lib64",
    "media",
    "mnt",
    "opt",
    "proc",
    "root",
    "run",
    "sbin",
    "srv",
    "sys",
    "tmp",
    "usr",
    "var",
}

_BUILD_PATH_KEYS = (
    "APPS_BASE",
    "PEDIGREE_BASE",
    "CROSS_BASE",
    "TARGET_SYSROOT",
    "OUTPUT_BASE",
    "DOWNLOAD_TEMP",
    "BUILD_BASE",
    "PORTS_SYSROOT",
)
_BUILD_PATH_MARKERS = (
    "/.build/",
    "/downloads/",
    "/newpacks/",
    "/root.incomplete/",
)
_HOST_PATH_PREFIXES = (
    "/Applications/",
    "/Library/",
    "/System/",
    "/Users/",
    "/home/",
    "/nix/",
    "/opt/homebrew/",
    "/private/",
    "/tmp/",
    "/usr/local/",
    "/workspace/",
)
_TARGET_PATH_PREFIXES = (
    "/bin/",
    "/etc/",
    "/lib/",
    "/lib64/",
    "/run/",
    "/sbin/",
    "/usr/",
    "/var/",
)
_ABSOLUTE_PATH = re.compile(r"(?<![A-Za-z0-9_])(?:-L|-R)?(/[^\s'\";]+)")
_DEPENDENCY_LIBS = re.compile(
    r"^[ \t]*dependency_libs=(?:'([^']*)'|\"([^\"]*)\"|(.*))$",
    re.MULTILINE,
)
_DYNAMIC_TAG = re.compile(
    r"\((NEEDED|SONAME|RPATH|RUNPATH)\)[^\[]*\[(.*)\]\s*$"
)
_HOST_BINARY_MAGICS = (
    b"MZ",
    b"\xca\xfe\xba\xbe",
    b"\xcf\xfa\xed\xfe",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xfe\xed\xfa\xce",
)
_PEDIGREE_INTERPRETER = "/usr/lib/ld-musl-x86_64.so.1"
_SAFE_DYNAMIC_NAME = re.compile(r"[A-Za-z0-9_+.-]+")


class AuditError(RuntimeError):
    pass


@dataclass(frozen=True)
class PayloadEntry:
    kind: str
    mode: int
    digest: str = ""
    link_target: str = ""


def _digest(source):
    result = hashlib.sha256()
    while True:
        chunk = source.read(1024 * 1024)
        if not chunk:
            break
        result.update(chunk)
    return result.hexdigest()


def _filesystem_payload(root):
    payload = {}

    def visit(directory, relative_parts=()):
        with os.scandir(directory) as entries:
            for entry in sorted(entries, key=lambda item: item.name):
                parts = relative_parts + (entry.name,)
                relative = "/".join(parts)
                details = entry.stat(follow_symlinks=False)
                mode = stat.S_IMODE(details.st_mode)
                if stat.S_ISDIR(details.st_mode):
                    payload[relative] = PayloadEntry("directory", mode)
                    visit(entry.path, parts)
                elif stat.S_ISREG(details.st_mode):
                    with open(entry.path, "rb") as source:
                        digest = _digest(source)
                    payload[relative] = PayloadEntry("file", mode, digest=digest)
                elif stat.S_ISLNK(details.st_mode):
                    payload[relative] = PayloadEntry(
                        "symlink", mode, link_target=os.readlink(entry.path)
                    )
                else:
                    raise AuditError(
                        "root contains unsupported file type: %s" % relative
                    )

    visit(root)
    return payload


def _safe_archive_name(member):
    name = member.name
    if member.isdir() and name.endswith("/"):
        name = name[:-1]
    path = PurePosixPath(name)
    if (
        not name
        or path.is_absolute()
        or ".." in path.parts
        or str(path) != name
    ):
        raise AuditError("PUP contains unsafe member name: %r" % member.name)
    return str(path)


def _archive_payload(archive_path):
    payload = {}
    try:
        archive = tarfile.open(archive_path, "r:*")
    except (OSError, tarfile.TarError) as error:
        raise AuditError("cannot open PUP archive: %s" % error) from error

    with archive:
        for member in archive.getmembers():
            relative = _safe_archive_name(member)
            if relative in payload:
                raise AuditError("PUP contains duplicate member: %s" % relative)
            if (
                member.uid != 0
                or member.gid != 0
                or member.uname != "root"
                or member.gname != "root"
            ):
                raise AuditError(
                    "PUP member is not owned by root: %s" % relative
                )

            mode = member.mode & 0o7777
            if member.isdir():
                payload[relative] = PayloadEntry("directory", mode)
            elif member.isfile() or member.islnk():
                if member.islnk():
                    link_path = PurePosixPath(member.linkname)
                    if (
                        not member.linkname
                        or link_path.is_absolute()
                        or ".." in link_path.parts
                        or str(link_path) != member.linkname
                    ):
                        raise AuditError(
                            "PUP contains unsafe hard-link target: %r"
                            % member.linkname
                        )
                try:
                    source = archive.extractfile(member)
                except (KeyError, OSError, tarfile.TarError) as error:
                    raise AuditError(
                        "PUP hard-link target is missing or unreadable: %s"
                        % relative
                    ) from error
                if source is None:
                    raise AuditError(
                        "PUP member has no readable payload: %s" % relative
                    )
                with source:
                    digest = _digest(source)
                payload[relative] = PayloadEntry("file", mode, digest=digest)
            elif member.issym():
                payload[relative] = PayloadEntry(
                    "symlink", mode, link_target=member.linkname
                )
            else:
                raise AuditError(
                    "PUP contains unsupported member type: %s" % relative
                )
    return payload


def _check_fhs(payload):
    for relative, entry in payload.items():
        parts = PurePosixPath(relative).parts
        top_level = parts[0]
        if top_level not in FHS_TOP_LEVEL:
            raise AuditError("non-FHS top-level path: %s" % top_level)
        if len(parts) > 1 and parts[0] == "usr" and parts[1] in (
            "doc",
            "info",
            "man",
        ):
            raise AuditError("non-FHS /usr path: %s/%s" % (parts[0], parts[1]))
        if len(parts) == 1 and entry.kind not in ("directory", "symlink"):
            raise AuditError("FHS top-level path is not a directory: %s" % top_level)


def _check_symlinks(payload, forbidden_paths):
    for relative, entry in payload.items():
        if entry.kind != "symlink":
            continue
        target = entry.link_target
        if (
            not target
            or "\0" in target
            or _contains_build_path(target, forbidden_paths)
            or _contains_host_path(target)
        ):
            raise AuditError("unsafe symlink target in %s: %r" % (relative, target))

        target_path = PurePosixPath(target)
        if target_path.is_absolute():
            if ".." in target_path.parts or len(target_path.parts) < 2:
                raise AuditError(
                    "unsafe absolute symlink target in %s: %r"
                    % (relative, target)
                )
            if target_path.parts[1] not in FHS_TOP_LEVEL:
                raise AuditError(
                    "non-FHS absolute symlink target in %s: %r"
                    % (relative, target)
                )
            continue

        resolved = list(PurePosixPath(relative).parent.parts)
        for part in target_path.parts:
            if part == "..":
                if not resolved:
                    raise AuditError(
                        "symlink escapes package root in %s: %r"
                        % (relative, target)
                    )
                resolved.pop()
            elif part != ".":
                resolved.append(part)
        if not resolved:
            raise AuditError(
                "symlink resolves to package root in %s: %r"
                % (relative, target)
            )
        if resolved[0] not in FHS_TOP_LEVEL:
            raise AuditError(
                "symlink resolves to non-FHS path in %s: %r"
                % (relative, target)
            )


def _compare_payloads(root_payload, archive_payload):
    root_paths = set(root_payload)
    archive_paths = set(archive_payload)
    missing = sorted(root_paths - archive_paths)
    extra = sorted(archive_paths - root_paths)
    if missing:
        raise AuditError("PUP is missing root path: %s" % missing[0])
    if extra:
        raise AuditError("PUP has path absent from root: %s" % extra[0])

    for relative in sorted(root_paths):
        expected = root_payload[relative]
        actual = archive_payload[relative]
        if expected.kind != actual.kind:
            raise AuditError(
                "PUP type differs from root for %s: %s != %s"
                % (relative, actual.kind, expected.kind)
            )
        if expected.mode != actual.mode:
            raise AuditError(
                "PUP mode differs from root for %s: %04o != %04o"
                % (relative, actual.mode, expected.mode)
            )
        if expected.kind == "file" and expected.digest != actual.digest:
            raise AuditError("PUP content differs from root for %s" % relative)
        if (
            expected.kind == "symlink"
            and expected.link_target != actual.link_target
        ):
            raise AuditError(
                "PUP symlink differs from root for %s: %r != %r"
                % (relative, actual.link_target, expected.link_target)
            )


def _forbidden_build_paths(env):
    paths = []
    for key in _BUILD_PATH_KEYS:
        value = env.get(key)
        if not value or not os.path.isabs(value) or value == "/":
            continue
        paths.append(value.rstrip("/"))
    return tuple(sorted(set(paths), key=len, reverse=True))


def _contains_build_path(value, forbidden_paths):
    return any(path in value for path in forbidden_paths) or any(
        marker in value for marker in _BUILD_PATH_MARKERS
    )


def _contains_host_path(value):
    return any(prefix in value for prefix in _HOST_PATH_PREFIXES)


def _readelf(env, path, *arguments):
    readelf = env.get("CROSS_READELF")
    if not readelf:
        readelf = os.path.join(
            env.get("CROSS_BASE", ""),
            "bin",
            env.get("CROSS_TARGET", "") + "-readelf",
        )
    try:
        result = subprocess.run(
            [readelf, *arguments, path],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
    except OSError as error:
        raise AuditError("cannot run target readelf: %s" % error) from error
    if result.returncode:
        diagnostic = result.stderr.strip() or result.stdout.strip()
        raise AuditError(
            "target readelf rejected %s: %s" % (path, diagnostic)
        )
    return result.stdout


def _check_elf_headers(env, path, relative, allow_empty=False):
    output = _readelf(env, path, "-hW")
    classes = re.findall(r"^\s*Class:\s*(.+?)\s*$", output, re.MULTILINE)
    data = re.findall(r"^\s*Data:\s*(.+?)\s*$", output, re.MULTILINE)
    machines = re.findall(r"^\s*Machine:\s*(.+?)\s*$", output, re.MULTILINE)
    types = re.findall(r"^\s*Type:\s*(\S+)", output, re.MULTILINE)
    if not classes and allow_empty:
        return []
    if not classes or not (len(classes) == len(data) == len(machines) == len(types)):
        raise AuditError("target readelf returned incomplete headers for %s" % relative)

    architecture = env.get("ARCH_TARGET")
    if architecture != "x86_64":
        raise AuditError("unsupported audit architecture: %s" % architecture)
    for elf_class, byte_order, machine in zip(classes, data, machines):
        if elf_class != "ELF64":
            raise AuditError("non-target ELF class in %s: %s" % (relative, elf_class))
        if "little endian" not in byte_order:
            raise AuditError(
                "non-target ELF byte order in %s: %s" % (relative, byte_order)
            )
        if machine != "Advanced Micro Devices X86-64":
            raise AuditError(
                "non-target ELF machine in %s: %s" % (relative, machine)
            )
    return types


def _safe_dynamic_name(tag, value, relative):
    if (
        not value
        or value != os.path.basename(value)
        or value in (".", "..")
        or ".." in value
        or "$" in value
        or any(character.isspace() for character in value)
        or not _SAFE_DYNAMIC_NAME.fullmatch(value)
    ):
        raise AuditError("unsafe %s in %s: %r" % (tag, relative, value))


def _root_shared_library(relative, elf_types):
    parts = PurePosixPath(relative).parts
    in_library_root = (
        len(parts) == 2 and parts[0] in ("lib", "lib64")
    ) or (
        len(parts) == 3
        and parts[0] == "usr"
        and parts[1] in ("lib", "lib64")
    )
    filename = parts[-1]
    return (
        in_library_root
        and filename.startswith("lib")
        and ".so" in filename
        and "DYN" in elf_types
    )


def _in_runtime_tree(parts):
    return bool(parts) and (
        parts[0] in ("lib", "lib64")
        or (len(parts) > 1 and parts[:2] in (("usr", "lib"), ("usr", "lib64")))
    )


def _check_runtime_component(tag, component, relative):
    origin = None
    for candidate in ("$ORIGIN", "${ORIGIN}"):
        if component == candidate or component.startswith(candidate + "/"):
            origin = candidate
            break
    if origin:
        resolved = list(PurePosixPath(relative).parent.parts)
        suffix = component[len(origin) :]
        for part in (suffix.split("/")[1:] if suffix else ()):
            if not part or part == ".":
                raise AuditError(
                    "%s contains non-canonical ORIGIN entry in %s: %s"
                    % (tag, relative, component)
                )
            if part == "..":
                if not resolved:
                    raise AuditError(
                        "%s ORIGIN entry escapes package root in %s: %s"
                        % (tag, relative, component)
                    )
                resolved.pop()
            else:
                resolved.append(part)
        if not _in_runtime_tree(tuple(resolved)):
            raise AuditError(
                "%s ORIGIN entry resolves outside runtime library trees in %s: %s"
                % (tag, relative, component)
            )
        return

    if not component.startswith("/"):
        raise AuditError(
            "%s contains unsafe relative entry in %s: %s"
            % (tag, relative, component)
        )
    raw_parts = component.split("/")[1:]
    if any(not part or part in (".", "..") for part in raw_parts):
        raise AuditError(
            "%s contains non-canonical absolute entry in %s: %s"
            % (tag, relative, component)
        )
    if not _in_runtime_tree(tuple(raw_parts)):
        raise AuditError(
            "%s contains unsafe host path in %s: %s"
            % (tag, relative, component)
        )


def _check_dynamic(env, path, relative, elf_types, forbidden_paths):
    output = _readelf(env, path, "-dW")
    tags = {name: [] for name in ("NEEDED", "SONAME", "RPATH", "RUNPATH")}
    for line in output.splitlines():
        match = _DYNAMIC_TAG.search(line)
        if match:
            tags[match.group(1)].append(match.group(2))
        elif any("(%s)" % name in line for name in tags):
            raise AuditError(
                "malformed dynamic tag in %s: %s"
                % (relative, line.strip())
            )

    if _root_shared_library(relative, elf_types) and not tags["SONAME"]:
        raise AuditError("shared library has no SONAME: %s" % relative)
    if len(tags["SONAME"]) > 1:
        raise AuditError("shared library has multiple SONAMEs: %s" % relative)
    for value in tags["SONAME"]:
        _safe_dynamic_name("SONAME", value, relative)
    for value in tags["NEEDED"]:
        _safe_dynamic_name("NEEDED", value, relative)
    for tag in ("RPATH", "RUNPATH"):
        for value in tags[tag]:
            if _contains_build_path(value, forbidden_paths):
                raise AuditError(
                    "%s contains build path in %s: %s" % (tag, relative, value)
                )
            if _contains_host_path(value):
                raise AuditError(
                    "%s contains unsafe host path in %s: %s"
                    % (tag, relative, value)
                )
            for component in value.split(":"):
                if not component:
                    raise AuditError(
                        "%s contains current-directory entry in %s"
                        % (tag, relative)
                    )
                _check_runtime_component(tag, component, relative)
    return tags


def _check_program_headers(env, path, relative, elf_types, tags, mode):
    if not any(elf_type in ("DYN", "EXEC") for elf_type in elf_types):
        return

    output = _readelf(env, path, "-lW")
    for line in output.splitlines():
        fields = line.split()
        if not fields or fields[0] != "GNU_STACK":
            continue
        numeric_fields = fields[1:6]
        flags = "".join(fields[6:-1])
        if (
            len(fields) < 7
            or not all(
                re.fullmatch(r"0x[0-9A-Fa-f]+", value)
                for value in numeric_fields
            )
            # readelf prints zero segment alignment in decimal for LLD output.
            or not re.fullmatch(r"(?:0x[0-9A-Fa-f]+|[0-9]+)", fields[-1])
            or not set(flags).issubset(set("RWE"))
        ):
            raise AuditError(
                "malformed GNU_STACK program header in %s: %s"
                % (relative, line.strip())
            )
        # A missing marker remains valid for legacy target objects, but an
        # explicit executable stack request is unambiguous and unsafe.
        if "E" in flags:
            raise AuditError("executable GNU_STACK in %s" % relative)

    interpreters = re.findall(
        r"^\s*\[Requesting program interpreter:\s*(.*)\]\s*$",
        output,
        re.MULTILINE,
    )
    if len(interpreters) > 1:
        raise AuditError("multiple PT_INTERP entries in %s" % relative)
    if interpreters and interpreters[0] != _PEDIGREE_INTERPRETER:
        raise AuditError(
            "unsafe PT_INTERP in %s: %s" % (relative, interpreters[0])
        )

    filename = PurePosixPath(relative).name
    library_like = bool(tags["SONAME"]) or ".so" in filename
    executable = "EXEC" in elf_types or (bool(mode & 0o111) and not library_like)
    if executable and tags["NEEDED"] and not interpreters:
        raise AuditError("dynamic target executable has no PT_INTERP: %s" % relative)


def _check_libtool_archive(path, relative, forbidden_paths):
    try:
        with open(path, encoding="utf-8") as source:
            content = source.read()
    except (OSError, UnicodeDecodeError) as error:
        raise AuditError(
            "cannot read libtool archive %s: %s" % (relative, error)
        ) from error

    if _contains_build_path(content, forbidden_paths):
        raise AuditError("libtool archive contains build path: %s" % relative)
    assignments = "\n".join(
        line for line in content.splitlines() if not line.lstrip().startswith("#")
    )
    dependency_matches = list(_DEPENDENCY_LIBS.finditer(assignments))
    if len(dependency_matches) > 1:
        raise AuditError(
            "libtool archive has multiple dependency_libs assignments: %s"
            % relative
        )
    if dependency_matches:
        dependency_match = dependency_matches[0]
        dependency_libs = next(
            value for value in dependency_match.groups() if value is not None
        )
        try:
            dependency_tokens = shlex.split(dependency_libs)
        except ValueError as error:
            raise AuditError(
                "cannot parse dependency_libs in %s: %s" % (relative, error)
            ) from error
        for index, token in enumerate(dependency_tokens):
            bare_library_path = token.startswith(("-L/", "-R/"))
            bare_absolute = token.startswith("/")
            separated_absolute = (
                token in ("-L", "-R")
                and index + 1 < len(dependency_tokens)
                and dependency_tokens[index + 1].startswith("/")
            )
            if bare_library_path or bare_absolute or separated_absolute:
                raise AuditError(
                    "libtool dependency path is not sysroot-relocatable in %s: %s"
                    % (relative, token)
                )
    for match in _ABSOLUTE_PATH.finditer(assignments):
        absolute = match.group(1).rstrip(",)")
        if absolute.startswith(_HOST_PATH_PREFIXES) or not absolute.startswith(
            _TARGET_PATH_PREFIXES
        ):
            raise AuditError(
                "libtool archive contains non-relocatable host path in %s: %s"
                % (relative, absolute)
            )


def _check_artifact_formats(root, payload, env):
    forbidden_paths = _forbidden_build_paths(env)
    for relative, entry in sorted(payload.items()):
        if entry.kind != "file":
            continue
        path = os.path.join(root, *PurePosixPath(relative).parts)
        try:
            with open(path, "rb") as source:
                prefix = source.read(8)
        except OSError as error:
            raise AuditError(
                "cannot read root artifact %s: %s" % (relative, error)
            ) from error

        if relative.endswith(".la"):
            _check_libtool_archive(path, relative, forbidden_paths)
        if prefix == b"!<thin>\n":
            raise AuditError("thin archive is not self-contained: %s" % relative)
        if prefix == b"!<arch>\n":
            # readelf reports members of an ar archive rather than one ELF
            # header. Empty musl interface archives have no members, while
            # populated archives still need target-machine validation.
            _check_elf_headers(env, path, relative, allow_empty=True)
            continue
        if prefix.startswith(b"\x7fELF"):
            elf_types = _check_elf_headers(env, path, relative)
            tags = _check_dynamic(
                env, path, relative, elf_types, forbidden_paths
            )
            _check_program_headers(
                env, path, relative, elf_types, tags, entry.mode
            )
            continue
        host_binary_candidate = bool(entry.mode & 0o111) or relative.endswith(
            (".dll", ".dylib", ".exe")
        )
        if host_binary_candidate and any(
            prefix.startswith(magic) for magic in _HOST_BINARY_MAGICS
        ):
            raise AuditError("host binary format in target root: %s" % relative)
        if relative.endswith(".a"):
            raise AuditError("invalid target archive format: %s" % relative)


def _artifact_paths(name, package, env):
    version = buildsystem.package_version(package)
    deploy_base = os.path.join(env["OUTPUT_BASE"], name, version)
    return (
        os.path.join(deploy_base, "root"),
        os.path.join(deploy_base, ".complete"),
        os.path.join(
            env["PACKMAN_REPO"],
            "%s-%s-%s.pup" % (name, version, env["PACKMAN_TARGET_ARCH"]),
        ),
    )


def audit_package(name, package, env):
    root, marker, archive = _artifact_paths(name, package, env)
    if not os.path.isdir(root) or os.path.islink(root):
        raise AuditError("exact build root is missing: %s" % root)
    if not os.path.isfile(marker) or os.path.islink(marker):
        raise AuditError("exact completion marker is missing: %s" % marker)
    if not os.path.isfile(archive) or os.path.islink(archive):
        raise AuditError("exact PUP archive is missing: %s" % archive)

    try:
        with open(marker, encoding="utf-8") as source:
            marker_content = source.read()
    except OSError as error:
        raise AuditError("cannot read completion marker: %s" % error) from error
    expected_marker = "%s-%s\n" % (
        name, buildsystem.package_version(package)
    )
    if marker_content != expected_marker:
        raise AuditError(
            "completion marker content differs: %r != %r"
            % (marker_content, expected_marker)
        )

    root_payload = _filesystem_payload(root)
    if not root_payload:
        raise AuditError("build root is empty: %s" % root)
    _check_fhs(root_payload)
    _check_symlinks(root_payload, _forbidden_build_paths(env))
    archive_payload = _archive_payload(archive)
    _compare_payloads(root_payload, archive_payload)
    try:
        buildsystem.check_script_runtime(package, root)
    except RuntimeError as error:
        raise AuditError(str(error)) from error
    _check_artifact_formats(root, root_payload, env)


def audit_packages(packages, env):
    failed = []
    for name, package in packages:
        try:
            audit_package(name, package, env)
        except (AuditError, OSError) as error:
            log.error('audit failed for "%s": %s', name, error)
            failed.append(name)
        else:
            log.info('audit passed for "%s"', name)
    if failed:
        log.error("failed package audits: %s", ", ".join(sorted(failed)))
        return 1
    return 0
