# -*- coding: utf-8 -*-
import datetime, wiki, api, urllib, re
from hashlib import md5

class BadTitle(wiki.WikiError):
	"""Invalid title"""
	
class NoPage(wiki.WikiError):
	"""Non-existent page"""

class EditError(wiki.WikiError):
	"""Problem with edit request"""

class Page:
	""" A page on the wiki
	wiki - A wiki object
	title - The page title, as a string
	check - Checks for existence, normalizes title, required for most things
	followRedir - follow redirects (check must be true)
	section - the section name
	sectionnumber - the section number
	pageid - pageid, can be in place of title
	""" 
	def __init__(self, site, title=False, check=True, followRedir=True, section=False, sectionnumber=False, pageid=False):
		if not title and not pageid:
			raise wiki.WikiError("No title or pageid given")
		self.site = site
		if pageid:
			self.pageid = int(pageid)
		else:
			self.pageid = 0
		self.title = title
		self.wikitext = ''
		self.templates = ''
		self.links = ''
		self.exists = True # If we're not going to check, assume it does
		self.protection = {}
		
		if check:
			self.setPageInfo(followRedir)
		else: # Guess at some stuff
			self.namespace = False
			for ns in site.namespaces:
				if title.startswith(self.site.namespaces[ns]['*']+':'):
					self.namespace = int(ns)
					break
			if not self.namespace:
				self.namespace = 0
		if section or sectionnumber:
			self.setSection(section, sectionnumber)
		else:
			self.section = False
		if not isinstance(self.title, unicode):
			self.title = unicode(self.title, 'utf-8')
			self.urltitle = urllib.quote(self.title.encode('utf-8')).replace('%20', '_').replace('%2F', '/')	
		else:
			self.urltitle = urllib.quote(self.title.encode('utf-8')).replace('%20', '_').replace('%2F', '/')

	def setPageInfo(self, followRedir=True):
		"""
		Sets basic page info, required for almost everything
		"""
		
		params = {'action':'query'}
		if self.pageid:
			params['pageids'] = self.pageid
		else:
			params['titles'] = self.title
		if followRedir:
			params['redirects'] = ''
		req = api.APIRequest(self.site, params)
		response = req.query()
		self.pageid = response['query']['pages'].keys()[0]
		self.title = response['query']['pages'][self.pageid]['title'].encode('utf-8')
		if 'missing' in response['query']['pages'][self.pageid]:
			self.exists = False
		if 'invalid' in response['query']['pages'][self.pageid]:
			raise BadTitle(self.title)
		self.namespace = int(response['query']['pages'][self.pageid]['ns'])
		self.pageid = int(self.pageid)
		
	def setSection(self, section=False, number=False):
		"""
		Set a section for the page
		section - the section name
		"""
		if not section and not number:
			self.section = False
		elif number:
			try:
				self.section = str(int(number))
			except ValueError:
				raise WikiError("Section number must be an int")
		else:
			self.section = self.__getSection(section)
	
	def __getSection(self, section):
		if not self.title:
			self.setPageInfo(False)
		params = {
			'action': 'parse',
			'text': '{{:'+self.title+'}}__TOC__',
			'title':self.title,
			'prop':'sections'
		}
		number = False
		req = api.APIRequest(self.site, params)
		response = req.query()
		counter = 0
		for item in response['parse']['sections']:
			counter+=1
			if section == item['line']:
				number = counter
				break
		return number
		
	def canHaveSubpages(self):
		try:
			self.namespace
		except:
			self.setPageInfo(False)
		return self.site.namespaces[self.namespace].has_key('subpages')
		
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
		if self.namespace == False or not self.title:
			self.setPageInfo(False)
		ns = self.namespace
		if ns < 0:
			return False
		nsname = self.site.namespaces[ns]['*']
		if self.isTalk():
			newns = self.site.namespaces[ns-1]['*']
		else:
			newns = self.site.namespaces[ns+1]['*']
		try:
			pagename = self.title.split(nsname+':',1)[1]
		except:
			pagename = self.title
		if newns != '':
			newname = newns+':'+pagename
		else:
			newname = pagename
		return Page(self.site, newname, check, followRedir)						
			
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
		if self.section:
			params['rvsection'] = self.section
		req = api.APIRequest(self.site, params)
		response = req.query(False)
		self.wikitext = response['query']['pages'][self.pageid]['revisions'][0]['*'].encode('utf-8')
		self.lastedittime = response['query']['pages'][self.pageid]['revisions'][0]['timestamp']
		return self.wikitext
	
	def getLinks(self, force=False):
		"""
		Gets a list of all the internal links on the page
		force - load the list even if we already loaded it before
		"""
		if self.links and not force:
			return self.links
		if self.pageid == 0:
			self.setPageInfo()
		if not self.exists:
			raise NoPage
		params = {
			'action': 'query',
			'prop': 'links',
			'pageids': self.pageid,
			'pllimit': self.site.limit,
		}
		req = api.APIRequest(self.site, params)
		response = req.query()
		self.links = []
		if isinstance(response, list): #There shouldn't be more than 5000 links on a page...
			for page in response:
				self.links.extend(self.__extractToList(page, 'links'))
		else:
			self.links = self.__extractToList(response, 'links')
		return self.links
		
	def getProtection(self, force=False):
		if self.protection and not force:
			return self.protection
		if not self.exists:
			raise NoPage
		params = {
			'action': 'query',
			'prop': 'info',
			'pageids': self.pageid,
			'inprop': 'protection',
		}
		req = api.APIRequest(self.site, params)
		response = req.query()
		for pr in response['query'].values()[0].values()[0]['protection']:
			if pr['level']: 
				if pr['expiry'] == 'infinity':
					expiry = 'infinity'
				else:
					expiry = datetime.datetime.strptime(pr['expiry'],'%Y-%m-%dT%H:%M:%SZ')
				self.protection[pr['type']] = {
					'expiry': expiry, 
					'level': pr['level']
					}
		return self.protection
	
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
			'tllimit': self.site.limit,
		}
		req = api.APIRequest(self.site, params)
		response = req.query()
		self.templates = []
		if isinstance(response, list): #There shouldn't be more than 5000 templates on a page...
			for page in response:
				self.templates.extend(self.__extractToList(page, 'templates'))
		else:
			self.templates = self.__extractToList(response, 'templates')
		return self.templates
	
	def __extractToList(self, json, stuff):
		list = []
		if json['query']['pages'][self.pageid].has_key(stuff):
			for template in json['query']['pages'][self.pageid][stuff]:
				list.append(template['title'])
		return list
	
	def edit(self, newtext=False, prependtext=False, appendtext=False, summary=False, section=False, minor=False, bot=False, basetime=False, recreate=False, createonly=False, nocreate=False, watch=False, unwatch=False):
		"""
		Edit the page
		Most params are self-explanatory
		basetime - set this to the time you loaded the pagetext to avoid
		overwriting other people's edits in edit conflicts
		"""
	
		if newtext == False and not prependtext and not appendtext:
			raise EditError("No text specified")
		if prependtext and section:
			raise EditError("Bad param combination")
		if createonly and nocreate:
			raise EditError("Bad param combination")
		token = self.getToken('edit')
		if newtext != False:
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
			'md5':md5(hashtext).hexdigest(),
		}
		if newtext != False:
			params['text'] = newtext
		if prependtext:
			params['prependtext'] = prependtext
		if appendtext:
			params['appendtext'] = appendtext
		if summary:
			params['summary'] = summary
		if section:
			params['section'] = section
		if self.section:
			params['section'] = self.section
		if minor:
			params['minor'] = '1'
		else:
			params['notminor'] = '1'
		if bot:
			params['bot'] = '1'
		if basetime:
			params['basetimestamp'] = basetime
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
		req = api.APIRequest(self.site, params, write=True)
		result = req.query()
		if 'edit' in result and result['edit']['result'] == 'Success':
			self.wikitext = ''
			self.links = []
			self.templates = ''
		return result
		
	def move(self, mvto, reason=False, movetalk=False, noredirect=False, watch=False, unwatch=False):
		"""
		Move the page
		Most params are self-explanatory
		mvto (move to) is the only required param
		must have "suppressredirect" right to use noredirect
		"""
		if not self.exists:
			raise NoPage
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
		req = api.APIRequest(self.site, params, write=False)
		result = req.query()
		if 'move' in result:
			self.title = result['move']['to']
			if not isinstance(self.title, unicode):
				self.title = unicode(self.title, 'utf-8')
				self.urltitle = urllib.quote(self.title.encode('utf-8')).replace('%20', '_').replace('%2F', '/')	
			else:
				self.urltitle = urllib.quote(self.title.encode('utf-8')).replace('%20', '_').replace('%2F', '/')
		return result

	def delete(self, reason=False, watch=False, unwatch=False):
		"""
		Delete the page
		Most params are self-explanatory
		"""
		if not self.exists:
			raise NoPage
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
		req = api.APIRequest(self.site, params, write=False)
		result = req.query()
		if 'delete' in result:
			self.pageid = 0
			self.exists = False
			self.wikitext = ''
			self.templates = ''
			self.links = ''
			self.protection = {}
			self.section = False			
		return result
	
	def getToken(self, type):
		""" 
		Get a token for everything except blocks and rollbacks
		type (String) - edit, delete, protect, move, block, unblock, email
		Currently all the tokens are interchangeable, but this may change in the future
		"""
			
		if self.pageid == 0 or not self.title:
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
		req = api.APIRequest(self.site, params)
		response = req.query()
		token = response['query']['pages'][self.pageid][type+'token']
		return token
	
	def __eq__(self, other):
		if not isinstance(other, Page):
			return False
		if self.title:			
			if self.title == other.title and self.site == other.wiki:
				return True
		else:
			if self.pageid == other.pageid and self.site == other.wiki:
				return True
		return False
	def __ne__(self, other):
		if not isinstance(other, Page):
			return True
		if self.title:
			if self.title == other.title and self.site == other.wiki:
				return False
		else:
			if self.pageid == other.pageid and self.site == other.wiki:
				return False
		return True