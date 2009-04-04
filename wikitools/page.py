# -*- coding: utf-8 -*-
# Copyright 2008, 2009 Mr.Z-man,  bjweeks

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

import datetime, wiki, api, urllib, re
from hashlib import md5

class BadTitle(wiki.WikiError):
	"""Invalid title"""
	
class NoPage(wiki.WikiError):
	"""Non-existent page"""
	
class BadNamespace(wiki.WikiError):
	"""Invalid namespace number"""

class EditError(wiki.WikiError):
	"""Problem with edit request"""

class ProtectError(wiki.WikiError):
	"""Problem with protection request"""

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
			self.pageid = str(pageid)
		else:
			self.pageid = 0
		self.followRedir = followRedir
		self.title = title
		self.wikitext = ''
		self.templates = ''
		self.links = ''
		self.exists = True # If we're not going to check, assume it does
		self.protection = {}
		
		if check:
			self.setPageInfo()
		else: # Guess at some stuff
			self.namespace = False
			if self.title:
				self.title = self.title.replace('_', ' ')
				bits = self.title.split(':', 1)
				if len(bits) == 1 or bits[0] == '':
					self.namespace = 0
				else:
					nsprefix = bits[0].lower() # wp:Foo and caTEGory:Foo are normalized by MediaWiki
					for ns in self.site.namespaces:
						if nsprefix == self.site.namespaces[ns]['*'].lower():
							self.namespace = int(ns)
							self.title = self.site.namespaces[ns]['*']+':'+bits[1]
							break
					else:
						if self.site.NSaliases:
							for ns in self.site.NSaliases:
								if nsprefix == ns.lower():
									self.namespace = int(self.site.NSaliases[ns])
									self.title = self.site.namespaces[self.namespace]['*']+':'+bits[1]
									break
					if not self.namespace:
						self.namespace = 0
			else:
				self.namespace = 0
		if section or sectionnumber:
			self.setSection(section, sectionnumber)
		else:
			self.section = False
		if title and not isinstance(self.title, unicode):
			self.title = unicode(self.title, 'utf-8')
			self.urltitle = urllib.quote(self.title.encode('utf-8')).replace('%20', '_').replace('%2F', '/')	
		elif title:
			self.urltitle = urllib.quote(self.title.encode('utf-8')).replace('%20', '_').replace('%2F', '/')
		else:
			self.urltitle = False

	def setPageInfo(self):
		"""
		Sets basic page info, required for almost everything
		"""
		followRedir = self.followRedir
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
		self.pageid = str(self.pageid)
		
	def setNamespace(self, newns):
		"""
		Change the namespace number of a page object
		and update the title with the new prefix
		"""
		if not newns in self.site.namespaces.keys():
			raise BadNamespace
		if self.namespace == newns:
			return
		if self.title:
			if self.namespace != 0:
				bits = self.title.split(':', 1)
				nsprefix = bits[0].lower()
				for ns in self.site.namespaces:
					if nsprefix == self.site.namespaces[ns]['*'].lower():
						self.title = bits[1]
						break
				else:
					if self.site.NSaliases:
						for ns in self.site.NSaliases:
							if nsprefix == ns.lower():
								self.title = bits[1]
								break
			self.namespace = newns
			if self.namespace:
				self.title = self.site.namespaces[self.namespace]['*']+':'+self.title
			self.urltitle = urllib.quote(self.title.encode('utf-8')).replace('%20', '_').replace('%2F', '/')
		else:
			self.namespace = newns
		
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
			self.setPageInfo()
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
		if not self.title:
			self.setPageInfo()
		return 'subpages' in self.site.namespaces[self.namespace]
		
	def isRedir(self):
		params = {'action':'query',
			'redirects':''
		}
		if not self.exists:
			raise NoPage
		if self.pageid != 0 and self.exists:
			params['pageids'] = self.pageid
		elif self.title:
			params['titles'] = self.title
		else:
			self.setPageInfo()
			if self.pageid != 0 and self.exists:
				params['pageids'] = self.pageid
			else:
				raise NoPage
		req = api.APIRequest(self.site, params)
		res = req.query()
		if 'redirects' in res['query']:
			return True
		else:
			return False
	
	def isTalk(self):
		if not self.title:
			self.setPageInfo()
		return (self.namespace%2==1 and self.namespace >= 0)
		
	def toggleTalk(self, check=True, followRedir=True):
		"""
		Returns a new page object that's either the talk or non-talk
		version of the current page
		"""
		if not self.title:
			self.setPageInfo()
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
		if self.pageid == 0 and not self.title:
			self.setPageInfo()
		if not self.exists:
			raise NoPage
		params = {
			'action': 'query',
			'prop': 'revisions',
			'rvprop': 'content|timestamp',
			'rvlimit': '1'
		}
		if self.pageid:
			params['pageids'] = self.pageid
		else:
			params['titles'] = self.title		
		if expandtemplates:
			params['rvexpandtemplates'] = '1'
		if self.section:
			params['rvsection'] = self.section
		req = api.APIRequest(self.site, params)
		response = req.query(False)
		if self.pageid == 0:
			self.pageid = response['query']['pages'].keys()[0]
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
		if self.pageid == 0 and not self.title:
			self.setPageInfo()
		if not self.exists:
			raise NoPage
		params = {
			'action': 'query',
			'prop': 'links',
			'pllimit': self.site.limit,
		}
		if self.pageid > 0:
			params['pageids'] = self.pageid
		else:
			params['titles'] = self.title	
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
		if self.pageid == 0 and not self.title:
			self.setPageInfo()
		params = {
			'action': 'query',
			'prop': 'info',
			'inprop': 'protection',
		}
		if not self.exists or self.pageid <= 0:
			params['titles'] = self.title
		else:
			params['titles'] = self.title
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
		if self.pageid == 0 and not self.title:
			self.setPageInfo()
		if not self.exists:
			raise NoPage
		params = {
			'action': 'query',
			'prop': 'templates',
			'tllimit': self.site.limit,
		}
		if self.pageid:
			params['pageids'] = self.pageid
		else:
			params['titles'] = self.title	
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
		if self.pageid == 0:
			self.pageid = json['query']['pages'].keys()[0]
		if stuff in json['query']['pages'][self.pageid]:
			for template in json['query']['pages'][self.pageid][stuff]:
				list.append(template['title'])
		return list
	
	def edit(self, *args, **kwargs):
		"""
		Edit the page
		Arguments are a subset of the API's action=edit arguments, valid arguments
		are defined in the validargs set
		To skip MD5 check, set "skipmd5" keyword argument to True
		http://www.mediawiki.org/wiki/API:Edit_-_Create%26Edit_pages#Parameters
		"""
		validargs = set(['text', 'summary', 'minor', 'notminor', 'bot', 'basetimestamp', 'starttimestamp',
			'recreate', 'createonly', 'nocreate', 'watch', 'unwatch', 'prependtext', 'appendtext'])			
		# For backwards compatibility
		if 'newtext' in kwargs:
			kwargs['text'] = kwargs['newtext']
			del kwargs['newtext']
		if 'basetime' in kwargs:
			kwargs['basetimestamp'] = kwargs['basetime']
			del kwargs['basetime']		
		if len(args) and 'text' not in kwargs:
			kwargs['text'] = args[0]
		skipmd5 = False
		if 'skipmd5' in kwargs and kwargs['skipmd5']:
			skipmd5 = True
		invalid = set(kwargs.keys()).difference(validargs)		
		if invalid:
			for arg in invalid:
				del kwargs[arg]
		if not self.title:
			self.setPageInfo()			
		if not 'text' in kwargs and not 'prependtext' in kwargs and not 'appendtext' in kwargs:
			raise EditError("No text specified")
		if 'prependtext' in kwargs and 'section' in kwargs:
			raise EditError("Bad param combination")
		if 'createonly' in kwargs and 'nocreate' in kwargs:
			raise EditError("Bad param combination")
		token = self.getToken('edit')
		if 'text' in kwargs:
			hashtext = kwargs['text']
		elif 'prependtext' in kwargs and 'appendtext' in kwargs:
			hashtext = kwargs['prependtext']+kwargs['appendtext']
		elif 'prependtext' in kwargs:
			hashtext = kwargs['prependtext']
		else:
			hashtext = kwargs['appendtext']
		params = {
			'action': 'edit',
			'title':self.title,
			'token':token,
		}
		if not skipmd5:
			params['md5'] = md5(hashtext).hexdigest()
		params.update(kwargs)
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
		if not self.title and self.pageid == 0:
			self.setPageInfo()
		if not self.exists:
			raise NoPage
		token = self.getToken('move')
		params = {
			'action': 'move',
			'to':mvto,
			'token':token,
		}
		if self.pageid:
			params['fromid'] = self.pageid
		else:
			params['from'] = self.title
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
		req = api.APIRequest(self.site, params, write=True)
		result = req.query()
		if 'move' in result:
			self.title = result['move']['to']
			if not isinstance(self.title, unicode):
				self.title = unicode(self.title, 'utf-8')
				self.urltitle = urllib.quote(self.title.encode('utf-8')).replace('%20', '_').replace('%2F', '/')	
			else:
				self.urltitle = urllib.quote(self.title.encode('utf-8')).replace('%20', '_').replace('%2F', '/')
		return result

	def protect(self, restrictions={}, expirations={}, reason=False, cascade=False):
		"""
		Protect a page
		restrictions and expirations are dictionaries of
		protection level/expiry settings, eg, {'edit':'sysop'} and
		{'move':'3 days'}. expirations can also be a string to set 
		all levels to the same expiration
		"""
		if not self.title:
			self.setPageInfo()
		if not restrictions:
			raise ProtectError("No protection levels given")
		if len(expirations) > len(restrictions):
			raise ProtectError("More expirations than restrictions given")
		token = self.getToken('protect')
		protections = ''
		expiry = ''
		if isinstance(expirations, str):
			expiry = expirations
		for type in restrictions:
			if protections:
				protections+="|"
			protections+= type+"="+restrictions[type]
			if isinstance(expirations, dict) and type in expirations:
				if expiry:
					expiry+="|"
				expiry+=expirations[type]
			elif isinstance(expirations, dict):
				if expiry:
					expiry+="|"
				expiry+='indefinite'
		params = {'action':'protect',
			'title':self.title,
			'token':token,
			'protections':protections
		}
		if expiry:
			params['expiry'] = expiry
		if reason:
			params['reason'] = reason
		if cascade:
			params['cascade'] = ''
		req = api.APIRequest(self.site, params, write=True)
		result = req.query()
		if 'protect' in result:
			self.protection = {}
		return result
	
	def delete(self, reason=False, watch=False, unwatch=False):
		"""
		Delete the page
		Most params are self-explanatory
		"""
		if not self.title and self.pageid == 0:
			self.setPageInfo()
		if not self.exists:
			raise NoPage
		token = self.getToken('delete')
		params = {
			'action': 'delete',
			'token':token,
		}
		if self.pageid:
			params['pageid'] = self.pageid
		else:
			params['title'] = self.title
		if reason:
			params['reason'] = reason.encode('utf-8')
		if watch:
			params['watch'] = '1'
		if unwatch:
			params['unwatch'] = '1'
		req = api.APIRequest(self.site, params, write=True)
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
			
		if self.pageid == 0 and not self.title:
			self.setPageInfo()
		if not self.exists and type != 'edit':
			raise NoPage
		params = {
			'action':'query',
			'prop':'info',
			'intoken':type,
		}
		if self.exists and self.pageid:
			params['pageids'] = self.pageid
		else:
			params['titles'] = self.title
		req = api.APIRequest(self.site, params)
		response = req.query()
		if self.pageid == 0:
			self.pageid = response['query']['pages'].keys()[0]
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
