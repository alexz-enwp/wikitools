# -*- coding: utf-8 -*-
import urllib2, simplejson, re, time, cookielib
from urllib import quote_plus, _is_unicode

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
		self.encodeddata = urlencode(self.data, 1)
		self.headers = {
			"Content-type": "application/x-www-form-urlencoded",
			"User-agent": wiki.useragent,
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
			self.encodeddata = urlencode(self.data, 1)
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
						return False
			except: # Something's wrong with the data....
				return False
		return content
		
def urlencode(query,doseq=0):
    """
	Hack of urllib's urlencode function, which can handle
	Unicode, but for unknown reasons, chooses not to.
    """

    if hasattr(query,"items"):
        # mapping objects
        query = query.items()
    else:
        # it's a bother at times that strings and string-like objects are
        # sequences...
        try:
            # non-sequence items should not work with len()
            # non-empty strings will fail this
            if len(query) and not isinstance(query[0], tuple):
                raise TypeError
            # zero-length sequences of all types will get here and succeed,
            # but that's a minor nit - since the original implementation
            # allowed empty dicts that type of behavior probably should be
            # preserved for consistency
        except TypeError:
            ty,va,tb = sys.exc_info()
            raise TypeError, "not a valid non-string sequence or mapping object", tb

    l = []
    if not doseq:
        # preserve old behavior
        for k, v in query:
            k = quote_plus(str(k))
            v = quote_plus(str(v))
            l.append(k + '=' + v)
    else:
        for k, v in query:
            k = quote_plus(str(k))
            if isinstance(v, str):
                v = quote_plus(v)
                l.append(k + '=' + v)
            elif _is_unicode(v):
                # is there a reasonable way to convert to ASCII?
                # encode generates a string, but "replace" or "ignore"
                # lose information and "strict" can raise UnicodeError
                v = quote_plus(v.encode("utf8","replace"))
                l.append(k + '=' + v)
            else:
                try:
                    # is this a sufficient test for sequence-ness?
                    x = len(v)
                except TypeError:
                    # not a sequence
                    v = quote_plus(str(v))
                    l.append(k + '=' + v)
                else:
                    # loop over the sequence
                    for elt in v:
                        l.append(k + '=' + quote_plus(str(elt)))
    return '&'.join(l)
	