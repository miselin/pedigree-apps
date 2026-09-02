UPSTREAM_VERSION = "16.2.0"
BUILDER_VERSION = "15.3.0"

DISABLED_REASON = (
    "GCC is supplied by the maintained builder toolchain at 15.3.0. The "
    "legacy in-target GCC 8 recipe references missing GCC 4.8 Pedigree "
    "patches and obsolete Autoconf/Automake versions; self-hosting GCC 16.2 "
    "requires a separate bootstrap and target-runtime validation."
)
