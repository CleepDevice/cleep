#!/bin/bash

#script that build raspiot deb package

CUR_DIR=`pwd`

#add log if --newversion specified in command line
#dch -i

#build raspiot application
cd ../
debuild -us -uc 
debuild clean
rm -rf raspiot.egg-info
rm -rf pyraspiot.egg-info/

cd $CUR_DIR
