wikitools_py3 -- Package for working with MediaWiki wikis

Requirements
------------

  * Python 3.3+. Tested on 3.4.2
  * The requests package <http://docs.python-requests.org/en/latest/> is required.
  * Basic functionality should be possible in wikis as old as 1.13, but at least
    MediaWiki 1.21 is recommended.

Installation
------------

  * Run "python setup.py install" or copy the wikitools_py3 directory
    to an appropriate Python module directory.
  * An exe installer for Windows is also available (should be run as an
    administrator to avoid errors)
  * An RPM for Linux is also available.

Available modules
-----------------

  * api - Contains the APIRequest class, for doing queries directly,
    see API examples below
  * wiki - Contains the Wiki class, used for logging in to the site,
    storing cookies, and storing basic site information
  * page -  Contains the Page class for dealing with individual pages
    on the wiki. Can be used to get page info and text, as well as edit and
    other actions if enabled on the wiki
  * category - Category is a subclass of Page with extra functions for
    working with categories
  * wikifile - File is a subclass of Page with extra functions for
    working with files - note that there may be some issues with shared
    repositories, as the pages for files on shared repos technically don't
    exist on the local wiki.
  * user - Contains the User class for getting information about and
    blocking/unblocking users
  * pagelist - Contains several functions for getting a list of Page
    objects from lists of titles, pageids, or API query results

Further documentation
---------------------
  * https://github.com/alexz-enwp/wikitools/wiki

Current limitations
-------------------

  * Can only do what the API can do. On a site without the edit-API enabled
    (disabled by default prior to MediaWiki 1.14), you cannot edit/delete/
    protect pages, only retrieve information about them.
  * Usage on restricted-access (logged-out users can't read) wikis is
    mostly untested

Quick start
-----------

To make a simple query:

```python
#!/usr/bin/python

from wikitools_py3 import wiki
from wikitools_py3 import api

# create a Wiki object
site = wiki.Wiki("http://my.wikisite.org/w/api.php")
# login - required for read-restricted wikis
site.login("username", "password")
# define the params for the query
params = {'action':'query', 'titles':'Main Page'}
# create the request object
request = api.APIRequest(site, params)
# query the API
result = request.query()
```

The result will look something like:

```json
{u'query':
	{u'pages':
		{u'15580374':
			{u'ns': 0, u'pageid': 15580374, u'title': u'Main Page'}
		}
	}
}
```

For most normal usage, you may not have to do API queries yourself and can just
use the various classes. For example, to add a template to the top of all the
pages in namespace 0 in a category:

```python
#!/usr/bin/python

from wikitools_py3 import wiki
from wikitools_py3 import category

site = wiki.Wiki("http://my.wikisite.org/w/api.php")
site.login("username", "password")
# Create object for "Category:Foo"
cat = category.Category(site, "Foo")
# iterate through all the pages in ns 0
for article in cat.getAllMembersGen(namespaces=[0]):
	# edit each page
	article.edit(prependtext="{{template}}\n")
```

See the MediaWiki API documentation at <http://www.mediawiki.org/wiki/API>
for more information about using the MediaWiki API. You can get an example of
what query results will look like by doing the queries in your web browser using
the "jsonfm" format option

Licensed under the GNU General Public License, version 3. A copy of the
license is included with this release.

Authors
-------

* Original source code Alex Z. (User:Mr.Z-man @ en.wikipedia) <mrzmanwiki@gmail.com>
* Some code/assistance (User:Bjweeks @ en.wikipedia)
