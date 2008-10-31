# -*- coding: utf-8 -*-
__all__ = ["API", "Page", "Category"]
import cookielib, API, urllib, re

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
		self.useragent = "MediaWiki-API-python/0.2"
		self.limit = '5000' #  FIXME:There needs to be a way to set this based on userrights
		self.setSiteinfo()
	
	def setSiteinfo(self):
		params = {'action':'query',
			'meta':'siteinfo',
			'siprop':'general|namespaces'
		}
		self.setMaxlag('60')
		req = API.APIRequest(self, params)
		info = req.query()
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
		if not sidata.has_key('writeapi'):
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
		self.setMaxlag('120')
		req = API.APIRequest(self, data)
		info = req.query()
		self.setMaxlag()
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
	
	def setMaxlag(self, maxlag = 5):
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
	def __init__(self, wiki, title, check=True, followRedir=True):
		self.wiki = wiki
		self.title = title
		self.wikitext = ''
		self.templates = ''
		self.pageid = 0 # The API will set a negative pageid for bad titles
		self.exists = True # If we're not going to check, assume it does
		if check:
			self.setPageInfo(followRedir)
		else: # Guess at some stuff
			self.namespace = False
			for ns in wiki.namespaces:
				if title.startswith(wiki.namespaces[ns]['*']+':'):
					self.namespace = int(ns)
					break
			if not self.namespace:
				self.namespace = 0
		self.urltitle = urllib.urlencode({self.title.encode('utf-8'):''}).split('=')[0].replace('+', '_').replace('%2F', '/')		

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
		self.namespace = int(response['query']['pages'][self.pageid].get('ns'))
	
	def canHaveSubpages(self):
		try:
			self.namespace
		except:
			self.setPageInfo(False)
		return self.wiki.namespaces[self.namespace].has_key('subpages')
		
	def isTalk(self):
		try:
			self.namespace
		except:
			self.setPageInfo(False)
		return (self.namespace%2==1 and self.namespace != -1)
		
	def toggleTalk(self, check=True, followRedir=True):
		"""
		Returns a new page object that's either the talk or non-talk
		version of the current page
		"""
		try:
			self.namespace
		except:
			self.setPageInfo(False)
		ns = self.namespace
		if ns < 0:
			return False
		nsname = self.wiki.namespaces[ns]['*']
		if self.isTalk():
			newns = self.wiki.namespaces[ns-1]['*']
		else:
			newns = self.wiki.namespaces[ns+1]['*']
		try:
			pagename = self.title.split(nsname+':',1)[1]
		except:
			pagename = self.title
		if newns != '':
			newname = newns+':'+pagename
		else:
			newname = pagename
		return Page(self.wiki, newname, check, followRedir)						
			
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
			'tllimit': self.wiki.limit,
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
			raise EditError("No text specified")
		if prependtext and section:
			raise EditError("Bad param combination")
		if createonly and nocreate:
			raise EditError("Bad param combination")
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
		
	def move(self, mvto, reason=False, movetalk=False, noredirect=False, watch=False, unwatch=False):
		"""
		Move the page
		Most params are self-explanatory
		mvto (move to) is the only required param
		must have "suppressredirect" right to use noredirect
		"""
		token = self.getToken('move')
		params = {
			'action': 'move',
			'fromid':self.pageid,
			'mvto':mvto,
			'token':token,
		}
		if reason:
			params['reason'] = reason.encode('utf-8')
		if movetalk:
			params['movetalk'] = '1'
		if noredirect:
			params['noredirect'] = '1'
		if watch:
			params['watch'] = '1'
		if unwatch:
			params['unwatch'] = '1'
		req = API.APIRequest(self.wiki, params)
		result = req.query()
		return result

	def delete(self, reason=False, watch=False, unwatch=False):
		"""
		Delete the page
		Most params are self-explanatory
		"""
		token = self.getToken('delete')
		params = {
			'action': 'delete',
			'pageid':self.pageid,
			'token':token,
		}
		if reason:
			params['reason'] = reason.encode('utf-8')
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
		if not self.exists and type != 'edit':
			raise NoPage
		params = {
			'action':'query',
			'prop':'info',
			'intoken':type,
		}
		if self.exists:
			params['pageids'] = self.pageid
		else:
			params['titles'] = self.title
		req = API.APIRequest(self.wiki, params)
		response = req.query()
		token = response['query']['pages'][self.pageid][type+'token']
		return token

class Category(Page):
	"""
	A category on the wiki
	title should be the full title, including "Category:"
	"""
	def __init__(self, wiki, title, check=True, followRedir = False):
		self.wiki = wiki
		self.title = title
		self.wikitext = ''
		self.templates = ''
		self.members = []
		self.pageid = 0 # The API will set a negative pageid for bad titles
		self.exists = True # If we're not going to check, assume it does
		if check:
			self.setPageInfo(followRedir)
			
	def getAllMembers(self, titleonly=False, reload=False):
		"""
		Gets a list of pages in the category
		titleonly - set to True to only create a list of strings,
		else it will be a list of Page objects
		reload - reload the list even if it was generated before
		"""
		if self.members and not reload:
			return self.members
		else:
			self.members = []
			for page in self.__getMembersInternal(titleonly):
				self.members.append(page)
			return self.members
	
	def getAllMembersGen(self, titleonly=False, reload=False):
		"""
		Generator function for pages in the category
		titleonly - set to True to return strings,
		else it will return Page objects
		reload - reload the list even if it was generated before
		"""
		if self.members and not reload:
			for page in self.members:
				yield page
		else:
			self.members = []
			for page in self.__getMembersInternal(titleonly):
				self.members.append(page)
				yield page
	
	def __getMembersInternal(self, titleonly):
		params = {'action':'query',
			'list':'categorymembers',
			'cmtitle':self.title,
			'cmlimit':self.wiki.limit,
			'cmprop':'title'
		}
		while True:
			req = API.APIRequest(self.wiki, params)
			data = req.query(False)
			for page in data['query']['categorymembers']:
				if titleonly:
					yield page['title']
				else:
					yield Page(self.wiki, page['title'], check=False, followRedir=False)
			try:
				params['cmcontinue'] = data['query-continue']['categorymembers']['cmcontinue']
			except:
				break 
		
			
			

		