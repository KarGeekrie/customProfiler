# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

setup(
            name='customProfiler',
            version='0.0.0',
            description='TO DO',
            long_description='LONG TO DO',
            author='CEA',
            maintainer="Karim Ammar",
            author_email='karim.ammar@cea.fr',
            packages=find_packages(),
            keywords="profiler",
            install_requires=["psutil"]
      )
