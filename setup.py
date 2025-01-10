# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

setup(
            name='custom_profiler',
            version='0.3.0',
            description='Time and memory profiler',
            long_description='custom_profiler is a simple, interactive and lightweight (the only dependency is psutil) way of profiling the memory and execution time of your python code. Doc in https://github.com/KarGeekrie/customProfiler',
            author='Karim Ammar',
            maintainer="Karim Ammar",
            author_email='karim.ammar@cea.fr',
            packages=find_packages(),
            install_requires=["psutil"],
            keywords="profiler, timer",
            url="https://github.com/KarGeekrie/customProfiler",
            python_requires=">=3.6, <4",
            project_urls={  
                  "Bug Reports": "https://github.com/KarGeekrie/customProfiler/issues",
                  "Source": "https://github.com/KarGeekrie/customProfiler",
            },
      )
