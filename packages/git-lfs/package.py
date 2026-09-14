import os
import shutil

from support import buildsystem, steps


class GitLfsPackage(buildsystem.Package):
    def name(self):
        return "git-lfs"

    def version(self):
        return "3.8.0"

    def install_deps(self):
        return ["git", "ca-certificates", "dropbear"]

    def download(self, env, target):
        steps.download(
            "https://github.com/git-lfs/git-lfs/releases/download/v3.8.0/"
            "git-lfs-vendor-v3.8.0.tar.gz",
            target,
            sha256="28c49d50bea97d0b860fd1599cc5ab45aac937fd31125db8374bf149bb95622f",
        )

    def build(self, env, srcdir):
        command_env = env.copy()
        go_build_dir = os.path.join(
            env["BUILD_BASE"], "language-ports", "go"
        )
        command_env["PEDIGREE_GO_BUILD_DIR"] = go_build_dir
        steps.cmd(
            [os.path.join(env["APPS_BASE"], "scripts/build-go-pedigree.sh")],
            cwd=srcdir,
            env=command_env,
        )

        artifact_dir = os.path.join(srcdir, "pedigree-artifacts")
        os.makedirs(artifact_dir, exist_ok=True)
        steps.cmd(
            [
                os.path.join(go_build_dir, "linux-amd64/bin/pedigree-go"),
                "build",
                "-mod=vendor",
                "-trimpath",
                "-ldflags=-s -w "
                "-X github.com/git-lfs/git-lfs/v3/config.GitCommit=v3.8.0 "
                "-X github.com/git-lfs/git-lfs/v3/config.Vendor=Pedigree",
                "-o",
                os.path.join(artifact_dir, "git-lfs"),
                "./git-lfs.go",
            ],
            cwd=srcdir,
            env=command_env,
        )

    def deploy(self, env, srcdir, deploydir):
        bindir = os.path.join(deploydir, "usr/bin")
        docdir = os.path.join(deploydir, "usr/share/doc/git-lfs")
        os.makedirs(bindir)
        os.makedirs(docdir)
        shutil.copy2(
            os.path.join(srcdir, "pedigree-artifacts/git-lfs"),
            os.path.join(bindir, "git-lfs"),
        )
        for name in ("LICENSE.md", "README.md"):
            shutil.copy2(os.path.join(srcdir, name), docdir)
