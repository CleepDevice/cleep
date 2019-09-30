#!/bin/bash

#script that builds raspiot deb package and publish it to github repository
#DEPRECATED use cleep-cli build command instead

CUR_DIR=`pwd`
GITHUB_OWNER=tangb
GITHUB_REPO=cleep
GITHUB_ACCESS_TOKEN=`printenv GITHUB_ACCESS_TOKEN`
SENTRY_DSN=`printenv SENTRY_DSN`
#NO_PUBLISH=1

if [ -z "$GITHUB_ACCESS_TOKEN" ]; then
    echo 
    echo "ERROR: github access token not defined, please set an environment variable called GITHUB_ACCESS_TOKEN with a valid token"
    echo
    exit 1
fi

if [ -z "$SENTRY_DSN" ]; then
    echo 
    echo "ERROR: sentry DSN not defined, please set an environment variable called SENTRY_DSN with valid data"
    echo
    exit 1
fi

#generate github release data
# param1: version
# param2: description file path
github_release_data() {
    cat <<EOF
{
  "tag_name": "v$1",
  "target_commitish": "master",
  "name": "$1",
  "body": "`sed -E ':a;N;$!ba;s/\r{0,1}\n/\\\\n/g' $2`",
  "draft": false,
  "prerelease": true
}
EOF
}

#clean all files
clean() {
    echo `pwd`
    rm -rf build
    rm -rf debian/raspiot
    rm -rf debian/*debhelper*
    rm -rf ../raspiot_*_armhf.*
    rm -rf tmp
}

#add log if --newversion specified in command line
#dch -i

#jump in cleep root directory
cd ..

#clean previous build
clean

#check python version
VERSION=`head -n 1 debian/changelog | awk '{ gsub("[\(\)]","",$2); print $2 }'`
PYTHON_VERSION=`cat raspiot/__init__.py | grep $VERSION | wc -l`
if [ "$PYTHON_VERSION" -ne "1" ]
then
    echo
    echo "ERROR: python version is not the same than debian version, please update raspiot/__init__.py __version__ to $VERSION"
    echo
    exit 1
fi

#generate /etc/default/raspiot.conf
mkdir tmp
touch tmp/raspiot.conf
echo "SENTRY_DSN=$SENTRY_DSN" >> tmp/raspiot.conf

#build raspiot application
debuild -us -uc 

#clean python stuff
rm -rf raspiot.egg-info
rm -rf pyraspiot.egg-info/

#move to previous directory where archive was generated
DUMMY_DIR=`pwd`
SRC_DIR=`basename $DUMMY_DIR`
cd ..

#collect variables
DEB=`ls -A1 raspiot* | grep \.deb`
CHANGES=`ls -A1 raspiot* | grep \.changes`
ARCHIVE=raspiot_$VERSION.zip
SHA256=raspiot_$VERSION.sha256
PREINST=$SRC_DIR/scripts/preinst.sh
POSTINST=$SRC_DIR/scripts/postinst.sh

#build zip archive
rm -f *.zip
rm -f *.sha256
cp -a $DEB raspiot.deb
cp -a $PREINST .
cp -a $POSTINST .
zip $ARCHIVE raspiot.deb `basename $PREINST` `basename $POSTINST`
rm -f `basename $PREINST`
rm -f `basename $POSTINST`
rm -f raspiot.deb
sha256sum $ARCHIVE > $SHA256

#get description
sed -n "/raspiot ($VERSION)/,/Checksums-Sha1:/{/raspiot ($VERSION)/b;/Checksums-Sha1:/b;p}" $CHANGES | tail -n +2 > sed.out

#display changes
echo "Files \"$ARCHIVE\" and \"$SHA256\" are ready to be uploaded in https://github.com/$GITHUB_OWNER/$GITHUB_REPO/releases with following informations:"
echo "  - tag version \"v$VERSION\""
echo "  - release title \"$VERSION\""
echo "  - description:"
cat sed.out

#upload to github
if [ -z "$NO_PUBLISH" ]; then
    echo
    echo "Uploading release to github..."
    #https://www.barrykooij.com/create-github-releases-via-command-line/
    curl --silent --output curl.out --data "$(github_release_data "$VERSION" "sed.out")" https://api.github.com/repos/$GITHUB_OWNER/$GITHUB_REPO/releases?access_token=$GITHUB_ACCESS_TOKEN
    ID=`cat curl.out | grep "\"id\":" | head -n 1 | awk '{ gsub(",","",$2); print $2 }'`
    if [ -z "$ID" ]; then
        echo 
        echo "ERROR: problem when creating gihub release. Please check curl.out file content."
        echo
        exit 1
    fi
    #https://gist.github.com/stefanbuck/ce788fee19ab6eb0b4447a85fc99f447
    echo " - Uploading archive"
    curl --output curl.out --progress-bar --data-binary @"$ARCHIVE" -H "Authorization: token $GITHUB_ACCESS_TOKEN" -H "Content-Type: application/octet-stream" "https://uploads.github.com/repos/$GITHUB_OWNER/$GITHUB_REPO/releases/$ID/assets?name=$(basename $ARCHIVE)"
    echo " - Uploading checksum"
    curl --output curl.out --progress-bar --data-binary @"$SHA256" -H "Authorization: token $GITHUB_ACCESS_TOKEN" -H "Content-Type: application/octet-stream" "https://uploads.github.com/repos/$GITHUB_OWNER/$GITHUB_REPO/releases/$ID/assets?name=$(basename $SHA256)"
    rm curl.out
    rm sed.out
    echo "Done."
fi

#clean install
cd -
clean

#return back to original directory
cd $CUR_DIR

