#!/usr/bin/env python

from distutils.core import setup

setup(name='wikitools_py3',
      version='1.2',
      description='Python package for interacting with a MediaWiki wiki',
      long_description = """A Python package for interacting with a MediaWiki wiki using the MediaWiki API.
Designed for MediaWiki version 1.20 and higher, should work on 1.13+.
The edit-API must be enabled on the site to use editing features.
Please report any bugs to <https://github.com/alexz-enwp/wikitools/issues>""",
      author='Alex Zaddach (User:Mr.Z-man @ en.wikipedia)',
      author_email='mrzmanwiki@gmail.com',
      url='https://github.com/alexz-enwp/wikitools',
      license='GPL v3',
      packages=['wikitools_py3'],
      package_data={'wikitools_py3': ['COPYING']}
     )
