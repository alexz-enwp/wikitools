# -*- coding: utf-8 -*-
# Copyright 2008-2016 Alex Zaddach (mrzmanwiki@gmail.com)

# This file is part of wikitools.
# wikitools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# wikitools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with wikitools.  If not, see <http://www.gnu.org/licenses/>.

import wikitools_py3

def listFromQuery(site, queryresult):
	"""Generate a list of Pages from an API query result

	queryresult is the list (or dict) of pages from a list or generator query
	e.g. - for a list=categorymembers query, use result['query']['categorymembers']
	for prop=linkshere, use result['query']['pages'][pageid]['linkshere']
	for a generator query, use result['query']['pages']
	"""
	ret = []
	if isinstance(queryresult, dict):
		queryresult = queryresult.values()
	return [makePage(item, site, False) for item in queryresult]

def listFromTextList(site, sequence, datatype, check=True, followRedir=False):
	"""Create a list of Page objects from a list of titles, pageids, or (namespace, title) pairs
	sequence must be something similar to a list
	datatype must be one of 'titles', 'pageids', 'dbkeys'
	check and followRedir have the same meaning as in page.Page
	"""
	if datatype not in ['titles', 'pageids', 'dbkeys']:
		raise wiki.WikiError("listFromTextList datatype must be one of titles, pageids, dbkeys")
	if datatype == 'dbkeys':
		sequence = sequence.copy()
		sequence = [site.namespaces[int(i[0])]['*']+':'+i[1] if int(i[0]) else i[1] for i in sequence]
		datatype = 'titles'
	if not check:
		if datatype == 'pageids':
			sequence = [int(i) for i in sequence]
		opt = datatype[:-1]
		return [wikitools_py3.page.Page(site, check=False, followRedir=followRedir, **{opt:item}) for item in sequence]
	start = 0
	end = 0
	ret = []
	if datatype == 'pageids':
		sequence = [str(i) for i in sequence]
	while end < len(sequence):
		lim = int(site.limit/10)
		end = start+lim
		tlist = '|'.join(sequence[start:end])
		params = {'action':'query',
			datatype:tlist,
		}
		if followRedir:
			params['redirects'] = ''
		req = wikitools_py3.api.APIRequest(site, params)
		res = req.query(False)
		for key in res['query']['pages']:
			obj = res['query']['pages'][key]
			item = makePage(obj, site, followRedir)
			ret.append(item)
		start = end
	return ret

def listFromDbKeys(site, keys, check=True, followRedir=False):
	"""Create a list of Page objects from a list of (ns, title) pairs
	such as might be retrieved from a database query where the ns and title
	are stored separately
	Strictly speaking the sequences can contain more data than the ns and title,
	the only requirement is that the ns and title are the first 2 items

	check and followRedir have the same meaning as in page.Page
	"""
	listFromTextList(site, keys, 'dbkeys', check, followRedir)

def listFromTitles(site, titles, check=True, followRedir=False):
	"""Create a list of page objects from a list of titles

	check and followRedir have the same meaning as in page.Page

	"""
	listFromTextList(site, titles, 'titles', check, followRedir)

def listFromPageids(site, pageids, check=True, followRedir=False):
	"""Create a list of page objects from a list of pageids

	check and followRedir have the same meaning as in page.Page

	"""
	listFromTextList(site, pageids, 'pageids', check, followRedir)

def makePage(result, site, followRedir):
	"""Make a Page object from an API query result
	result - dict from action=query that contains, at minimum, the page title
	site - the Wiki object for the page
	followRedit - the value for the followRedir option
	"""
	if 'invalid' in result:
		return None
	title = None
	ns = None
	if 'title' in result:
		title = result['title']
		ns = result['ns']
	pageid = 0
	if 'pageid' in result and result['pageid'] > 0:
		pageid = result['pageid']
	if ns == site.NS_CATEGORY:
		item = wikitools_py3.category.Category(site, title=title, check=False, followRedir=followRedir, pageid=pageid)
	elif ns == site.NS_FILE:
		item = wikitools_py3.wikifile.File(site, title=title, check=False, followRedir=followRedir, pageid=pageid)
	else:
		item = wikitools_py3.page.Page(site, title=title, check=False, followRedir=followRedir, pageid=pageid)
	if 'missing' in result:
		item.exists = False
	elif pageid:
		item.exists = True
	return item
