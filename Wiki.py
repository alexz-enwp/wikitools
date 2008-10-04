# -*- coding: utf-8  -*-
import cookielib, API

class WikiError(Exception):
	"""Base class for errors"""

class BadTitle(WikiError):
	"""Invalid title"""
	
class NoPage(WikiError):
	"""Non-existent page"""

class Wiki:
	def __init__(self, url="http://en.wikipedia.org/w/api.php"):
		self.apibase = url
		self.cookies = cookielib.CookieJar()
		self.username = ''
	
	# Login to the site, Remember currently does nothing, CAPTCHA handling would be nice
	def login(self, username, password = False, remember = True):
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
		data = {
			"action" : "query",
			"meta" : "userinfo",
		}
		req = API.APIRequest(self, data)
		info = req.query()
		if info['query']['userinfo']['id'] == 0:
			return false
		elif username and info['query']['userinfo']['name'] != username:
			return false
		else:
			return true

""" A page on the wiki
wiki - A wiki object
title - The page title, as a string
check - Checks for existence, normalizes title
followRedir - follow redirects (check must be true)
"""			
class Page:
	def __init__(self, wiki, title, check=True, followRedir = True):
		self.limit = '5000' #  FIXME:There needs to be a way to set this based on userrights
		self.wiki = wiki
		self.title = title.encode('utf-8')
		self.wikitext = ''
		self.templates = ''
		self.pageid = 0 # The API will set a negative pageid for bad titles
		self.exists = True # If we're not going to check, assume it does
		if check:
			self.setPageInfo(followRedir)
			
	def setPageInfo(self, followRedir=True):
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
		if response['query']['pages'][self.pageid].has_key('ns'):
			self.namespace = response['query']['pages'][self.pageid]['ns']
			
			
	def getWikiText(self, expandtemplates=False, force=False):
		if self.wikitext and not force:
			return self.wikitext
		if self.pageid == 0:
			self.setPageInfo(followRedir=False)
		if not self.exists:
			return self.wikitext
		params = {
			'action': 'query',
			'prop': 'revisions',
			'rvprop': 'content',
			'pageids': self.pageid,
			'rvlimit': '1'
		}
		if expandtemplates:
			params['rvexpandtemplates'] = '1'
		req = API.APIRequest(self.wiki, params)
		response = req.query()
		self.wikitext = response['query']['pages'][self.pageid]['revisions'][0]['*'].encode('utf-8')
		return self.wikitext
	
	def templates(self, force=False):
		if not self.exists:
			raise NoPage
		if self.templates and not force:
			return self.templates
		if self.pageid == 0:
			self.setPageInfo()
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
		for template in json['query']['pages'][self.pageid]['templates']:
			list.append(template['title'].encode('utf-8'))
		return list
		
		