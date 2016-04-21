
import base64
import hashlib
import webapp2

try:
    import simplejson as json
except ImportError:
    import json

from models import Package, Authorisation


class PackageIndex(webapp2.RequestHandler):

    def doPackage(self):
        requested_package = self.request.path.strip('/')

        package = Package.query(Package.fullname == requested_package).get()

        if package:
            self.response.headers['Content-Type'] = 'application/octet-stream'
            self.response.write(package.contents)
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
</li>''')

        # TODO(miselin): add information for human readability.
        for package in Package.query().iter():
            self.response.write('''<li>
    <a href="/%s">%s</a>
</li>''' % (package.fullname, package.fullname))

    def get(self):
        path = self.request.path
        if path == '/':
            self.doIndex()
        elif path == '/packages.pupdb':
            self.doDatabase()
        else:
            self.doPackage()


class PackageUpload(webapp2.RequestHandler):

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
            package = Package(fullname=fullname, package_name=name,
                              architecture=arch, version=vers, sha1=sha1,
                              contents=blob)
            package.put()

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('ok')
