UPSTREAM_VERSION = "3.18.2"

DISABLED_REASON = (
    "libfuse 3.18.2 is a userspace half of the FUSE protocol, not a "
    "standalone filesystem layer. Pedigree provides neither /dev/fuse nor "
    "the matching kernel protocol ABI, and no target consumer can exercise "
    "the library without them."
)
