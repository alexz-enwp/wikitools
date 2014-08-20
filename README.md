﻿wikitools -- Package for working with MediaWiki wikis
-----------------------------------------------------------

Requirements:

  * Python 2.5+. (not compatible with Python 3; not tested on older versions)
  * Bob Ippolito's simplejson module, if using Python < 2.6
    <http://pypi.python.org/pypi/simplejson>
  * To upload files or import XML, you need Chris AtLee's poster package
    <http://pypi.python.org/pypi/poster>  
  * The wiki this is used for should be running at least MediaWiki
    version 1.13 and have the API enabled.

Installation:

  * Run "python setup.py install" or copy the wikitools directory
    to an appropriate Python module directory.
  * An exe installer for Windows is also available (should be run as an 
    administrator to avoid errors)
  * An RPM for Linux is also available.

Available modules:

  * api.py - Contains the APIRequest class, for doing queries directly,
	see API examples below
  * wiki.py - Contains the Wiki class, used for logging in to the site,
    storing cookies, and storing basic site information
  * page.py -  Contains the Page class for dealing with individual pages
    on the wiki. Can be used to get page info and text, as well as edit and
	other actions if enabled on the wiki
  * category.py - Category is a subclass of Page with extra functions for
    working with categories
  * wikifile.py - File is a subclass of Page with extra functions for
    working with files - note that there may be some issues with shared 
	repositories, as the pages for files on shared repos technically don't
	exist on the local wiki.
  * user.py - Contains the User class for getting information about and 
    blocking/unblocking users
  * pagelist.py - Contains several functions for getting a list of Page
    objects from lists of titles, pageids, or API query results

Further documentation:
  * https://code.google.com/p/python-wikitools/wiki/Documentation

Current limitations:

  * Can only do what the API can do. On a site without the edit-API enabled
    (disabled by default prior to MediaWiki 1.14), you cannot edit/delete/
	protect pages, only retrieve information about them. 
  * May have issues with some non-ASCII characters. Most of these bugs
    should be resolved, though full UTF-8 support is still a little flaky
  * Usage on restricted-access (logged-out users can't read) wikis is
    mostly untested
  
API examples:
To do a simple query:

from wikitools import wiki
from wikitools import api
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

The result will look something like:
{u'query':
	{u'pages':
		{u'15580374':
			{u'ns': 0, u'pageid': 15580374, u'title': u'Main Page'}
		}
	}
}

For most normal usage, you may not have to do API queries yourself and can just
use the various classes. For example, to add a template to the top of all the 
pages in namespace 0 in a category:

from wikitools import wiki
from wikitools import category
site = wiki.Wiki("http://my.wikisite.org/w/api.php") 
site.login("username", "password")
# Create object for "Category:Foo"
cat = category.Category(site, "Foo")
# iterate through all the pages in ns 0
for article in cat.getAllMembersGen(namespaces=[0]):
	# edit each page
	article.edit(prependtext="{{template}}\n")
 

See the MediaWiki API documentation at <http://www.mediawiki.org/wiki/API>
for more information about using the MediaWiki API. You can get an example of
what query results will look like by doing the queries in your web browser using
the "jsonfm" format option
 
Licensed under the GNU General Public License, version 3. A copy of the
license is included with this release.

Author/maintainer:
Alex Z. (User:Mr.Z-man @ en.wikipedia) <mrzmanwiki@gmail.com>
Some code/assistance from:
(User:Bjweeks @ en.wikipedia)
