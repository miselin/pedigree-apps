#!/usr/bin/env python

from distutils.core import setup

setup(name='pup',
      version='1.0',
      description='Pedigree UPdater',
      author='Matthew Iselin',
      author_email='matthew@theiselins.net',
      url='https://www.pedigree-project.org',
      packages=['pup', 'pup.commands', 'pup.lib'],
      scripts=['scripts/pup'],
      data_files=[('/config', ['pup.conf.default'])],
)
