#!/bin/bash

DIR=/root/temp/raspiot/
COPYMODULE=$DIR"scripts/copymodule.sh"
MODULES=("https://github.com/tangb/cleepmod-audio.git" "https://github.com/tangb/cleepmod-cleepbus.git" "https://github.com/tangb/cleepmod-network.git" "https://github.com/tangb/cleepmod-parameters.git" "https://github.com/tangb/cleepmod-system.git")

#jump to tmp dir
rm -rf /tmp/raspiot
mkdir -p /tmp/raspiot/modules
cd /tmp/raspiot/modules

#install modules
for url in ${MODULES[@]}; do
    module=`echo $url | awk -F '[/\.-]' '{ print $7 }'`

    #clone repo
    git clone $url

    #move cleepmod-XXX -> XXX
    mv "cleepmod-"$module $module

    #copy module
    $COPYMODULE $module release

done

#clean everything
rm -rf /tmp/scripts
rm -rf /tmp/raspiot

