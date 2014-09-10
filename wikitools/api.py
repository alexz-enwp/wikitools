# -*- coding: utf-8 -*-
# Copyright 2008-2013 Alex Zaddach (mrzmanwiki@gmail.com)

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

# This module is documented at http://code.google.com/p/python-wikitools/wiki/api

import requests
from requests.auth import HTTPDigestAuth

import re
import time
import sys
import wiki
import StringIO
from urllib import quote_plus, _is_unicode

try:
	import json
except:
	import simplejson as json

class APIError(Exception):
	"""Base class for errors"""

class APIDisabled(APIError):
	"""API not enabled"""
	
class APIRequest:
	"""A request to the site's API"""
	def __init__(self, wiki, data, write=False, multipart=True):
		"""	
		wiki - A Wiki object
		data - API parameters in the form of a dict
		write - set to True if doing a write query, so it won't try again on error
        multipart - obsolete and unused option, you can use file objet to send
        multipart requests.

		maxlag is set by default to 5 but can be changed
		format is always overriden to force 'json'
		"""
		self.sleep = 5
		self.data = data.copy()
		self.data['format'] = "json"
		self.iswrite = write
		if wiki.assertval is not None and self.iswrite:
			self.data['assert'] =  wiki.assertval
		if not 'maxlag' in self.data and not wiki.maxlag < 0:
			self.data['maxlag'] = wiki.maxlag
		self.headers = {}
		self.headers["User-agent"] = wiki.useragent
		self.headers['Accept-Encoding'] = 'gzip'
		self.wiki = wiki
		self.response = False
		self.authman = None if wiki.auth is None else HTTPDigest(wiki.auth) 
		
	def changeParam(self, param, value):
		"""Change or add a parameter after making the request object
		
		Simply changing self.data won't work as it needs to update other things.

		value can either be a normal string value, or a file-like object,
		which will be uploaded.
		
		"""
		if param == 'format':
			raise APIError('You can not change the result format')
		self.data[param] = value
	
	def query(self, querycontinue=True):
		"""Actually do the query here and return usable stuff
		
		querycontinue - look for query-continue in the results and continue querying
		until there is no more data to retrieve
		
		"""
		data = False
		while not data:
			rawdata = StringIO.StringIO(self.__getRaw().content)
			data = self.__parseJSON(rawdata)
			if not data and type(data) is APIListResult:
				break
		if 'error' in data:
			if self.iswrite and data['error']['code'] == 'blocked':
				raise wiki.UserBlocked(data['error']['info'])
			raise APIError(data['error']['code'], data['error']['info'])
		if 'query-continue' in data and querycontinue:
			data = self.__longQuery(data)
		return data
	
	def __longQuery(self, initialdata):
		"""For queries that require multiple requests"""
		self._continues = set()
		self._generator = ''
		total = initialdata
		res = initialdata
		params = self.data
		numkeys = len(res['query-continue'].keys())
		while numkeys > 0:
			key1 = ''
			key2 = ''
			possiblecontinues = res['query-continue'].keys()
			if len(possiblecontinues) == 1:
				key1 = possiblecontinues[0]
				keylist = res['query-continue'][key1].keys()
				if len(keylist) == 1:
					key2 = keylist[0]
				else:
					for key in keylist:
						if len(key) < 11:
							key2 = key
							break
					else:
						key2 = keylist[0]
			else:
				for posskey in possiblecontinues:
					keylist = res['query-continue'][posskey].keys()
					for key in keylist:
						if len(key) < 11:
							key1 = posskey
							key2 = key
							break
					if key1:
						break
				else:
					key1 = possiblecontinues[0]
					key2 = res['query-continue'][key1].keys()[0]
			if isinstance(res['query-continue'][key1][key2], int):
				cont = res['query-continue'][key1][key2]
			else:
				cont = res['query-continue'][key1][key2].encode('utf-8')
			if len(key2) >= 11 and key2.startswith('g'):
				self._generator = key2
				for ckey in self._continues:
					params.pop(ckey, None)		
			else:
				self._continues.add(key2)
			params[key2] = cont
			req = APIRequest(self.wiki, params)
			res = req.query(False)
			for type in possiblecontinues:
				total = resultCombine(type, total, res)
			if 'query-continue' in res:
				numkeys = len(res['query-continue'].keys())
			else:
				numkeys = 0
		return total

	def __getRaw(self):
		data = False
		while not data:
			try:
				if self.sleep >= self.wiki.maxwaittime or self.iswrite:
					catcherror = None
				else:
					catcherror = Exception
				data = self.response = requests.get(self.wiki.apibase, params=self.data,
                                    headers=self.headers, auth=self.authman)
			except catcherror, exc:
				errname = sys.exc_info()[0].__name__
				errinfo = exc
				print("%s: %s trying request again in %d seconds" % (errname, errinfo, self.sleep))
				time.sleep(self.sleep+0.5)
				self.sleep+=5
		return data

	def __parseJSON(self, data):
		maxlag = True
		while maxlag:
			try:
				maxlag = False
				parsed = json.loads(data.read())
				content = None
				if isinstance(parsed, dict):
					content = APIResult(parsed)
					content.response = self.response.headers.items()
				elif isinstance(parsed, list):
					content = APIListResult(parsed)
					content.response = self.response.headers.items()
				else:
					content = parsed
				if 'error' in content:
					error = content['error']['code']
					if error == "maxlag":
						lagtime = int(re.search("(\d+) seconds", content['error']['info']).group(1))
						if lagtime > self.wiki.maxwaittime:
							lagtime = self.wiki.maxwaittime
						print("Server lag, sleeping for "+str(lagtime)+" seconds")
						maxlag = True
						time.sleep(int(lagtime)+0.5)
						return False
			except: # Something's wrong with the data...
				data.seek(0)
				if "MediaWiki API is not enabled for this site. Add the following line to your LocalSettings.php<pre><b>$wgEnableAPI=true;</b></pre>" in data.read():
					raise APIDisabled("The API is not enabled on this site")
				print "Invalid JSON, trying request again"
				# FIXME: Would be nice if this didn't just go forever if its never going to work
				return False
		return content
		
class APIResult(dict):
	response = []
	
class APIListResult(list):
	response = []
		
def resultCombine(type, old, new):
	"""Experimental-ish result-combiner thing
	
	If the result isn't something from action=query,
	this will just explode, but that shouldn't happen hopefully?
	
	"""
	ret = old
	if type in new['query']: # Basic list, easy
		ret['query'][type].extend(new['query'][type])
	else: # Else its some sort of prop=thing and/or a generator query
		for key in new['query']['pages'].keys(): # Go through each page
			if not key in old['query']['pages']: # if it only exists in the new one
				ret['query']['pages'][key] = new['query']['pages'][key] # add it to the list
			else:
				if not type in new['query']['pages'][key]:
					continue
				elif type in new['query']['pages'][key] and not type in ret['query']['pages'][key]: # if only the new one does, just add it to the return
					ret['query']['pages'][key][type] = new['query']['pages'][key][type]
					continue					
				else: # Need to check for possible duplicates for some, this is faster than just iterating over new and checking for dups in ret
					retset = set([tuple(entry.items()) for entry in ret['query']['pages'][key][type]])
					newset = set([tuple(entry.items()) for entry in new['query']['pages'][key][type]])
					retset.update(newset)
					ret['query']['pages'][key][type] = [dict(entry) for entry in retset]
	return ret
		
