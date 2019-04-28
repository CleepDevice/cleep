#!/bin/bash

# Check command result
# $1: command result (usually $?)
# $2: awaited command result
checkResult() {
    if [ $1 -ne $2 ]
    then
        echo "Error occured. Please check command output."
        exit 1
    fi  
}

#install system dependencies
#we install scipy and numpy from raspiot repositories because it's too long (and problematic) to build these libraries on raspi
apt-get -y update
apt-get install -y python-dev libffi-dev libssl-dev python-scipy python-numpy
checkResult $? 0
apt-get clean -y
apt-get autoremove -y
echo "Done"
echo ""

#install pip (or upgrade if necessary)
echo "Installing pip..."
wget --no-check-certificate -P /tmp/ "https://bootstrap.pypa.io/get-pip.py"
checkResult $? 0
python /tmp/get-pip.py --trusted-host pypi.python.org
checkResult $? 0
rm -f /tmp/get-pip.py
echo "Done"
echo ""

#install python dependencies
echo "Installing python dependencies..."
pip install --no-cache-dir --trusted-host pypi.python.org "future==0.17.1" "six==1.12.0" "gevent==1.4.0" "bottle==0.12.16" "pyre-gevent==0.2.1" "netifaces==0.10.9" "uptime==3.0.1" "urllib3==1.24.2" "psutil==5.6.1" "passlib==1.7.1" "simplejson==3.16.0" "raven==6.10.0" "pytz==2019.1" "reverse-geocode==1.3" "timezonefinder==3.4.2" "tzlocal==1.5.1"
checkResult $? 0
echo "Done"
echo ""

