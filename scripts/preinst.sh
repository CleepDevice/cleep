#!/bin/sh

apt-get update
apt-get install -y python-dev libffi-dev libssl-dev python-scipy python-numpy
apt-get clean -y
apt-get autoremove -y

