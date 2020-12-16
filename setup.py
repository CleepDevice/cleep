#!/usr/bin/env python
# -*- coding: utf-8 -*-
 
from setuptools import setup, find_packages
 
import cleep

exclude = [
    "*tests*",
    "modules"
]
 
setup(
    name = 'cleep',
    version = cleep.__version__,
    packages = find_packages(exclude=exclude),
    author = 'Tanguy Bonneau',
    author_email = 'tanguy.bonneau+cleep@gmail.com',
    description = 'Build your own IoT device with a raspberry pi',
    long_description = open('README.md').read(),
    install_requires = open('requirements.txt').readlines(),
    include_package_data = True,
    url = 'http://www.github.com/tangb/cleep',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Free For Home Use",
        "Operating System :: POSIX :: Linux"
    ],
    python_requires='~=3.7',
)

