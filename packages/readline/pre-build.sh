#!/bin/bash

source "$1/environment.sh"

set -e

cd "$2"

# Prepare to build shared libraries, and don't leak the host (the script
# normally uses uname etc...)

cat <<EOF > ./support/shobj-conf
#!/bin/sh

echo SHOBJ_STATUS=supported
echo SHLIB_STATUS=supported

echo SHOBJ_CC=\'$ARCH_TARGET-pedigree-gcc\'
echo SHOBJ_CFLAGS=\'$CFLAGS -fPIC -shared\'
echo SHOBJ_LD=\'$ARCH_TARGET-pedigree-gcc\'
echo SHOBJ_LDFLAGS=\'$LDFLAGS -shared\'
echo SHOBJ_XLDFLAGS=
echo SHOBJ_LIBS=

echo SHLIB_DOT=\'.\'
echo SHLIB_LIBPREF=\'lib\'
echo SHLIB_LIBSUFF=\'so\'

echo SHLIB_LIBVERSION=\'so\'
echo SHLIB_DLLVERSION=

EOF
