import api, page, category

def listFromQuery(site, queryresult):
	"""
	Generate a list of pages from an API query result
	queryresult is the list of pages from a list or generator query
	e.g. - for a list=categorymembers query, use result['query']['categorymembers']
	for a generator query, use result['query']['pages']
	"""
	ret = []
	if isinstance(queryresult, list):
		for item in queryresult:
			pageid = False
			if 'pageid' in item:
				pageid = item['pageid']
			if item['ns'] == 14:
				item = category.Category(site, title=item['title'], check=False, followRedir=False, pageid=pageid)
			else:
				item = page.Page(site, title=item['title'], check=False, followRedir=False, pageid=pageid)
			ret.append(item)
	else:
		for key in queryresult.keys():
			item = queryresult[key]
			pageid = False
			if 'pageid' in item:
				pageid = item['pageid']
			if item['ns'] == 14:
				item = category.Category(site, title=item['title'], check=False, followRedir=False, pageid=pageid)
			else:
				item = page.Page(site, title=item['title'], check=False, followRedir=False, pageid=pageid)
			ret.append(item)
	return ret

def listFromTitles(site, titles, check=True, followRedir=True):
	"""
	Create a list of page objects from a list of titles
	check and followRedir have the same meaning as in page.Page
	"""
	ret = []
	if not check:
		for title in titles:
			title = page.Page(site, title=title, check=False)
			ret.append(title)
	else:
		tlist = unicode('', 'utf8')
		first = True
		for title in titles:
			if not first:
				tlist+='|'
			first = False
			tlist+=title
		params = {'action':'query',
			'titles':tlist,
		}
		if followRedir:
			params['redirects'] = ''
		req = api.APIRequest(site, params)
		response = req.query()
		for key in response['query']['pages'].keys():
			res = response['query']['pages'][key]
			item = makePage(key, res, site)
			ret.append(item)
	return ret

def listFromPageids(site, pageids, check=True, followRedir=True):			
	"""
	Create a list of page objects from a list of pageids
	check and followRedir have the same meaning as in page.Page
	"""
	ret = []
	if not check:
		for id in pageids:
			title = page.Page(site, pageid=id, check=False)
			ret.append(title)
	else:
		idlist = ''
		first = True
		for id in pageids:
			if not first:
				idlist+='|'
			first = False
			idlist+=id
		params = {'action':'query',
			'pageids':idlist,
		}
		if followRedir:
			params['redirects'] = ''
		req = api.APIRequest(site, params)
		response = req.query()
		for key in response['query']['pages'].keys():
			res = response['query']['pages'][key]
			item = makePage(key, res, site)
			ret.append(item)
	return ret
	
def makePage(key, result, site):
	if result['ns'] == 14:
		item = category.Category(site, title=result['title'], check=False, followRedir=False, pageid=result['pageid'])
	else:
		item = page.Page(site, title=result['title'], check=False, followRedir=False, pageid=result['pageid'])
	item.pageid = key
	item.title = result['title'].encode('utf-8')
	if 'missing' in result:
		item.exists = False
	if 'invalid' in result:
		item = False
	if 'ns' in result:
		item.namespace = int(result['ns'])
	return item