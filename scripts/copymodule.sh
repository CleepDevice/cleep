#!/bin/bash

if [ "$#" -eq 2 ] && [ "$2" = "release" ]; then
    #release dirs
    SOURCE=/tmp/raspiot/
    BACKEND=/root/temp/raspiot/raspiot/modules/
    FRONTEND=/root/temp/raspiot/html/js/modules/
    SCRIPTS=/tmp/scripts/
else
    #dev dirs
    SOURCE=/root/raspiot/
    BACKEND=/usr/lib/python2.7/dist-packages/raspiot/modules/
    FRONTEND=/opt/raspiot/html/js/modules/
    SCRIPTS=/opt/raspiot/scripts/
fi

cd $SOURCE

if [ "$#" -lt 1 ]; then
    echo "Please specify module name"
    exit 1
fi
if [ ! -d "modules/$1" ]; then
    echo "Module '"$SOURCE"modules/$1' doesn't exist"
    exit 1
fi


if [ ! -d "$BACKEND/$1" ]; then
    mkdir -p $BACKEND/$1
fi
cp -a modules/$1/backend/* $BACKEND/$1/.

if [ -d "modules/$1/frontend/" ]; then
    if [ ! -d "$FRONTEND/$1" ]; then
        mkdir -p $FRONTEND/$1
    fi
    cp -a modules/$1/frontend/* $FRONTEND/$1/.
fi

if [ -d "modules/$1/scripts/" ]; then
    if [ ! -d "$SCRIPTS/$1" ]; then
        mkdir -p $SCRIPTS/$1
    fi
    cp -a modules/$1/scripts/* $SCRIPTS/$1/.
fi

