#!/usr/bin/env python

from setuptools import setup, find_packages


setup(name='pup',
      version='1.0',
      description='Pedigree UPdater',
      author='Matthew Iselin',
      author_email='matthew@theiselins.net',
      url='https://www.pedigree-project.org',
      packages=find_packages(),
      data_files=[('config', ['pup.conf.default'])],
      entry_points={
          'console_scripts': [
              'pup=pedigree_updater.frontend.main:main',
          ],
      },
      )
