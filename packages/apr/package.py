UPSTREAM_VERSION = "1.7.6"

DISABLED_REASON = (
    "APR 1.7.6 cross-configure cannot determine a usable process-shared "
    "mutex/shared-memory backend for Pedigree, and its bundled libtool does "
    "not recognize the pedigree target for shared libraries. A static-only "
    "probe is not sufficient for Apache without APR-util and target runtime "
    "validation."
)
