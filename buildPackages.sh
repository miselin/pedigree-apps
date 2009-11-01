#!/bin/bash
# Runs through each subdirectory, finding PKGBUILDs and building the packages.
#
# PKGBUILDs are looked for in ARCH/APP/PKGBUILD and ARCH/APP/VER/PKGBUILD

ARCHS="./i686"

dopkg()
{
	# Enter the application directory
	currDir=`pwd`
	echo $1
	cd $1
	
	# Obtain the variables and find our temporary directory for the .tar.gz
	. ./PKGBUILD
	workdir=`basename $source .tar.gz`
	
	# Create the .tar.gz
	mkdir -p $workdir
	cp -R root/* $workdir/
	tar -czf $source $workdir
	rm -rf $workdir
	
	# Create the package itself
	makepkg --nodeps
	
	# Remove the .tar.gz we created
	rm $source
	
	# Remove makepkg's temporary directories
	rm -rf pkg src
	
	# Move to the new package directory ready for adding to the repo later
	mkdir -p /pedigree-apps/new-packages
	mv *.pkg.tar.gz /pedigree-apps/new-packages/
	
	# Return to the original directory
	cd $currDir
}

# Each architecture...
for arch in $ARCHS
do
	# ... And then look in each subdirectory (APPS) ...
	APPS="$arch/*"
	for app in $APPS
	do
		# ... Then is there a PKGBUILD in the application directory?
		if [ -f "$app/PKGBUILD" ]; then
			dopkg $app
		
		# Otherwise, look in the version directory
		else
			VERSIONS="$app/*"
			for ver in $VERSIONS
			do
				if [ -f "$ver/PKGBUILD" ]; then
					dopkg $ver
				fi
			done
		fi
	done
done

# Complete, add packages to the Pacman db now and we're done
cd /pedigree-apps
mv ./new-packages/* ./
rm -rf new-packages
repo-add ./pedigree-main.db.tar.gz *.pkg.tar.gz
