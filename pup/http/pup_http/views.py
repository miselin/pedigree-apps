import base64
import collections
import hmac
import json
from functools import cmp_to_key
from io import BytesIO

from flask import Flask, Response, render_template, request
from google.appengine.ext import blobstore

from .models import Authorisation, DepsModel, Package, PupModel

flask_app = Flask(__name__, static_folder=None)


def version_cmp(version_one, version_two):
    parts_one = [int(component) for component in version_one.split(".")]
    parts_two = [int(component) for component in version_two.split(".")]
    desired_length = max(len(parts_one), len(parts_two))

    parts_one.extend([0] * (desired_length - len(parts_one)))
    parts_two.extend([0] * (desired_length - len(parts_two)))
    return (parts_one > parts_two) - (parts_one < parts_two)


def dedup_packages(packages):
    """De-duplicate packages by name and architecture, keeping the latest."""
    all_packages = collections.defaultdict(list)
    for package in packages:
        key = f"{package.package_name}-{package.architecture}"
        all_packages[key].append(package)

    result = []
    for versions in all_packages.values():
        versions.sort(
            key=cmp_to_key(
                lambda left, right: version_cmp(left.version, right.version)
            ),
            reverse=True,
        )
        result.append(versions[0])

    return sorted(result, key=lambda package: package.package_name)


def text_response(body, status=200, content_type="text/plain"):
    return Response(body, status=status, content_type=content_type)


def request_is_authorised():
    credential_name = request.values.get("key")
    credential_value = request.values.get("key_value")
    if not credential_name or not credential_value:
        return False

    credential = Authorisation.query(Authorisation.key_name == credential_name).get()
    return bool(
        credential
        and credential.allowed
        and hmac.compare_digest(credential.key_value, credential_value)
    )


def invalid_credentials():
    return text_response("Invalid credentials.", status=403)


def invalid_parameters():
    return text_response("Incorrect parameters.", status=400)


@flask_app.get("/")
@flask_app.get("/index.<extension>")
def index(extension=None):
    architecture_query = Package.query(projection=["architecture"], distinct=True)
    architectures = [package.architecture for package in architecture_query]
    graphs = {dependency.deps_arch: True for dependency in DepsModel.query().iter()}
    packages = dedup_packages(Package.query().fetch(None))
    return render_template(
        "index.html",
        archs=architectures,
        packages=packages,
        graphs=graphs,
    )


@flask_app.get("/packages.pupdb")
def package_database():
    result = {}
    for package in dedup_packages(Package.query().iter()):
        key = f"{package.package_name}-{package.architecture}"
        result[key] = {
            "architecture": package.architecture,
            "version": package.version,
            "name": package.package_name,
            "sha1": package.sha1,
        }

    return text_response(json.dumps(result), content_type="application/json")


@flask_app.get("/<path:requested_package>")
def download_package(requested_package):
    if not requested_package.endswith((".pup", ".pupdb", ".whl")):
        return text_response("That package does not exist.", status=404)

    package = Package.query(Package.fullname == requested_package).get()
    blob_info = blobstore.get(package.blob) if package else None
    if not blob_info:
        return text_response("That package does not exist.", status=404)

    headers = blobstore.BlobstoreDownloadHandler().send_blob(
        request.environ,
        blob_info,
    )
    headers["Content-Type"] = "application/octet-stream"
    return "", headers


@flask_app.get("/upload")
def package_upload_url():
    if not request_is_authorised():
        return invalid_credentials()
    return text_response(blobstore.create_upload_url("/blobstore"))


@flask_app.post("/blobstore")
def package_upload_blobstore():
    request_body = request.get_data(cache=True)
    name = request.form.get("name")
    architecture = request.form.get("arch")
    version = request.form.get("vers")
    sha1 = request.form.get("sha1")
    if not all((name, architecture, version, sha1)):
        return invalid_parameters()

    request.environ["wsgi.input"] = BytesIO(request_body)
    try:
        uploads = blobstore.BlobstoreUploadHandler().get_uploads(request.environ)
    except blobstore.BlobInfoParseError:
        return invalid_parameters()
    if not uploads:
        return invalid_parameters()
    uploaded_key = uploads[0].key()

    fullname = f"{name}-{version}-{architecture}.pup"
    known_package = Package.query(Package.fullname == fullname).get()
    if known_package:
        previous_blob = blobstore.get(known_package.blob)
        if previous_blob:
            previous_blob.delete()
        known_package.sha1 = sha1
        known_package.blob = uploaded_key
        known_package.put()
    else:
        Package(
            fullname=fullname,
            package_name=name,
            architecture=architecture,
            version=version,
            sha1=sha1,
            blob=uploaded_key,
        ).put()

    return text_response("ok")


@flask_app.route("/pup.whl", methods=["GET", "POST"])
@flask_app.route("/pup-version", methods=["GET", "POST"])
def pup():
    if request.method == "GET":
        latest_pup = PupModel.query().order(-PupModel.pup_version).get()
        if not latest_pup:
            return text_response("pup is not present", status=404)
        if request.path == "/pup-version":
            return text_response(str(latest_pup.pup_version))
        return text_response(
            latest_pup.pup_contents,
            content_type="application/octet-stream",
        )

    if not request_is_authorised():
        return invalid_credentials()

    try:
        version = int(request.form.get("version", ""))
        contents = base64.b64decode(request.form.get("blob", ""), validate=True)
    except ValueError, TypeError:
        return invalid_parameters()
    if not contents:
        return invalid_parameters()

    known_pup = PupModel.query(PupModel.pup_version == version).get()
    if known_pup:
        return text_response("Version already exists.", status=400)

    PupModel(pup_version=version, pup_contents=contents).put()
    return text_response("ok")


@flask_app.route("/<path:dependency_graph>.svg", methods=["GET", "POST"])
def dependency_graph(dependency_graph):
    try:
        architecture = dependency_graph.split("-", 1)[1]
    except IndexError:
        return text_response("invalid path", status=404)

    if request.method == "GET":
        dependency = DepsModel.query(DepsModel.deps_arch == architecture).get()
        if not dependency:
            return text_response("invalid path", status=404)
        return text_response(dependency.deps_contents, content_type="image/svg+xml")

    if not request_is_authorised():
        return invalid_credentials()

    posted_architecture = request.form.get("arch")
    contents = request.form.get("blob", "").encode("utf-8")
    if not contents or not posted_architecture:
        return invalid_parameters()

    entry = DepsModel.query(DepsModel.deps_arch == posted_architecture).get()
    if entry:
        entry.deps_contents = contents
        entry.put()
    else:
        DepsModel(
            deps_arch=posted_architecture,
            deps_contents=contents,
        ).put()

    return text_response("ok")
