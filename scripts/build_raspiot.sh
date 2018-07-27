#!/bin/bash

#script that build raspiot deb package

CUR_DIR=`pwd`

#add log if --newversion specified in command line
#dch -i

#jump in raspiot root directory
cd ..

#clean previous build
rm -rf ../raspiot_*_armhf.*

#build raspiot application
debuild -us -uc 

#clean python stuff
rm -rf raspiot.egg-info
rm -rf pyraspiot.egg-info/

#collect variables
cd ..
VERSION=`ls -A1 | grep \.deb | awk -F "_" '{ print $2; }'`
DEB=`ls -A1 | grep \.deb`
CHANGES=`ls -A1 | grep \.changes`
ARCHIVE=raspiot_$VERSION.zip
SHA256=raspiot_$VERSION.sha256
PREINST=raspiot/scripts/preinst.sh
POSTINST=raspiot/scripts/postinst.sh

#check python version
PYTHON_VERSION=`cat raspiot/raspiot/__init__.py | grep $VERSION | wc -l`
if [ "$PYTHON_VERSION" -ne "1" ]
then
    echo "Error: python version is not the same than debian version, please update raspiot/__init__.py __version__ to $VERSION"
    exit 1
fi

#build zip archive
rm -f *.zip
rm -f *.sha256
cp -a $DEB raspiot.deb
cp -a $PREINST .
cp -a $POSTINST .
zip $ARCHIVE raspiot.deb `basename $PREINST` `basename $POSTINST`
rm -f `basename $PREINST`
rm -f `basename $POSTINST`
sha256sum $ARCHIVE > $SHA256

echo "Files \"$ARCHIVE\" and \"$SHA256\" are ready to be uploaded in https://github.com/tangb/raspiot/releases with following informations:"
echo "  - tag version \"v$VERSION\""
echo "  - release title \"$VERSION\""
echo "  - description:"
sed -n "/raspiot ($VERSION)/,/Checksums-Sha1:/{/raspiot ($VERSION)/b;/Checksums-Sha1:/b;p}" $CHANGES

#return back to original directory
cd $CUR_DIR

