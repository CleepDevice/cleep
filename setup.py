#!/usr/bin/env python
# -*- coding: utf-8 -*-
 
from setuptools import setup, find_packages
 
import raspiot
 
setup(
    name = 'pyraspiot',
    version = raspiot.__version__,
    packages = find_packages(),
    author = 'Tanguy Bonneau',
    author_email = 'tanguy.bonneau+raspiot@gmail.com',
    description = 'Make your own IoT device with a raspberry pi',
    long_description = open('README.md').read(),
    install_requires = open('requirements.txt').readlines(),
    include_package_data = True,
    url = 'http://www.github.com/tangb/raspiot'
)

