#!/bin/bash

cd /root/raspiot/

if [ "$#" -ne 1 ]; then
    echo "Please specify module name"
    exit 1
fi
if [ ! -d "modules/$1" ]; then
    echo "Module '/root/raspiot/modules/$1' doesn't exist"
    exit 1
fi

BACKEND=/usr/lib/python2.7/dist-packages/raspiot/modules
FRONTEND=/opt/raspiot/html/js/modules/
SCRIPTS=/opt/raspiot/scripts/

if [ ! -d "$BACKEND/$1" ]; then
    mkdir -p $BACKEND/$1
fi
cp -a modules/$1/backend/* $BACKEND/$1/.

if [ ! -d "$FRONTEND/$1" ]; then
    mkdir -p $FRONTEND/$1
fi
cp -a modules/$1/frontend/* $FRONTEND/$1/.

if [ ! -d "$SCRIPTS/$1" ]; then
    mkdir -p $SCRIPTS/$1
fi
cp -a modules/$1/scripts/* $SCRIPTS/$1/.

