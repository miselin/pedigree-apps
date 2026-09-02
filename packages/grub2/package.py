UPSTREAM_VERSION = "2.14"

DISABLED_REASON = (
    "GNU GRUB 2.14 is a host-side boot-image tool, not a Pedigree target "
    "package. The current image build consumes checked-in GRUB Legacy 0.97 "
    "stage2_eltorito files and has no GRUB 2 host-tool or image-generation "
    "contract to package here."
)
