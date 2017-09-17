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

# This module contains internal functions used by multiple wikitools
# modules. There isn't much reason to use them on their own. 
# Breaking changes to these functions may be made without warning.

from . import exceptions
from . import api
import warnings

def getList(obj, querytype, listtype, prefix, direction='older', limit='all', lowlimit=False, **kwargs):
	"""Do an API query to get a list of stuff
	obj - Some sort of wikitools object that contains a Wiki object
	listtype - API list= value
	prefix - prefix for API query params
	direction/limit - standard arguments for list generation
	kwargs - Any other keyword arguments, which should correspond
		directly with API arguments
	"""
	maximum = limit
	if limit == 'all':
		maximum = float("inf")
	if limit == 'all' or limit > obj.site.limit:
		limit = obj.site.limit
	if lowlimit and limit > obj.site.limit/10:
			limit = int(obj.site.limit/10)
	if 'continue' not in obj.site.features:
		w = "Warning: only %d log entries will be returned" % (limit)
		warnings.warn(w)
	entries = []
	qc = None
	while True:
		res, qc = __getListInternal(obj, querytype, listtype, prefix, direction, limit, qc, kwargs)
		entries = entries+res
		if len(entries) == maximum or qc is None:
			break
		if maximum - len(entries) < obj.site.limit:
			limit = maximum - len(entries)
	return entries

def getListGen(obj, querytype, listtype, prefix, direction='older', limit='all', **kwargs):
	if 'continue' not in obj.site.features:
		raise exceptions.UnsupportedError("MediaWiki 1.21+ is required for this function")
	maximum = limit
	count = 0
	qc = None
	while True:
		res, qc = __getListInternal(obj, querytype, listtype, prefix, direction, 1, qc, kwargs)
		yield res[0]
		count += 1
		if count == maximum or qc is None:
			break

def __getListInternal(obj, querytype, listtype, prefix, direction, limit, querycontinue, kwargs):
	if direction != 'newer' and direction != 'older':
		raise exceptions.WikiError("direction must be 'newer' or 'older'")
	params = {'action':'query',
		querytype:listtype,
		prefix+'dir':direction,
		prefix+'limit':limit,	
		'continue':'',
	}
	for key, value in kwargs.items():
		if value is not None:
			params[key] = value
	if querycontinue:
		for key, value in querycontinue.items():
			params[key] = value
	req = api.APIRequest(obj.site, params)
	response = req.query(False)
	result = None
	if querytype == 'list':
		result = response['query'][listtype]
	elif querytype == 'prop':
		key = list(response['query']['pages'].keys())[0]
		if listtype not in response['query']['pages'][key]:
			result = [None]
		else:
			result = response['query']['pages'][key][listtype]
	qc = None
	if 'continue' in response:
		qc = response['continue']
	return (result, qc)

