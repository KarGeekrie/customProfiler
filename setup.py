# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

setup(
            name='custom_profiler',
            version='0.1.0',
            description='time and memory profiler',
            long_description='time and memory profiler',
            author='Karim Ammar',
            maintainer="Karim Ammar",
            author_email='karim.ammar@cea.fr',
            packages=find_packages(),
            keywords="profiler",
            install_requires=["psutil"]
      )
