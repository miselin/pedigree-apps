#!/bin/bash

source ./package-info.sh

source "$1/environment.sh"

BASE=$OUTPUT_BASE/$package/$version

# Remove existing files to force our updated version/link
[[ -e $CROSS_BASE/bin/libtool ]] && rm $CROSS_BASE/bin/libtool
[[ -e $CROSS_BASE/bin/libtoolize ]] && rm $CROSS_BASE/bin/libtoolize
[[ -e $CROSS_BASE/include/ltdl.h ]] && rm $CROSS_BASE/include/ltdl.h
[[ -e $CROSS_BASE/include/libltdl ]] && rm -r $CROSS_BASE/include/libltdl
[[ -e $CROSS_BASE/lib/libltdl.a ]] && rm $CROSS_BASE/lib/libltdl.a
[[ -e $CROSS_BASE/lib/libltdl.so ]] && rm $CROSS_BASE/lib/libltdl.so
[[ -e $CROSS_BASE/lib/libltdl.la ]] && rm $CROSS_BASE/lib/libltdl.la

cp $BASE/applications/libtool $CROSS_BASE/bin/libtool
cp $BASE/applications/libtoolize $CROSS_BASE/bin/libtoolize

# Rename all paths in the newly copied libtool
sed -i -e 's|/applications|'$BASE'/applications|g' $CROSS_BASE/bin/libtool
sed -i -e 's|/support|'$BASE'/support|g' $CROSS_BASE/bin/libtool
sed -i -e 's|/include|'$BASE'/include|g' $CROSS_BASE/bin/libtool
sed -i -e 's|/libraries|'$BASE'/libraries|g' $CROSS_BASE/bin/libtool

sed -i 's|/applications|'$BASE'/applications|g' $CROSS_BASE/bin/libtoolize
sed -i -e 's|/support|'$BASE'/support|g' $CROSS_BASE/bin/libtoolize
sed -i -e 's|/include|'$BASE'/include|g' $CROSS_BASE/bin/libtoolize
sed -i -e 's|/libraries|'$BASE'/libraries|g' $CROSS_BASE/bin/libtoolize

ln -s $BASE/include/ltdl.h $CROSS_BASE/include/ltdl.h
ln -s $BASE/include/libltdl $CROSS_BASE/include/libltdl

ln -s $BASE/libraries/libltdl.a $CROSS_BASE/lib/libltdl.a
ln -s $BASE/libraries/libltdl.so $CROSS_BASE/lib/libltdl.so
ln -s $BASE/libraries/libltdl.la $CROSS_BASE/lib/libltdl.la
