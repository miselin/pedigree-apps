import os
import shutil

from support import buildsystem
from support import steps


class CaCertificatesPackage(buildsystem.Package):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = buildsystem.Options()
        self._options.tarfile_format = "bare"

    def name(self):
        return "ca-certificates"

    def version(self):
        return "2026.08.13"

    def options(self):
        return self._options

    def download(self, env, target):
        steps.download(
            "https://curl.se/ca/cacert-2026-08-13.pem",
            target,
            sha256=(
                "f66dff1bdf8f96060b8177976f8b7d92"
                "54bc89bc4db933d769f7384d28480bc9"
            ),
        )

    def deploy(self, env, srcdir, deploydir):
        ssl_dir = os.path.join(deploydir, "etc", "ssl")
        os.makedirs(ssl_dir)
        destination = os.path.join(ssl_dir, "cert.pem")
        shutil.copyfile(os.path.join(srcdir, "source"), destination)
        os.chmod(destination, 0o644)

    def postdeploy(self, env, srcdir, deploydir):
        bundle = os.path.join(deploydir, "etc", "ssl", "cert.pem")
        with open(bundle, "rb") as source:
            contents = source.read()

        certificate_begin = b"-----BEGIN CERTIFICATE-----"
        certificate_end = b"-----END CERTIFICATE-----"
        certificates = contents.count(certificate_begin)
        if not certificates or certificates != contents.count(certificate_end):
            raise RuntimeError("CA bundle does not contain complete certificates")
        if b"PRIVATE KEY-----" in contents:
            raise RuntimeError("CA bundle contains private key material")
