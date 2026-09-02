LEGACY_VERSION = "0.1"

DISABLED_REASON = (
    "The target updater is a source-tree Python 2 setup.py package that "
    "installs to /applications, /libraries/python2.7, and /support. Its client "
    "must be ported to Python 3 and an FHS/runtime dependency contract before "
    "pedigree-updater can be re-enabled."
)
