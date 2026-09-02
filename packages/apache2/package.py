UPSTREAM_VERSION = "2.4.68"

DISABLED_REASON = (
    "Apache HTTP Server 2.4.68 needs current APR and APR-util. This catalog "
    "has no APR-util port, and the removed 2.2 recipe depended on an obsolete "
    "Pedigree layout, source-bundled APR trees, and a fixed /src cache file."
)
