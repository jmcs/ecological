#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import platform

from setuptools import setup, find_packages

VERSION_MAJOR = 1
VERSION_MINOR = 1
VERSION = '{VERSION_MAJOR}.{VERSION_MINOR}'.format_map(locals())

python_version_major, python_version_minor = (int(version) for version in platform.python_version_tuple()[:-1])

if python_version_major < 3:
    print("Ecological doesn't support Python 2")


setup(
    name='ecological',
    packages=find_packages(),
    version=VERSION,
    description='Map a python configuration from environment variables',
    long_description=open('README.rst').read(),
    author='Zalando SE',
    url='https://github.com/jmcs/ecological',
    license='MIT License',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
    ],
)
