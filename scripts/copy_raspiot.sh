#!/bin/bash

# Script that copies all raspiot files to existing raspiot installation

cd /root/raspiot/
#raspbian jessie (also need to add manually link to new files to /usr/lib/python2.7/dist-packages/raspiot/
cp -a raspiot/* /usr/share/pyshared/raspiot/.
#raspbian stretch
cp -a raspiot/* /usr/share/pyshared/raspiot/.
cp -a html /opt/raspiot/.
cp -a bin/raspiot /usr/bin/raspiot
cp -a medias/sounds/* /opt/raspiot/sounds/
