#!/bin/bash

# Install required modules from own repository
# To perform this, this script download modules.json file that contains all
# available cleep modules. Then it downloads required modules, check if archive
# is valid and install it (backend and frontend only)

CLEEPMODS=( audio cleepbus network parameters system )
LOG_FILE=/tmp/cleepiso.log
GITHUB_OWNER=tangb
GITHUB_REPO=cleep
MODULES_JSON=https://github.com/$GITHUB_OWNER/$GITHUB_REPO/raw/master/modules.json

# Check command result
# $1: command result (usually $?)
# $2: awaited command result
# $3: error message
checkResult() {
    if [ $1 -ne $2 ]
    then
        msg=$3
        if [[ -z "$1" ]]; then
            msg="see output log"
        fi  
        echo -e "${RED}Error occured: $msg.${NOCOLOR}"
        exit 1
    fi  
}

/usr/bin/wget $MODULES_JSON -q --show-progress -O /tmp/modules.json
checkResult $? 0

for CLEEPMOD in "${CLEEPMODS[@]}"; do
    echo "- installing $CLEEPMOD module"
    #download and checksum module
    download=`cat /tmp/modules.json | /usr/bin/jq .list.$CLEEPMOD.download | awk '{ gsub("\"","",$0); print $0}'`
    checksum=`cat /tmp/modules.json | /usr/bin/jq .list.$CLEEPMOD.sha256 | awk '{ gsub("\"","",$0); print $0}'`
    /usr/bin/wget $download -q --show-progress -O /tmp/cleepmod.zip
    echo "$checksum /tmp/cleepmod.zip" > /tmp/cleepmod.sha
    checkResult $? 0
    /usr/bin/sha256sum -c /tmp/cleepmod.sha
    checkResult $? 0
    #install module
    /usr/bin/unzip -q -o -d /tmp/cleepmod /tmp/cleepmod.zip
    checkResult $? 0
    cp -a /tmp/cleepmod/backend/* /usr/lib/python2.7/dist-packages/raspiot/
    checkResult $? 0
    if [ -d "/tmp/cleepmod/frontend/" ]; then
        cp -a /tmp/cleepmod/frontend/* /opt/raspiot/html/
        checkResult $? 0
    fi
    rm -rf /tmp/cleepmod
    rm -f /tmp/cleepmod.zip
    rm -f /tmp/cleepmod.sha
    echo "  Done"
done
rm -f /tmp/modules.json

