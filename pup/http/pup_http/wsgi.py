
import webapp2

from views import PackageIndex, PackageUpload, Pup


app = webapp2.WSGIApplication([
    ('/upload', PackageUpload),
    ('/pup.whl', Pup),
    ('/pup-version', Pup),
    ('/.*', PackageIndex),
])
