
import webapp2

from views import PackageIndex, PackageUpload, Pup, PackageUploadBlobstore


app = webapp2.WSGIApplication([
    ('/blobstore', PackageUploadBlobstore),
    ('/upload', PackageUpload),
    ('/pup.whl', Pup),
    ('/pup-version', Pup),
    ('/', PackageIndex),
    ('/.*\.pup', PackageIndex),
    ('/.*\.pupdb', PackageIndex),
    ('/.*\.whl', PackageIndex),
])
