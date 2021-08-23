#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from distutils.core import setup
import codecs
import os

def read(*parts):
    """
    Build an absolute path from *parts* and and return the contents of the
    resulting file.  Assume UTF-8 encoding.
    """
    HERE = os.path.abspath(os.path.dirname(__file__))

    with codecs.open(os.path.join(HERE, *parts), "rb", "utf-8") as f:
        return f.read()

setup(
    version='3.0.0',
    url='https://github.com/elsiehupp/wikitools3',
    author=["Alex Zaddach", 'Elsie Hupp'],
    author_email='github at elsiehupp dot com',
    license='GPL v3',
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    name='wikitools3',
    packages=['wikitools3'],
    python_requires=">=3.5",
    keywords = ["wikipedia", "mediawiki", "archive", "scrape", "archiveteam"],
    classifiers = [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Wiki",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    description=(
        'Python package for interacting with a MediaWiki wiki.'
        'It is used by WikiTeam for archiving MediaWiki wikis.'
    ),
)