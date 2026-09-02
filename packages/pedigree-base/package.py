LEGACY_VERSION = "0.1"

DISABLED_REASON = (
    "The main build still owns images/base and translates that tree to FHS "
    "only while composing a disk image. It does not publish a versioned FHS "
    "staging root, so packaging the mounted checkout as legacy version 0.1 "
    "would produce mutable, untraceable PUP contents."
)
