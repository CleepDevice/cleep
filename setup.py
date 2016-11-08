#!/usr/bin/env python
# -*- coding: utf-8 -*-
 
from setuptools import setup, find_packages
 
# notez qu'on import la lib
# donc assurez-vous que l'importe n'a pas d'effet de bord
import raspiot
 
# Ceci n'est qu'un appel de fonction. Mais il est trèèèèèèèèèèès long
# et il comporte beaucoup de paramètres
setup(
    name = 'raspiot',
    version = raspiot.__version__,
    packages = find_packages(),
    author = 'Tanguy BONNEAU',
    author_email = 'tanguy.bonneau+raspiot@gmail.com',
    description = 'Make your own IoT device with a raspberry pi',
    long_description = open('README.md').read(),
    install_requires = open('requirements.txt').readlines(),
    include_package_data = True,
    url = 'http://www.github.com'
)

