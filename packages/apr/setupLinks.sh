#!/bin/bash

source ./package-info.sh

source $1/environment.sh

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/lib/libapr-1.a ]] && rm $CROSS_BASE/lib/libapr-1.a
[[ -e $CROSS_BASE/lib/libapr-1.so ]] && rm $CROSS_BASE/lib/libapr-1.so
rm -f $CROSS_BASE/include/apr_*.h

echo "        * libapr-1.a"
ln -s $BASE/libraries/libapr-1.a $CROSS_BASE/lib/libapr-1.a
echo "        * libapr-1.so"
ln -s $BASE/libraries/libapr-1.so.0.4.2 $CROSS_BASE/lib/libapr-1.so

for f in $BASE/include/*.h; do
    short=`basename $f`
    echo "        * $short"
    ln -s $f $CROSS_BASE/include/$short
done

