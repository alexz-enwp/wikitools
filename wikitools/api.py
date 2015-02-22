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

from . import exceptions
import re
import time
import sys
import base64
import warnings
import copy
import json
import io
from collections import deque
from requests.auth import HTTPDigestAuth

logging = False
querylog = deque()
resultlog = deque()

# Do this, otherwise it won't show maxlag/HTTP error warnings more than once
warnings.filterwarnings("always", category=UserWarning, module='wikitools.api')

class APIRequest:
	"""A request to the site's API"""
	def __init__(self, site, data, write=False, multipart=False):
		"""
		site - A Wiki object
		data - API parameters in the form of a dict
		write - set to True if doing a write query, so it won't try again on error
		multipart - Deprecated, unused

		maxlag is set by default to 5 but can be changed via the setMaxlag method
		of the Wiki class
		format is always set to json
		"""
		self.sleep = 5
		self.data = data.copy()
		self.file = {}
		for param in self.data:
			if isinstance(self.data[param], io.IOBase):
				self.file[param] = self.data[param]
		for param in self.file:
			del self.data[param]
		self.data['format'] = "json"
		self.iswrite = write
		if site.assertval is not None and self.iswrite:
			self.data['assert'] =  site.assertval
		if not 'maxlag' in self.data and not site.maxlag < 0:
			self.data['maxlag'] = site.maxlag
		self.headers = {}
		self.headers["User-agent"] = site.useragent
		self.site = site
		self.response = None

	def setMultipart(self, multipart=True):
		"""Unused, for backward-compatibility only"""
		pass

	def changeParam(self, param, value):
		"""
		Change or add a parameter after making the request object
		If value is None, deletes the parameter
		"""
		if param == 'format':
			raise exceptions.APIError('You can not change the result format')
		if value is None:
			if param in self.data:
				del self.data[param]
			if param in self.file:
				del self.file[param]
			return
		if isinstance(value, io.IOBase):
			self.file[param] = value
			if param in self.data:
				del self.data[param]
		else:
			self.data[param] = value
			if param in self.file:
				del self.file[param]

	def query(self, querycontinue=True):
		"""Actually do the query here and return usable stuff

		querycontinue - look for query-continue in the results and continue querying
		until there is no more data to retrieve (DEPRECATED: use queryGen as a more
		reliable and efficient alternative)

		"""
		if querycontinue and 'action' in self.data and self.data['action'] == 'query':
			warnings.warn("""The querycontinue option is deprecated and will be removed
in a future release, use the new queryGen function instead
for queries requring multiple requests""", FutureWarning)
		data = False
		while not data:
			rawdata = self.__getRaw().text
			data = self.__parseJSON(rawdata)
			if not data and type(data) is APIListResult:
				break
		if 'error' in data:
			if self.iswrite and data['error']['code'] == 'blocked':
				raise exceptions.UserBlocked(data['error']['info'])
			raise exceptions.APIQueryError(data['error']['code'], data['error']['info'])
		if 'query-continue' in data and querycontinue:
			data = self.__longQuery(data)
		if logging:
			resultlog.appendleft(data)
		return data

	def queryGen(self):
		"""Unlike the old query-continue method that tried to stitch results
		together, which could work poorly for complex result sets and could
		use a lot of memory, this yield each set returned by the API and lets
		the user process the data.
		Loosely based on the recommended implementation on mediawiki.org

		"""
		if 'continue' not in self.site.features:
			raise exceptions.UnsupportedError("MediaWiki 1.21+ is required for this function")
		reqcopy = self.data.copy()
		self.changeParam('continue', '')
		while True:
			data = False
			while not data:
				rawdata = self.__getRaw().text
				data = self.__parseJSON(rawdata)
				if not data and type(data) is APIListResult:
					break
			if 'error' in data:
				if self.iswrite and data['error']['code'] == 'blocked':
					raise exceptions.UserBlocked(data['error']['info'])
				raise exceptions.APIQueryError(data['error']['code'], data['error']['info'])
			if logging:
				resultlog.appendleft(data)
			yield data
			if 'continue' not in data:
				break
			else:
				self.data = reqcopy.copy()
				for param in data['continue']:
					self.changeParam(param, data['continue'][param])

	def __longQuery(self, initialdata):
		"""For queries that require multiple requests
		(DEPRECATED)
		"""
		self._continues = set()
		self._generator = ''
		total = initialdata
		res = initialdata
		params = self.data
		numkeys = len(list(res['query-continue'].keys()))
		while numkeys > 0:
			key1 = ''
			key2 = ''
			possiblecontinues = list(res['query-continue'].keys())
			if len(possiblecontinues) == 1:
				key1 = possiblecontinues[0]
				keylist = list(res['query-continue'][key1].keys())
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
					keylist = list(res['query-continue'][posskey].keys())
					for key in keylist:
						if len(key) < 11:
							key1 = posskey
							key2 = key
							break
					if key1:
						break
				else:
					key1 = possiblecontinues[0]
					key2 = list(res['query-continue'][key1].keys())[0]
			if isinstance(res['query-continue'][key1][key2], int):
				cont = res['query-continue'][key1][key2]
			else:
				cont = res['query-continue'][key1][key2]
			if len(key2) >= 11 and key2.startswith('g'):
				self._generator = key2
				for ckey in self._continues:
					params.pop(ckey, None)
			else:
				self._continues.add(key2)
			params[key2] = cont
			req = APIRequest(self.site, params)
			res = req.query(False)
			for type in possiblecontinues:
				total = resultCombine(type, total, res)
			if 'query-continue' in res:
				numkeys = len(list(res['query-continue'].keys()))
			else:
				numkeys = 0
		return total

	def __getRaw(self):
		data = False
		while not data:
			try:
				catcherror = True
				if self.sleep >= self.site.maxwaittime or self.iswrite:
					catcherror = False
				if logging:
					querylog.appendleft(self.data.copy())
				data = self.response = self.site.session.post(self.site.apibase, data=self.data,
					headers=self.headers, auth=self.site.auth, files=self.file)
				self.response.raise_for_status()
			except Exception as exc:
				if not catcherror:
					raise exc
				errname = sys.exc_info()[0].__name__
				warnstring = "%s: %s trying request again in %d seconds" % (errname, exc, self.sleep)
				warnings.warn(warnstring, UserWarning)
				time.sleep(self.sleep+0.5)
				self.sleep+=5
		return data


	def __parseJSON(self, data):
		maxlag = True
		try:
			parsed = json.loads(data)
			content = None
			if isinstance(parsed, dict):
				content = APIResult(parsed)
				content.response = list(self.response.headers.items())
			elif isinstance(parsed, list):
				content = APIListResult(parsed)
				content.response = list(self.response.headers.items())
			else:
				content = parsed
			if 'error' in content:
				error = content['error']['code']
				if error == "maxlag":
					lagtime = int(re.search("(\d+) seconds", content['error']['info']).group(1))
					if lagtime > self.site.maxwaittime:
						lagtime = self.site.maxwaittime
					warnstring = "Server lag, sleeping for "+str(lagtime)+" seconds"
					warnings.warn(warnstring, UserWarning)
					time.sleep(int(lagtime)+0.5)
					return False
		except: # Something's wrong with the data...
			if "MediaWiki API is not enabled for this site." in data:
				raise exceptions.APIDisabled("The API is not enabled on this site")
			if self.sleep >= self.site.maxwaittime or self.iswrite:
				raise exceptions.APIFailure("Invalid JSON received. API is broken, or this isn't a MediaWiki API")
			warnstring = "Invalid JSON, trying request again in %d seconds" % (self.sleep)
			warnings.warn(warnstring, UserWarning)
			time.sleep(self.sleep+0.5)
			self.sleep+=5
			return False
		self.sleep = 5
		return content

class APIResult(dict):
	response = []

class APIListResult(list):
	response = []

def resultCombine(type, old, new):
	"""Experimental-ish result-combiner thing

	If the result isn't something from action=query,
	this will just explode, but that shouldn't happen hopefully?
	(DEPRECATED)
	"""
	warnings.warn("resultCombine is deprecated, will not be mantained, and may be removed in the future",
		DeprecationWarning)
	ret = old
	if type in new['query']: # Basic list, easy
		ret['query'][type].extend(new['query'][type])
	else: # Else its some sort of prop=thing and/or a generator query
		for key in list(new['query']['pages'].keys()): # Go through each page
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

