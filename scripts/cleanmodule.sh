#!/bin/bash

if [ "$#" -lt 1 ]; then
    echo "Please specify module name"
    exit 1
fi

if [ -d "/usr/lib/python2.7/dist-packages/raspiot/modules/$1" ]; then
    rm -rf "/usr/lib/python2.7/dist-packages/raspiot/modules/$1"
fi

if [ -d "/opt/raspiot/html/js/modules/$1" ]; then
    rm -rf "/opt/raspiot/html/js/modules/$1"
fi

if [ -d "/opt/raspiot/scripts/$1" ]; then
    rm -rf "/opt/raspiot/scripts/$1"
fi

if [ -d "/opt/raspiot/iinstall/$1" ]; then
    rm -rf "/opt/raspiot/install/$1"
fi

sed -i -E "s/(modules = \[.*)'$1'(.*\].*)/\1\2/" /etc/raspiot/raspiot.conf

