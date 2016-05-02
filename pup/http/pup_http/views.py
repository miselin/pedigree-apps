
import base64
import jinja2
import os
import webapp2

try:
    import simplejson as json
except ImportError:
    import json

from models import Package, Authorisation, PupModel

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


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
        result = {}
        for package in packages:
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

        template_data = {
            # TODO(miselin): this should be figured out from datastore.
            'archs': ('amd64', 'arm'),
            'packages': Package.query().fetch(None),
        }

        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        self.response.write(template.render(template_data))

        return



        self.response.write('''<!DOCTYPE html>
<html>
<head>
    <title>pup</title>
</head>
<body>
<h1>The Pedigree UPdater Master Repository</h1>
<ul>
<li>
    <a href="/packages.pupdb">packages.pupdb</a>
</li>
<li>
    <a href="/pup.whl">pup.whl</a>
</li>''')

        # TODO(miselin): add information for human readability.
        for package in Package.query().iter():
            self.response.write('''<li>
    <a href="/%s">%s</a>
</li>''' % (package.fullname, package.fullname))

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
