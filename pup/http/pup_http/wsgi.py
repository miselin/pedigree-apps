
import webapp2

from views import PackageIndex, PackageUpload


app = webapp2.WSGIApplication([
    ('/upload', PackageUpload),
    ('/.*', PackageIndex),
])
