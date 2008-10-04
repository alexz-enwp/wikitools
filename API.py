# -*- coding: utf-8  -*-
import urllib2, simplejson, re, time, cookielib
from urllib import urlencode

class APIError(Exception):
	"""Base class for errors"""

class APIRequest:
	def __init__(self, wiki, data):
		self.sleep = 5
		self.data = data
		self.data['format'] = "json"
		if not data.has_key('maxlag'):
			self.data['maxlag'] = "5"
		self.encodeddata = urlencode(self.data)
		self.headers = {
			"Content-type": "application/x-www-form-urlencoded",
			"User-agent": "MediaWiki-API-python/0.1",
			"Content-length": len(self.encodeddata)
		}
		self.wiki = wiki
		self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(wiki.cookies))
		self.request = urllib2.Request(wiki.apibase, self.encodeddata, self.headers)
	
	# Actually do the query here and return usable stuff
	def query(self, querycontinue=True):
		data = False
		while not data:
			rawdata = self.__getRaw()
			data = self.__parseJSON(rawdata)
		#Certain errors should probably be handled here...
		if data.has_key('error'):
			raise APIError(data['error']['code'], data['error']['info'])
		if data.has_key('query-continue') and querycontinue:
			data = self.__longQuery(data)
		return data
	
	# For queries that require multiple requests
	#FIXME - queries can have multiple continue things....
	# http://en.wikipedia.org/w/api.php?action=query&prop=langlinks|links&titles=Main%20Page&redirects&format=jsonfm
	def __longQuery(self, initialdata):
		totaldata = [initialdata]
		key1 = initialdata['query-continue'].keys()[0]
		key2 = initialdata['query-continue'][key1].keys()[0]
		querycont = initialdata['query-continue'][key1][key2]
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
					
					
	#Gets the actual data from the server
	def __getRaw(self):
		data = False
		while not data:
			try:
				data = self.opener.open(self.request)
			except:
				if self.sleep == 60:
					print("Aborting")
					return
				else:
					print("Server error, trying request again in "+str(self.sleep)+" seconds")
					time.sleep(self.sleep+0.5)
					self.sleep+=5
		self.response = data.info()
		return data
	# Convert the JSON to usable stuff
	def __parseJSON(self, data):
		maxlag = True
		while  maxlag:
			try:
				maxlag = False
				response = simplejson.loads(data.read())
				if response.has_key('error'):
					error = response['error']['code']
					if error == "maxlag":
						lagtime = re.search("(\d+) seconds", response['error']['info']).group(1)
						print("Server lag, sleeping for "+lagtime+" seconds")
						maxlag = True
						time.sleep(int(lagtime)+0.5)
			except: # Something's wrong with the data....
				return False
		return response

	# Function to change the default useragent
	def setUserAgent(self, useragent):
		self.headers['User-agent'] = useragent