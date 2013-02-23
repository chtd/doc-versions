#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from setuptools import setup, find_packages

setup(name='doc-versions',
      version='0.1',
      description='Django app for tracking changes in models',
      author='CHTD',
      author_email='info@chtd.ru',
      url='https://github.com/chtd/doc-versions',
      include_package_data=True,
      packages=find_packages(),
     )
