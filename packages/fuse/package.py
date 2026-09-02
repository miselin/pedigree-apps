UPSTREAM_VERSION = "3.18.2"

DISABLED_REASON = (
    "libfuse 3.18.2 requires the FUSE kernel protocol and /dev/fuse. "
    "Pedigree does not provide that device/protocol ABI, and the historical "
    "entry contains no source or build implementation."
)
