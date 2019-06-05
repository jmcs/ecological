#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import platform
import sys

from setuptools import find_packages, setup

VERSION_MAJOR = 1
VERSION_MINOR = 6
REVISION = 0
VERSION = f"{VERSION_MAJOR}.{VERSION_MINOR}.{REVISION}"

python_version_major, python_version_minor = (
    int(version) for version in platform.python_version_tuple()[:-1]
)
install_requires = []

if (python_version_major, python_version_minor) < (3, 6):
    print("Ecological doesn't support Python <= 3.6")
    sys.exit(1)
if (python_version_major, python_version_minor) == (3, 6):
    install_requires = ["dataclasses"]

setup(
    name="ecological",
    packages=find_packages(),
    install_requires=install_requires,
    version=VERSION,
    description="Map a python configuration from environment variables",
    long_description=open("README.rst").read(),
    author="João Santos",
    url="https://github.com/jmcs/ecological",
    license="MIT License",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
    ],
)
