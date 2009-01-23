# -*- coding: utf-8 -*-
import cookielib, api, urllib, re

class WikiError(Exception):
	"""Base class for errors"""

class BadTitle(WikiError):
	"""Invalid title"""
	
class NoPage(WikiError):
	"""Non-existent page"""

class EditError(WikiError):
	"""Problem with edit request"""

class Wiki:
	"""
	A Wiki site
	url - A URL to the site's API, defaults to en.wikipedia
	"""	
	def __init__(self, url="http://en.wikipedia.org/w/api.php"):
		self.apibase = url
		self.cookies = cookielib.CookieJar()
		self.username = ''
		self.maxlag = 5
		self.useragent = "MediaWiki-API-python/0.1"
		self.limit = 500
		self.setSiteinfo()
	
	def setSiteinfo(self):
		params = {'action':'query',
			'meta':'siteinfo',
			'siprop':'general|namespaces'
		}
		if self.maxlag == 5:
			self.setMaxlag(120)
		req = api.APIRequest(self, params)
		info = req.query()
		if self.maxlag == 5:
			self.setMaxlag()
		sidata = info['query']['general']
		self.siteinfo = {}
		for item in sidata:
			self.siteinfo[item] = sidata[item]
		nsdata = info['query']['namespaces']
		self.namespaces = {}
		for ns in nsdata:
			nsinfo = nsdata[ns]
			self.namespaces[nsinfo['id']] = nsinfo
		if not 'writeapi' in sidata:
			print "WARNING: Write-API not enabled, you will not be able to edit"
		version = re.search("\d\.(\d\d)", self.siteinfo['generator'])
		if not int(version.group(1)) >= 13: # Will this even work on 13?
			print "WARNING: Some features may not work on older versions of MediaWiki"
	
	def login(self, username, password = False, remember = True):
		"""
		Login to the site
		remember - currently unused
		"""
		
		if not password:
			from getpass import getpass
			password = getpass()
		data = {
			"action" : "login",
			"lgname" : username,
			"lgpassword" : password
		}
		if self.maxlag == 5:
			self.setMaxlag(120)
		req = api.APIRequest(self, data)
		info = req.query()
		if info['login']['result'] == "Success":
			self.username = username
		else:
			try:
				print info['login']['result']
			except:
				print info['error']['code']
				print info['error']['info']
		
		params = {
			'action': 'query',
			'meta': 'userinfo',
			'uiprop': 'rights'
		}
		req = api.APIRequest(self, params)
		info = req.query()
		if self.maxlag == 5:
			self.setMaxlag()
		user_rights = info['query']['userinfo']['rights']
		if 'apihighlimits' in user_rights:
			self.limit = 5000
	
	def logout(self):
		params = { 'action': 'logout' }
		req = api.APIRequest(self, params, write=True)
		# action=logout returns absolutely nothing, which json.loads() treats as False
		# causing APIRequest.query() to get stuck in a loop
		req.opener.open(req.request)
		self.cookies = cookielib.CookieJar()
		self.username = ''
		self.maxlag = 5
		self.useragent = "Python-wikitools/0.1"
		self.limit = 500
		
	def isLoggedIn(self, username = False):
		"""
		Verify that we are a logged in user
		username - specify a username to check against
		"""
		
		data = {
			"action" : "query",
			"meta" : "userinfo",
		}
		req = api.APIRequest(self, data)
		info = req.query()
		if info['query']['userinfo']['id'] == 0:
			return False
		elif username and info['query']['userinfo']['name'] != username:
			return False
		else:
			return True
	
	def setMaxlag(self, maxlag = 5):
		"""
		Set the maxlag for all requests to something other than 5
		"""
		try:
			int(maxlag)
		except:
			raise WikiError("maxlag must be an integer")
		self.maxlag = int(maxlag)
		
	def setUserAgent(self, useragent):
		"""
		Function to set a different user-agent
		"""
		self.useragent['User-agent'] = str(useragent)

	def __eq__(self, other):
		if not isinstance(other, Wiki):
			return False
		if self.apibase == other.apibase:
			return True
		return False
	def __ne__(self, other):
		if not isinstance(other, Wiki):
			return True
		if self.apibase == other.apibase:
			return False
		return True
		