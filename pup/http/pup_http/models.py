
from google.appengine.ext import ndb


class Package(ndb.Model):
    """Model representing a package in the system."""
    fullname = ndb.StringProperty(indexed=True)
    package_name = ndb.StringProperty(indexed=False)
    architecture = ndb.StringProperty(indexed=True)
    version = ndb.StringProperty(indexed=False)
    sha1 = ndb.StringProperty(indexed=False)
    blob = ndb.BlobKeyProperty()
    uploaded_at = ndb.DateTimeProperty(auto_now=True, auto_now_add=True)


class Authorisation(ndb.Model):
    """Model representing authorisation permission in the system."""
    key_name = ndb.StringProperty(indexed=True)
    key_value = ndb.StringProperty(indexed=False)
    allowed = ndb.BooleanProperty(indexed=False, default=True)


class PupModel(ndb.Model):
    """This is entirely the wrong way to do this."""
    pup_version = ndb.IntegerProperty(indexed=True)
    pup_contents = ndb.BlobProperty(indexed=False, compressed=True)


class DepsModel(ndb.Model):
    """This is ALSO entirely the wrong way to do this."""
    deps_arch = ndb.StringProperty(indexed=True)
    # SVG.
    deps_contents = ndb.BlobProperty(indexed=False, compressed=True)
