
import base64
import collections
import itertools
import jinja2
import os
import webapp2

try:
    import simplejson as json
except ImportError:
    import json

from models import Package, Authorisation, PupModel, DepsModel

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


def pad_list(l, to_length, value=0):
    if len(l) < to_length:
        l += [value] * to_length - len(l)
    return l


def version_cmp(vers1, vers2):
    vers1 = [int(x) for x in vers1.split('.')]
    vers2 = [int(x) for x in vers2.split('.')]

    desired_len = max(len(vers1), len(vers2))

    vers1 = pad_list(vers1, desired_len)
    vers2 = pad_list(vers2, desired_len)

    for comp in itertools.izip(vers1, vers2):
        if vers1 < vers2:
            return -1
        elif vers1 > vers2:
            return 1

    return 0


def dedup_packages(packages):
    """De-duplicate packages in the given list by using the latest version."""
    all_packages = collections.defaultdict(list)
    for package in packages:
        name = package.package_name
        arch = package.architecture

        all_packages['%s-%s' % (name, arch)].append(package)

    result = []
    for name, versions in all_packages.iteritems():
        if len(versions) > 1:
            versions = sorted(versions,
                              cmp=lambda x, y: version_cmp(x.version,
                                                           y.version),
                              reverse=True)

        result.append(versions[0])

    # Sort resulting packages alphabetically.
    return sorted(result, key=lambda x: x.package_name)


class PackageIndex(blobstore_handlers.BlobstoreDownloadHandler):

    def doPackage(self):
        requested_package = self.request.path.strip('/')

        package = Package.query(Package.fullname == requested_package).get()

        if package and blobstore.get(package.blob):
            self.response.headers['Content-Type'] = 'application/octet-stream'
            self.send_blob(package.blob)
        else:
            self.error(404)
            self.response.write('That package does not exist.')

    def doDatabase(self):
        packages = Package.query().iter()
        all_packages = dedup_packages(packages)

        result = {}
        for package in all_packages:
            name = package.package_name
            arch = package.architecture
            vers = package.version
            sha1 = package.sha1

            result['%s-%s' % (name, arch)] = {
                'architecture': arch,
                'version': vers,
                'name': name,
                'sha1': sha1,
            }

        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(result))

    def doIndex(self):
        self.response.headers['Content-Type'] = 'text/html'

        query = Package.query(projection=['architecture'], distinct=True)
        archs = [x.architecture for x in query]

        # Load graphs.
        graphs = {}
        for dep in DepsModel.query().iter():
            graphs[dep.deps_arch] = True

        packages = dedup_packages(Package.query().fetch(None))

        template_data = {
            # TODO(miselin): this should be figured out from datastore.
            'archs': archs,
            'packages': packages,
            'graphs': graphs,
        }

        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        self.response.write(template.render(template_data))

    def get(self):
        path = self.request.path
        if path == '/' or path.startswith('/index.'):
            self.doIndex()
        elif path == '/packages.pupdb':
            self.doDatabase()
        else:
            self.doPackage()


class PackageUploadBlobstore(blobstore_handlers.BlobstoreUploadHandler):

    def badrequest(self):
        self.error(400)
        self.response.write('Incorrect parameters.')

    def post(self):
        # OK, we can process the rest now.
        name = self.request.get('name')
        arch = self.request.get('arch')
        vers = self.request.get('vers')
        sha1 = self.request.get('sha1')
        if not (name and arch and vers and sha1):
            self.badrequest()
            return

        try:
            uploaded = self.get_uploads()[0]
            uploaded_key = uploaded.key()
        except:
            self.badrequest()
            return

        fullname = '%s-%s-%s.pup' % (name, vers, arch)

        # Do we already know of a package like this?
        known_package = Package.query(Package.fullname == fullname).get()

        if not known_package:
            # Now create the record.
            package = Package(fullname=fullname, package_name=name,
                              architecture=arch, version=vers, sha1=sha1,
                              blob=uploaded_key)
            package.put()
        else:
            # Wipe out the created item in blobstore, we don't need it.
            item = blobstore.get(known_package.blob)
            item.delete()

            # Update the package contents.
            known_package.sha1 = sha1
            known_package.blob = uploaded_key
            known_package.put()

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('ok')


class PackageUpload(webapp2.RequestHandler):

    def noauth(self):
        self.error(403)
        self.response.write('Invalid credentials.')

    def get(self):
        # Does the user have the right credential?
        cred_name = self.request.get('key')
        cred_value = self.request.get('key_value')
        if not (cred_name and cred_value):
            self.noauth()
            return

        query = Authorisation.query(Authorisation.key_name == cred_name)
        credential = query.get()
        if not credential:
            self.noauth()
            return

        if credential.key_value != cred_value:
            self.noauth()
            return

        if not credential.allowed:
            self.noauth()
            return

        # Get URL for blobstore upload.
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write(blobstore.create_upload_url('/blobstore'))


class Pup(webapp2.RequestHandler):

    def noauth(self):
        self.error(403)
        self.response.write('Invalid credentials.')

    def badrequest(self):
        self.error(400)
        self.response.write('Incorrect parameters.')

    def get(self):
        pup = PupModel.query().order(-PupModel.pup_version).get()
        if not pup:
            self.error(404)
            self.response.write('pup is not present')
        else:
            if self.request.path == '/pup-version':
                self.response.headers['Content-Type'] = 'text/plain'
                self.response.write(pup.pup_version)
            else:
                content_type = 'application/octet-stream'
                self.response.headers['Content-Type'] = content_type
                self.response.write(pup.pup_contents)

    def post(self):
        # Does the user have the right credential?
        cred_name = self.request.get('key')
        cred_value = self.request.get('key_value')
        if not (cred_name and cred_value):
            self.noauth()
            return

        query = Authorisation.query(Authorisation.key_name == cred_name)
        credential = query.get()
        if not credential:
            self.noauth()
            return

        if credential.key_value != cred_value:
            self.noauth()
            return

        if not credential.allowed:
            self.noauth()
            return

        version = int(self.request.get('version'))

        # Load contents.
        blob = self.request.get('blob')
        if not blob:
            self.badrequest()
            return

        blob = base64.b64decode(blob)

        known_pup = PupModel.query(PupModel.pup_version == version).get()
        if known_pup:
            self.error(400)
            self.response.write('Version already exists.')
            return

        PupModel(pup_version=version, pup_contents=blob).put()

        self.response.write('ok')


class Svg(webapp2.RequestHandler):

    def noauth(self):
        self.error(403)
        self.response.write('Invalid credentials.')

    def badrequest(self):
        self.error(400)
        self.response.write('Incorrect parameters.')

    def get(self):
        path = self.request.path
        arch = path.replace('.svg', '').split('-', 1)[1]

        deps = DepsModel.query(DepsModel.deps_arch == arch).get()
        if not deps:
            self.error(404)
            self.response.write('invalid path')
        else:
            self.response.headers['Content-Type'] = 'image/svg+xml'
            self.response.write(deps.deps_contents)

    def post(self):
        # Does the user have the right credential?
        cred_name = self.request.get('key')
        cred_value = self.request.get('key_value')
        if not (cred_name and cred_value):
            self.noauth()
            return

        query = Authorisation.query(Authorisation.key_name == cred_name)
        credential = query.get()
        if not credential:
            self.noauth()
            return

        if credential.key_value != cred_value:
            self.noauth()
            return

        if not credential.allowed:
            self.noauth()
            return

        arch = self.request.get('arch')

        # Load contents.
        blob = self.request.get('blob').encode('utf-8')
        if not (blob and arch):
            self.badrequest()
            return

        entry = DepsModel.query(DepsModel.deps_arch == arch).get()
        if entry:
            entry.deps_contents = blob
            entry.put()
        else:
            DepsModel(deps_arch=arch, deps_contents=blob).put()

        self.response.write('ok')
