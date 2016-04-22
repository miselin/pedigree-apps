
import base64
import lib.cloudstorage as gcs
import hashlib
import webapp2

try:
    import simplejson as json
except ImportError:
    import json

from models import Package, Authorisation, PupModel

from google.appengine.api import app_identity


retry_params = gcs.RetryParams(initial_delay=0.2,
                               max_delay=5.0,
                               backoff_factor=2,
                               max_retry_period=15)
gcs.set_default_retry_params(retry_params)


class PackageIndex(webapp2.RequestHandler):

    def readPackage(self, name):
        filename = '/%s/%s' % (app_identity.get_default_gcs_bucket_name(),
                               name)
        gcs_file = gcs.open(filename)
        result = gcs_file.read()
        gcs_file.close()
        return result

    def doPackage(self):
        requested_package = self.request.path.strip('/')

        package = Package.query(Package.fullname == requested_package).get()

        if package:
            self.response.headers['Content-Type'] = 'application/octet-stream'
            self.response.write(self.readPackage(package.fullname))
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


class PackageUpload(webapp2.RequestHandler):

    def packageToGcs(self, name, contents):
        filename = '/%s/%s' % (app_identity.get_default_gcs_bucket_name(),
                               name)
        write_retry_params = gcs.RetryParams(backoff_factor=1.1)
        gcs_file = gcs.open(filename, 'w',
                            content_type='application/octet-stream',
                            retry_params=write_retry_params)
        gcs_file.write(contents)
        gcs_file.close()

    def noauth(self):
        self.error(403)
        self.response.write('Invalid credentials.')

    def badrequest(self):
        self.error(400)
        self.response.write('Incorrect parameters.')

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

        # OK, we can process the rest now.
        name = self.request.get('name')
        arch = self.request.get('arch')
        vers = self.request.get('vers')
        if not (name and arch and vers):
            self.badrequest()
            return

        # Load contents.
        blob = self.request.get('blob')
        if not blob:
            self.badrequest()
            return

        blob = base64.b64decode(blob)

        hasher = hashlib.sha1()
        hasher.update(blob)
        sha1 = hasher.hexdigest()

        fullname = '%s-%s-%s.pup' % (name, vers, arch)

        # Do we already know of a package like this?
        known_package = Package.query(Package.fullname == fullname).get()
        not_same = True
        if known_package:
            if known_package.sha1 == sha1:
                not_same = False

        if not_same:
            # Write to GCS first.
            self.packageToGcs(fullname, blob)

            # Now create the record.
            package = Package(fullname=fullname, package_name=name,
                              architecture=arch, version=vers, sha1=sha1)
            package.put()

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('ok')


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
