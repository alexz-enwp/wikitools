# -*- coding: utf-8 -*-
import cookielib, API

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
		self.maxlag = '5'
		self.useragent = "MediaWiki-API-python/0.1"
	
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
		req = API.APIRequest(self, data)
		info = req.query()
		if info['login']['result'] == "Success":
			self.username = username
		else:
			try:
				print info['login']['result']
			except:
				print info['error']['code']
				print info['error']['info']
	
	def isLoggedIn(self, username = False):
		"""
		Verify that we are a logged in user
		username - specify a username to check against
		"""
		
		data = {
			"action" : "query",
			"meta" : "userinfo",
		}
		req = API.APIRequest(self, data)
		info = req.query()
		if info['query']['userinfo']['id'] == 0:
			return False
		elif username and info['query']['userinfo']['name'] != username:
			return False
		else:
			return True
	
	def setMaxlag(self, maxlag):
		"""
		Set the maxlag for all requests to something other than 5
		"""
		try:
			int(maxlag)
		except:
			raise WikiError("maxlag must be an integer")
		self.maxlag = str(maxlag)
		
	def setUserAgent(self, useragent):
		"""
		Function to set a different user-agent
		"""
		self.useragent['User-agent'] = str(useragent)
		
class Page:
	""" A page on the wiki
	wiki - A wiki object
	title - The page title, as a string
	check - Checks for existence, normalizes title
	followRedir - follow redirects (check must be true)
	"""	
	def __init__(self, wiki, title, check=True, followRedir = True):
		self.limit = '5000' #  FIXME:There needs to be a way to set this based on userrights
		self.wiki = wiki
		self.title = title
		self.wikitext = ''
		self.templates = ''
		self.pageid = 0 # The API will set a negative pageid for bad titles
		self.exists = True # If we're not going to check, assume it does
		if check:
			self.setPageInfo(followRedir)

	def setPageInfo(self, followRedir=True):
		"""
		Sets basic page info, required for almost everything
		"""
		
		params = {
			'action': 'query',
			'titles': self.title,
			'indexpageids':'1'
		}
		if followRedir:
			params['redirects'] = '1'
		req = API.APIRequest(self.wiki, params)
		response = req.query()
		if response['query'].has_key('normalized'):
			self.title = response['query']['normalized'][0]['to'].encode('utf-8')
		if followRedir and response['query'].has_key('redirects'):
			self.title = response['query']['redirects'][0]['to'].encode('utf-8')
		self.pageid = response['query']['pageids'][0]
		if not self.title:
			self.title = response['query']['pages'][self.pageid]['title'].encode('utf-8')
		if response['query']['pages'][self.pageid].has_key('missing'):
			self.exists = False
		if response['query']['pages'][self.pageid].has_key('invalid'):
			raise BadTitle(self.title)
		self.namespace = response['query']['pages'][self.pageid].get('ns')
			
	def getWikiText(self, expandtemplates=False, force=False):
		"""
		Gets the Wikitext of the page
		expandtemplates - expand the templates to wikitext instead of transclusions
		force - load the text even if we already loaded it before
		"""
	
		if self.wikitext and not force:
			return self.wikitext
		if self.pageid == 0:
			self.setPageInfo(followRedir=False)
		if not self.exists:
			return self.wikitext
		params = {
			'action': 'query',
			'prop': 'revisions',
			'rvprop': 'content|timestamp',
			'pageids': self.pageid,
			'rvlimit': '1'
		}
		if expandtemplates:
			params['rvexpandtemplates'] = '1'
		req = API.APIRequest(self.wiki, params)
		response = req.query(False)
		self.wikitext = unicode(response['query']['pages'][self.pageid]['revisions'][0]['*'])
		self.lastedittime = response['query']['pages'][self.pageid]['revisions'][0]['timestamp']
		return self.wikitext

	def getTemplates(self, force=False):
		"""
		Gets all list of all the templates on the page
		force - load the list even if we already loaded it before
		"""
	
		if self.templates and not force:
			return self.templates
		if self.pageid == 0:
			self.setPageInfo()
		if not self.exists:
			raise NoPage
		params = {
			'action': 'query',
			'prop': 'templates',
			'pageids': self.pageid,
			'tllimit': self.limit,
		}
		req = API.APIRequest(self.wiki, params)
		response = req.query()
		self.templates = []
		if isinstance(response, list): #There shouldn't be more than 5000 templates on a page...
			for page in response:
				self.templates.extend(self.__extractTemplates(page))
		else:
			self.templates = self.__extractTemplates(response)
		return self.templates
	
	def __extractTemplates(self, json):
		list = []
		if json['query']['pages'][self.pageid].has_key('templates'):
			for template in json['query']['pages'][self.pageid]['templates']:
				list.append(template['title'].encode('utf-8'))
		return list
	
	def edit(self, newtext=False, prependtext=False, appendtext=False, summary=False, section=False, minor=False, bot=False, basetime=False, recreate=False, createonly=False, nocreate=False, watch=False, unwatch=False):
		"""
		Edit the page
		Most params are self-explanatory
		basetime - set this to the time you loaded the pagetext to avoid
		overwriting other people's edits in edit conflicts
		"""
	
		if not newtext and not prependtext and not appendtext:
			raise EditError
		if prependtext and section:
			raise EditError
		if createonly and nocreate:
			raise EditError
		token = self.getToken('edit')
		from hashlib import md5
		if newtext:
			hashtext = newtext
		elif prependtext and appendtext:
			hashtext = prependtext+appendtext
		elif prependtext:
			hashtext = prependtext
		else:
			hashtext = appendtext
		params = {
			'action': 'edit',
			'title':self.title,
			'token':token,
			'md5':md5(hashtext.encode('utf-8')).hexdigest(),
		}
		if newtext:
			params['text'] = newtext.encode('utf-8')
		if prependtext:
			params['prependtext'] = prependtext.encode('utf-8')
		if appendtext:
			params['appendtext'] = appendtext.encode('utf-8')
		if summary:
			params['summary'] = summary.encode('utf-8')
		if section:
			params['section'] = section.encode('utf-8')
		if minor:
			params['minor'] = '1'
		else:
			params['notminor'] = '1'
		if bot:
			params['bot'] = '1'
		if basetime:
			params['basetimestamp'] = basetime.encode('utf-8')
		if recreate:
			params['recreate'] = '1'
		if createonly:
			params['createonly'] = '1'
		if nocreate:
			params['nocreate'] = '1'
		if watch:
			params['watch'] = '1'
		if unwatch:
			params['unwatch'] = '1'
		req = API.APIRequest(self.wiki, params)
		result = req.query()
		return result		
	
	def getToken(self, type):
		""" 
		Get a token for everything except blocks and rollbacks
		type (String) - edit, delete, protect, move, block, unblock, email
		Currently all the tokens are interchangeable, but this may change in the future
		"""
			
		if self.pageid == 0:
			self.setPageInfo()
		if not self.exists:
			raise NoPage
		params = {
			'action':'query',
			'pageids':self.pageid,
			'prop':'info',
			'intoken':type,
		}
		req = API.APIRequest(self.wiki, params)
		response = req.query()
		token = response['query']['pages'][self.pageid][type+'token']
		return token
		
		
		