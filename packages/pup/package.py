import os
import shutil

from support import buildsystem


class PupPackage(buildsystem.Package):

    def name(self):
        return "pup"

    def version(self):
        return "1.2"

    def build_requires(self):
        return ["ca-certificates", "python3"]

    def install_deps(self):
        return self.build_requires()

    def deploy(self, env, srcdir, deploydir):
        source = os.path.join(env["APPS_BASE"], "pup")
        package_source = os.path.join(source, "pedigree_updater")
        site_packages = os.path.join(
            deploydir,
            "usr",
            "lib",
            "python3.14",
            "site-packages",
        )
        target_package = os.path.join(site_packages, "pedigree_updater")
        os.makedirs(site_packages)
        shutil.copytree(
            package_source,
            target_package,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                "*_test.py",
            ),
        )
        for root, directories, filenames in os.walk(target_package):
            os.chmod(root, 0o755)
            for directory in directories:
                os.chmod(os.path.join(root, directory), 0o755)
            for filename in filenames:
                os.chmod(os.path.join(root, filename), 0o644)

        bindir = os.path.join(deploydir, "usr", "bin")
        os.makedirs(bindir)
        launcher = os.path.join(self._path, "pup")
        target_launcher = os.path.join(bindir, "pup")
        shutil.copyfile(launcher, target_launcher)
        os.chmod(target_launcher, 0o755)

        config_dir = os.path.join(deploydir, "etc", "pup")
        os.makedirs(config_dir)
        target_config = os.path.join(config_dir, "pup.conf")
        shutil.copyfile(
            os.path.join(source, "pup.conf.default"),
            target_config,
        )
        os.chmod(target_config, 0o644)

        os.makedirs(os.path.join(deploydir, "var", "lib", "pup"))
