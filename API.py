# -*- coding: utf-8 -*-
import urllib2, simplejson, re, time, cookielib
from urllib import urlencode

try:
	import gzip
	import StringIO
except:
	gzip = False

class APIError(Exception):
	"""Base class for errors"""
	
class ServerError(APIError):
	"""Base class for errors"""

class APIRequest:
	"""
	A request to the site's API
	wiki - A Wiki object
	data - API parameters in the form of a dict
	maxlag is set by default to 5 but can be changed
	format is always set to json
	"""
	def __init__(self, wiki, data):
		self.sleep = 5
		self.data = data
		self.data['format'] = "json"
		if not data.has_key('maxlag'):
			self.data['maxlag'] = wiki.maxlag
		self.encodeddata = urlencode(self.data)
		self.headers = {
			"Content-type": "application/x-www-form-urlencoded",
			"User-agent": "MediaWiki-API-python/0.1",
			"Content-length": len(self.encodeddata)
		}
		if gzip:
			self.headers['Accept-Encoding'] = 'gzip'
		self.wiki = wiki
		self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(wiki.cookies))
		self.request = urllib2.Request(wiki.apibase, self.encodeddata, self.headers)

	def query(self, querycontinue=True):
		"""
		Actually do the query here and return usable stuff
		"""
		
		data = False
		while not data:
			rawdata = self.__getRaw()
			if rawdata:
				data = self.__parseJSON(rawdata)
			else:
				raise ServerError
		#Certain errors should probably be handled here...
		if data.has_key('error'):
			raise APIError(data['error']['code'], data['error']['info'])
		if data.has_key('query-continue') and querycontinue:
			data = self.__longQuery(data)
		return data
	
	def __longQuery(self, initialdata):
		"""
		For queries that require multiple requests
		FIXME - queries can have multiple continue things....
		http://en.wikipedia.org/w/api.php?action=query&prop=langlinks|links&titles=Main%20Page&redirects&format=jsonfm
		"""
	
		totaldata = [initialdata]
		key1 = initialdata['query-continue'].keys()[0]
		key2 = initialdata['query-continue'][key1].keys()[0]
		if isinstance(initialdata['query-continue'][key1][key2], int):
			querycont = initialdata['query-continue'][key1][key2]
		else:
			querycont = initialdata['query-continue'][key1][key2].encode('utf-8')
		while querycont:
			self.data[key2] = querycont
			self.encodeddata = urlencode(self.data)
			self.headers['Content-length'] = len(self.encodeddata)
			self.request = urllib2.Request(self.wiki.apibase, self.encodeddata, self.headers)
			newdata = self.query(False)
			totaldata.append(newdata)
			if newdata.has_key('query-continue') and newdata['query-continue'].has_key(key1):
				querycont = newdata['query-continue'][key1][key2]
			else:
				querycont = False
		return totaldata
					
	def __getRaw(self):
		data = False
		while not data:
			try:
				data = self.opener.open(self.request)
				self.response = data.info()
				if gzip:
					encoding = self.response.get('Content-encoding')
					if encoding in ('gzip', 'x-gzip'):
						data = gzip.GzipFile('', 'rb', 9, StringIO.StringIO(data.read()))
			except:
				if self.sleep == 60:
					print("Aborting")
					return false
				else:
					print("Server error, trying request again in "+str(self.sleep)+" seconds")
					time.sleep(self.sleep+0.5)
					self.sleep+=5
		return data

	def __parseJSON(self, data):
		maxlag = True
		while maxlag:
			try:
				maxlag = False
				content = simplejson.loads(data.read())
				if content.has_key('error'):
					error = content['error']['code']
					if error == "maxlag":
						lagtime = re.search("(\d+) seconds", content['error']['info']).group(1)
						print("Server lag, sleeping for "+lagtime+" seconds")
						maxlag = True
						time.sleep(int(lagtime)+0.5)
			except: # Something's wrong with the data....
				return False
		return content

	def setUserAgent(self, useragent):
		"""
		Function to set a different user-agent
		"""
		self.headers['User-agent'] = useragent