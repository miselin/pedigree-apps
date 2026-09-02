import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from io import BytesIO
from unittest import mock

from . import audit
from . import buildsystem


class AuditTest(unittest.TestCase):
    class FakePackage(buildsystem.Package):
        def name(self):
            return "example"

        def version(self):
            return "1.0"

    valid_header = """\
ELF Header:
  Class:                             ELF64
  Data:                              2's complement, little endian
  Type:                              DYN (Shared object file)
  Machine:                           Advanced Micro Devices X86-64
"""

    def environment(self, temporary):
        return {
            "APPS_BASE": "/workspace",
            "ARCH_TARGET": "x86_64",
            "BUILD_BASE": "/workspace/.build/x86_64",
            "CROSS_BASE": "/opt/pedigree",
            "CROSS_READELF": "/opt/pedigree/bin/x86_64-pedigree-readelf",
            "CROSS_TARGET": "x86_64-pedigree",
            "OUTPUT_BASE": os.path.join(temporary, "output"),
            "PACKMAN_REPO": os.path.join(temporary, "repo"),
            "PACKMAN_TARGET_ARCH": "amd64",
        }

    def artifact_paths(self, temporary):
        env = self.environment(temporary)
        base = os.path.join(env["OUTPUT_BASE"], "example", "1.0")
        return (
            env,
            os.path.join(base, "root"),
            os.path.join(base, ".complete"),
            os.path.join(env["PACKMAN_REPO"], "example-1.0-amd64.pup"),
        )

    @staticmethod
    def root_owned(member):
        member.uid = 0
        member.gid = 0
        member.uname = "root"
        member.gname = "root"
        return member

    def create_root(self, root):
        bindir = os.path.join(root, "usr", "bin")
        os.makedirs(bindir)
        executable = os.path.join(bindir, "example")
        with open(executable, "wb") as output:
            output.write(b"example\n")
        os.chmod(executable, 0o755)
        os.symlink("example", os.path.join(bindir, "example-link"))

    def create_archive(self, root, archive, owner_filter=None):
        os.makedirs(os.path.dirname(archive), exist_ok=True)
        with tarfile.open(archive, "w:gz") as package:
            for entry in sorted(os.listdir(root)):
                package.add(
                    os.path.join(root, entry),
                    arcname=entry,
                    filter=owner_filter or self.root_owned,
                )

    @staticmethod
    def change_content(root):
        with open(os.path.join(root, "usr", "bin", "example"), "ab") as output:
            output.write(b"changed\n")

    @staticmethod
    def change_mode(root):
        os.chmod(os.path.join(root, "usr", "bin", "example"), 0o700)

    @staticmethod
    def change_symlink(root):
        link = os.path.join(root, "usr", "bin", "example-link")
        os.unlink(link)
        os.symlink("other", link)

    def complete_artifacts(self, temporary):
        env, root, marker, archive = self.artifact_paths(temporary)
        self.create_root(root)
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "w", encoding="utf-8") as output:
            output.write("example-1.0\n")
        self.create_archive(root, archive)
        return env, root, marker, archive

    def readelf_result(
        self, command, dynamic="", program_headers="", header=None
    ):
        if "-hW" in command:
            output = header or self.valid_header
        elif "-lW" in command:
            output = program_headers
        else:
            output = dynamic
        return subprocess.CompletedProcess(command, 0, output, "")

    def test_complete_matching_payload_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            env, _, _, _ = self.complete_artifacts(temporary)
            audit.audit_package("example", self.FakePackage(__file__), env)

    def test_rejects_executable_script_without_runtime_provider(self):
        with tempfile.TemporaryDirectory() as temporary:
            env, root, _, archive = self.complete_artifacts(temporary)
            with open(
                os.path.join(root, "usr", "bin", "example"),
                "w",
                encoding="utf-8",
            ) as executable:
                executable.write("#!/usr/bin/env python3\n")
            self.create_archive(root, archive)

            with self.assertRaisesRegex(
                audit.AuditError, "requires runtime provider python3"
            ):
                audit.audit_package(
                    "example", self.FakePackage(__file__), env
                )

    def test_requires_exact_completion_marker_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            env, _, marker, _ = self.complete_artifacts(temporary)
            with open(marker, "w", encoding="utf-8") as output:
                output.write("stale-0.9\n")

            with self.assertRaisesRegex(
                audit.AuditError, "completion marker content differs"
            ):
                audit.audit_package("example", self.FakePackage(__file__), env)

    def test_requires_exact_root_marker_and_pup_paths(self):
        removals = (
            ("root", lambda root, marker, archive: shutil.rmtree(root)),
            ("completion marker", lambda root, marker, archive: os.unlink(marker)),
            ("PUP archive", lambda root, marker, archive: os.unlink(archive)),
        )
        for message, remove in removals:
            with self.subTest(
                artifact=message
            ), tempfile.TemporaryDirectory() as temporary:
                env, root, marker, archive = self.complete_artifacts(temporary)
                remove(root, marker, archive)
                with self.assertRaisesRegex(audit.AuditError, message):
                    audit.audit_package(
                        "example", self.FakePackage(__file__), env
                    )

    def test_rejects_unsafe_archive_member_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            env, _, _, archive = self.complete_artifacts(temporary)
            with tarfile.open(archive, "w:gz") as package:
                contents = b"escape\n"
                member = tarfile.TarInfo("../escape")
                member.size = len(contents)
                package.addfile(self.root_owned(member), BytesIO(contents))

            with self.assertRaisesRegex(audit.AuditError, "unsafe member name"):
                audit.audit_package("example", self.FakePackage(__file__), env)

    def test_rejects_missing_archive_hard_link_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            env, _, _, archive = self.complete_artifacts(temporary)
            with tarfile.open(archive, "w:gz") as package:
                member = tarfile.TarInfo("usr/bin/example")
                member.type = tarfile.LNKTYPE
                member.linkname = "usr/bin/absent"
                package.addfile(self.root_owned(member))

            with self.assertRaisesRegex(
                audit.AuditError, "hard-link target is missing"
            ):
                audit.audit_package("example", self.FakePackage(__file__), env)

    def test_rejects_non_root_archive_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            env, root, _, archive = self.complete_artifacts(temporary)

            def user_owned(member):
                member.uid = 501
                member.gid = 20
                member.uname = "builder"
                member.gname = "staff"
                return member

            self.create_archive(root, archive, owner_filter=user_owned)
            with self.assertRaisesRegex(audit.AuditError, "not owned by root"):
                audit.audit_package("example", self.FakePackage(__file__), env)

    def test_rejects_payload_content_mode_and_symlink_differences(self):
        mutations = (
            ("content", self.change_content, "content differs"),
            ("mode", self.change_mode, "mode differs"),
            ("symlink", self.change_symlink, "symlink differs"),
        )
        for name, mutate, message in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                env, root, _, _ = self.complete_artifacts(temporary)
                mutate(root)
                with self.assertRaisesRegex(audit.AuditError, message):
                    audit.audit_package("example", self.FakePackage(__file__), env)

    def test_rejects_non_fhs_top_level_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            env, root, _, archive = self.complete_artifacts(temporary)
            os.makedirs(os.path.join(root, "applications"))
            self.create_archive(root, archive)

            with self.assertRaisesRegex(audit.AuditError, "non-FHS top-level"):
                audit.audit_package("example", self.FakePackage(__file__), env)

    def test_rejects_legacy_usr_documentation_roots(self):
        for legacy in ("doc", "info", "man"):
            with self.subTest(
                legacy=legacy
            ), tempfile.TemporaryDirectory() as temporary:
                env, root, _, archive = self.complete_artifacts(temporary)
                os.makedirs(os.path.join(root, "usr", legacy))
                self.create_archive(root, archive)

                with self.assertRaisesRegex(audit.AuditError, "non-FHS /usr"):
                    audit.audit_package(
                        "example", self.FakePackage(__file__), env
                    )

    def test_rejects_symlink_escaping_package_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            env, root, _, archive = self.complete_artifacts(temporary)
            link = os.path.join(root, "usr", "bin", "example-link")
            os.unlink(link)
            os.symlink("../../../outside", link)
            self.create_archive(root, archive)

            with self.assertRaisesRegex(audit.AuditError, "escapes package root"):
                audit.audit_package("example", self.FakePackage(__file__), env)

    def test_rejects_relative_symlink_resolving_to_non_fhs_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            env, root, _, archive = self.complete_artifacts(temporary)
            link = os.path.join(root, "usr", "bin", "example-link")
            os.unlink(link)
            os.symlink("../../applications/tool", link)
            self.create_archive(root, archive)

            with self.assertRaisesRegex(
                audit.AuditError, "resolves to non-FHS path"
            ):
                audit.audit_package("example", self.FakePackage(__file__), env)

    def test_rejects_build_and_host_paths_in_libtool_archive(self):
        cases = (
            ("/workspace/.build/sysroot/usr/lib", "contains build path"),
            ("/Users/builder/local/lib", "non-relocatable host path"),
        )
        for libdir_value, message in cases:
            with self.subTest(
                path=libdir_value
            ), tempfile.TemporaryDirectory() as temporary:
                env, root, _, archive = self.complete_artifacts(temporary)
                libdir = os.path.join(root, "usr", "lib")
                os.makedirs(libdir)
                with open(
                    os.path.join(libdir, "libexample.la"),
                    "w",
                    encoding="utf-8",
                ) as metadata:
                    metadata.write("libdir=%r\n" % libdir_value)
                self.create_archive(root, archive)

                with self.assertRaisesRegex(audit.AuditError, message):
                    audit.audit_package(
                        "example", self.FakePackage(__file__), env
                    )

    def test_requires_sysroot_relocatable_libtool_dependencies(self):
        cases = (
            ("dependency_libs='-L/usr/lib'", False, "not sysroot-relocatable"),
            (" dependency_libs='-L/usr/lib'", False, "not sysroot-relocatable"),
            (
                "dependency_libs='/usr/lib/libdependency.la'",
                False,
                "not sysroot-relocatable",
            ),
            (
                "dependency_libs='/usr/lib/libdependency.so'",
                False,
                "not sysroot-relocatable",
            ),
            (
                "dependency_libs='-L /usr/lib'",
                False,
                "not sysroot-relocatable",
            ),
            (
                "dependency_libs='-L=/usr/lib'\n"
                "dependency_libs='-L/usr/lib'",
                False,
                "multiple dependency_libs",
            ),
            (
                "dependency_libs='-L=/usr/lib =/usr/lib/libdependency.la'",
                True,
                "",
            ),
        )
        for dependency_line, accepted, message in cases:
            with self.subTest(
                dependency_line=dependency_line
            ), tempfile.TemporaryDirectory() as temporary:
                env, root, _, archive = self.complete_artifacts(temporary)
                libdir = os.path.join(root, "usr", "lib")
                os.makedirs(libdir)
                with open(
                    os.path.join(libdir, "libexample.la"),
                    "w",
                    encoding="utf-8",
                ) as metadata:
                    metadata.write("libdir='/usr/lib'\n")
                    metadata.write(dependency_line + "\n")
                self.create_archive(root, archive)

                if accepted:
                    audit.audit_package(
                        "example", self.FakePackage(__file__), env
                    )
                else:
                    with self.assertRaisesRegex(
                        audit.AuditError, message
                    ):
                        audit.audit_package(
                            "example", self.FakePackage(__file__), env
                        )

    def test_rejects_wrong_target_archive_machine(self):
        with tempfile.TemporaryDirectory() as temporary:
            env, root, _, archive = self.complete_artifacts(temporary)
            libdir = os.path.join(root, "usr", "lib")
            os.makedirs(libdir)
            with open(os.path.join(libdir, "libwrong.a"), "wb") as library:
                library.write(b"!<arch>\n")
            self.create_archive(root, archive)
            wrong_header = self.valid_header.replace(
                "Advanced Micro Devices X86-64", "AArch64"
            )
            result = subprocess.CompletedProcess([], 0, wrong_header, "")

            with mock.patch("support.audit.subprocess.run", return_value=result):
                with self.assertRaisesRegex(audit.AuditError, "ELF machine"):
                    audit.audit_package("example", self.FakePackage(__file__), env)

    def test_relocatable_objects_and_archives_skip_program_headers(self):
        for extension, prefix in ((".o", b"\x7fELFstub"), (".a", b"!<arch>\n")):
            with self.subTest(
                extension=extension
            ), tempfile.TemporaryDirectory() as temporary:
                env, root, _, archive = self.complete_artifacts(temporary)
                libdir = os.path.join(root, "usr", "lib")
                os.makedirs(libdir)
                with open(
                    os.path.join(libdir, "example" + extension), "wb"
                ) as artifact:
                    artifact.write(prefix)
                self.create_archive(root, archive)
                relocatable_header = self.valid_header.replace(
                    "DYN (Shared object file)", "REL (Relocatable file)"
                )

                def readelf(command, **kwargs):
                    self.assertNotIn("-lW", command)
                    return self.readelf_result(
                        command, header=relocatable_header
                    )

                with mock.patch(
                    "support.audit.subprocess.run", side_effect=readelf
                ):
                    audit.audit_package(
                        "example", self.FakePackage(__file__), env
                    )

    def test_rejects_missing_soname_and_unsafe_needed(self):
        cases = (
            ("0x1 (NEEDED) Shared library: [libc.so]\n", "no SONAME"),
            (
                "0xe (SONAME) Library soname: [libexample.so.1]\n"
                "0x1 (NEEDED) Shared library: [/tmp/libbad.so]\n",
                "unsafe NEEDED",
            ),
            (
                "0xe (SONAME) Library soname: [libexample.so.1]\n"
                "0x1 (NEEDED) Shared library: [libc.so] /tmp/evil]\n",
                "unsafe NEEDED",
            ),
            (
                "0xe (SONAME) Library soname: [libexample.so.1]\n"
                "0x1 (NEEDED) Shared library: [bad[libc.so]\n",
                "unsafe NEEDED",
            ),
        )
        for dynamic, message in cases:
            with self.subTest(
                message=message
            ), tempfile.TemporaryDirectory() as temporary:
                env, root, _, archive = self.complete_artifacts(temporary)
                libdir = os.path.join(root, "usr", "lib")
                os.makedirs(libdir)
                with open(os.path.join(libdir, "libexample.so.1"), "wb") as library:
                    library.write(b"\x7fELFstub")
                self.create_archive(root, archive)
                readelf = lambda command, **kwargs: self.readelf_result(
                    command, dynamic=dynamic
                )

                with mock.patch("support.audit.subprocess.run", side_effect=readelf):
                    with self.assertRaisesRegex(audit.AuditError, message):
                        audit.audit_package(
                            "example", self.FakePackage(__file__), env
                        )

    def test_rejects_unsafe_runpaths(self):
        cases = (
            (
                "/workspace/.build/x86_64/sysroot/usr/lib",
                "RUNPATH contains build path",
            ),
            ("/home/builder/lib", "RUNPATH contains unsafe host path"),
            ("relative/lib", "unsafe relative entry"),
            (":/usr/lib", "current-directory entry"),
            ("/usr/lib]:/tmp/evil", "unsafe host path"),
            ("/tmp/evil[/usr/lib", "unsafe host path"),
            ("/usr/lib/../../var/tmp", "non-canonical absolute entry"),
            ("$ORIGIN/../../../../var/tmp", "escapes package root"),
        )
        for runpath, message in cases:
            with self.subTest(
                runpath=runpath
            ), tempfile.TemporaryDirectory() as temporary:
                env, root, _, archive = self.complete_artifacts(temporary)
                bindir = os.path.join(root, "usr", "bin")
                with open(os.path.join(bindir, "elf-example"), "wb") as executable:
                    executable.write(b"\x7fELFstub")
                self.create_archive(root, archive)
                dynamic = (
                    "0x1 (NEEDED) Shared library: [libc.so]\n"
                    "0x1d (RUNPATH) Library runpath: [%s]\n" % runpath
                )
                readelf = lambda command, **kwargs: self.readelf_result(
                    command, dynamic=dynamic
                )

                with mock.patch(
                    "support.audit.subprocess.run", side_effect=readelf
                ):
                    with self.assertRaisesRegex(audit.AuditError, message):
                        audit.audit_package(
                            "example", self.FakePackage(__file__), env
                        )

    def test_requires_pedigree_interpreter_for_dynamic_executables(self):
        cases = (
            ("", "has no PT_INTERP"),
            (
                "[Requesting program interpreter: /lib64/ld-linux-x86-64.so.2]",
                "unsafe PT_INTERP",
            ),
            (
                "[Requesting program interpreter: "
                "/usr/lib/ld-musl-x86_64.so.1]evil]",
                "unsafe PT_INTERP",
            ),
        )
        for program_headers, message in cases:
            with self.subTest(
                program_headers=program_headers
            ), tempfile.TemporaryDirectory() as temporary:
                env, root, _, archive = self.complete_artifacts(temporary)
                executable = os.path.join(root, "usr", "bin", "elf-example")
                with open(executable, "wb") as output:
                    output.write(b"\x7fELFstub")
                os.chmod(executable, 0o755)
                self.create_archive(root, archive)
                dynamic = "0x1 (NEEDED) Shared library: [libc.so]\n"
                readelf = lambda command, **kwargs: self.readelf_result(
                    command,
                    dynamic=dynamic,
                    program_headers=program_headers,
                )

                with mock.patch(
                    "support.audit.subprocess.run", side_effect=readelf
                ):
                    with self.assertRaisesRegex(audit.AuditError, message):
                        audit.audit_package(
                            "example", self.FakePackage(__file__), env
                        )

    def test_rejects_executable_gnu_stack(self):
        executable_stack_headers = (
            "GNU_STACK 0x000000 0x0000000000000000 0x0000000000000000 "
            "0x000000 0x000000 RWE 0x10\n",
            "GNU_STACK 0x000000 0x0000000000000000 0x0000000000000000 "
            "0x000000 0x000000 R E 0x10\n",
        )
        for program_headers in executable_stack_headers:
            with self.subTest(
                program_headers=program_headers
            ), tempfile.TemporaryDirectory() as temporary:
                env, root, _, archive = self.complete_artifacts(temporary)
                executable = os.path.join(root, "usr", "bin", "elf-example")
                with open(executable, "wb") as output:
                    output.write(b"\x7fELFstub")
                os.chmod(executable, 0o755)
                self.create_archive(root, archive)
                readelf = lambda command, **kwargs: self.readelf_result(
                    command, program_headers=program_headers
                )

                with mock.patch(
                    "support.audit.subprocess.run", side_effect=readelf
                ):
                    with self.assertRaisesRegex(
                        audit.AuditError, "executable GNU_STACK"
                    ):
                        audit.audit_package(
                            "example", self.FakePackage(__file__), env
                        )

    def test_accepts_non_executable_or_missing_gnu_stack(self):
        program_header_cases = (
            "",
            "GNU_STACK 0x000000 0x0000000000000000 0x0000000000000000 "
            "0x000000 0x000000 RW 0x10\n",
        )
        for program_headers in program_header_cases:
            with self.subTest(
                program_headers=program_headers
            ), tempfile.TemporaryDirectory() as temporary:
                env, root, _, archive = self.complete_artifacts(temporary)
                executable = os.path.join(root, "usr", "bin", "elf-example")
                with open(executable, "wb") as output:
                    output.write(b"\x7fELFstub")
                os.chmod(executable, 0o755)
                self.create_archive(root, archive)
                readelf = lambda command, **kwargs: self.readelf_result(
                    command, program_headers=program_headers
                )

                with mock.patch(
                    "support.audit.subprocess.run", side_effect=readelf
                ):
                    audit.audit_package(
                        "example", self.FakePackage(__file__), env
                    )

    def test_exec_type_requires_interpreter_even_with_so_filename(self):
        with tempfile.TemporaryDirectory() as temporary:
            env, root, _, archive = self.complete_artifacts(temporary)
            executable = os.path.join(root, "usr", "bin", "tool.so")
            with open(executable, "wb") as output:
                output.write(b"\x7fELFstub")
            os.chmod(executable, 0o755)
            self.create_archive(root, archive)
            dynamic = "0x1 (NEEDED) Shared library: [libc.so]\n"
            exec_header = self.valid_header.replace(
                "DYN (Shared object file)", "EXEC (Executable file)"
            )
            readelf = lambda command, **kwargs: self.readelf_result(
                command, dynamic=dynamic, header=exec_header
            )

            with mock.patch("support.audit.subprocess.run", side_effect=readelf):
                with self.assertRaisesRegex(audit.AuditError, "has no PT_INTERP"):
                    audit.audit_package(
                        "example", self.FakePackage(__file__), env
                    )

    def test_accepts_pedigree_interpreter_and_origin_runpath(self):
        with tempfile.TemporaryDirectory() as temporary:
            env, root, _, archive = self.complete_artifacts(temporary)
            executable = os.path.join(root, "usr", "bin", "elf-example")
            with open(executable, "wb") as output:
                output.write(b"\x7fELFstub")
            os.chmod(executable, 0o755)
            self.create_archive(root, archive)
            dynamic = (
                "0x1 (NEEDED) Shared library: [libc.so]\n"
                "0x1d (RUNPATH) Library runpath: [$ORIGIN/../lib]\n"
            )
            program_headers = (
                "[Requesting program interpreter: "
                "/usr/lib/ld-musl-x86_64.so.1]\n"
            )
            readelf = lambda command, **kwargs: self.readelf_result(
                command,
                dynamic=dynamic,
                program_headers=program_headers,
            )

            with mock.patch("support.audit.subprocess.run", side_effect=readelf):
                audit.audit_package("example", self.FakePackage(__file__), env)

    def test_accepts_exact_braced_origin_in_runtime_library_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            env, root, _, archive = self.complete_artifacts(temporary)
            libdir = os.path.join(root, "usr", "lib")
            os.makedirs(libdir)
            with open(os.path.join(libdir, "plugin.so"), "wb") as plugin:
                plugin.write(b"\x7fELFstub")
            self.create_archive(root, archive)
            dynamic = (
                "0x1 (NEEDED) Shared library: [libc.so]\n"
                "0x1d (RUNPATH) Library runpath: [${ORIGIN}]\n"
            )
            readelf = lambda command, **kwargs: self.readelf_result(
                command, dynamic=dynamic
            )

            with mock.patch("support.audit.subprocess.run", side_effect=readelf):
                audit.audit_package("example", self.FakePackage(__file__), env)


if __name__ == "__main__":
    unittest.main()
