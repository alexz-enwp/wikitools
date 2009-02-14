#!/usr/bin/env python

from distutils.core import setup

setup(name='wikitools',
      version='0.1.1',
      description='Python package for interacting with a MediaWiki wiki',
	  long_description = """A Python package for interacting with a MediaWiki wiki using the MediaWiki API.
Designed for MediaWiki version 1.14 and higher, should work on 1.13, older
versions may have bugs.
The edit-API must be enabled on the site to use editing features.
This is atill a beta release and may have bugs, especially when dealing with
non-ASCII text.""",
      author='Alex Z. (User:Mr.Z-man @ en.wikipedia)',
      author_email='mrzmanwiki@gmail.com',
      url='http://code.google.com/p/python-wikitools/',
	  license='GPL v3',
      packages=['wikitools'],
     )