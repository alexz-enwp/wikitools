# `wikitools3` — Package for working with MediaWiki wikis

## Requirements

  * Python 3. Not compatible with Python 2. If you are using Python 2, use the original [`wikitools`](https://pypi.org/project/wikitools/) instead.
  * `wikitools3` uses [`poetry`](https://python-poetry.org/) for dependency management. If you are installing via `pip`, you should not need to install `poetry` separately.
  * To upload files or import XML, you need Chris AtLee's [`poster3`](http://pypi.python.org/pypi/poster3) package. This should be automatically installed by `pip` and/or `poetry` when you install `wikitools3`.
  * The MediaWiki instance you are working with should be version 1.13 or later and have the API enabled.

## Installation

  * Run `pip install wikitools3`. This is the preferred installation method.
  * Alternately, download the source repository and run `poetry install` within the `wikitools3` directory or copy the `wikitools3/wikitools3` subdirectory directly into the top-level directory of your project.

## Available modules

  * `api.py` - Contains the `APIRequest` class, for doing queries directly, see API examples below
  * `wiki.py` - Contains the `Wiki` class, used for logging in to the site, storing cookies, and storing basic site information
  * `page.py` - Contains the `Page` class for dealing with individual pages on the wiki. Can be used to get page info and text, as well as edit and other actions if enabled on the wiki
  * `category.py` - `Category` is a subclass of `Page` with extra functions for working with categories
  * `wikifile.py` - `File` is a subclass of `Page` with extra functions for working with files - note that there may be some issues with shared repositories, as the pages for files on shared repos technically don't exist on the local wiki.
  * `user.py` - Contains the `User` class for getting information about and blocking/unblocking users
  * `pagelist.py` - Contains several functions for getting a list of `Page` objects from lists of titles, pageids, or API query results

## Further documentation

  * See also: the legacy `wikitools` documentation at [Google Code](https://code.google.com/p/python-wikitools/wiki/Documentation).

## Current limitations

  * Can only do what the API can do. On a site without the edit-API enabled (disabled by default prior to MediaWiki 1.14), you cannot edit/delete/protect pages, only retrieve information about them.
  * May have issues with some non-ASCII characters. Most of these bugs should be resolved, though full UTF-8 support is still a little flaky.
  * Usage on restricted-access (logged-out users can't read) wikis is mostly untested.
  * `wikitools3` has not been tested beyond the needs of `wikiteam`. If functionality from `wikitools` for Python 2 works for you, but the same functionality does not work for you in `wikitools3`, please submit a bug report at [github.com/elsiehupp/wikitools3/issues](https://github.com/elsiehupp/wikitools3/issues).

## Quick start

To make a simple query:

```python
#!/usr/bin/env python3

from wikitools3 import wiki
from wikitools3 import api

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

If the API module you need requires a token, you first do something like:
```python
params = { 'action':'query', 'meta':'tokens' }
token = api.APIRequest(site, params).query()['query']['tokens']['csrftoken']
# define the params for the query
params = { 'action':'thank', 'rev':diff, 'token':token }
```

For most normal usage, you may not have to do API queries yourself and can just use the various classes. For example, to add a template to the top of all the pages in namespace `0` in a category:

```python
#!/usr/bin/env python3

from wikitools3 import wiki
from wikitools3 import category

site = wiki.Wiki("http://my.wikisite.org/w/api.php") 
site.login("username", "password")
# Create object for "Category:Foo"
cat = category.Category(site, "Foo")
# iterate through all the pages in ns 0
for article in cat.getAllMembersGen(namespaces=[0]):
	# edit each page
	article.edit(prependtext="{{template}}\n")
``` 

See the [MediaWiki API documentation](https://www.mediawiki.org/wiki/API:Main_page) for more information about using the MediaWiki API. You can get an example of what query results will look like by doing the queries in your web browser using the `jsonfm` format option.

Licensed under the [GNU General Public License, version 3](https://www.gnu.org/licenses/gpl-3.0.en.html). A copy of the license is included with this release.

Authors
-------

* Original source code Alex Z. (User:Mr.Z-man @ en.wikipedia) <mrzmanwiki@gmail.com>
* Some code/assistance (User:Bjweeks @ en.wikipedia)
* Python 3 migration Elsie Hupp ([github.com/elsiehupp](https://github.com/elsiehupp))
