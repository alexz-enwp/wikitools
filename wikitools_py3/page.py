# -*- coding: utf-8 -*-
# Copyright 2008-2016 Alex Zaddach (mrzmanwiki@gmail.com), bjweeks

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

from . import exceptions
from . import api
from . import internalfunctions
import datetime
import urllib.parse
import re
from hashlib import md5
import unicodedata

def namespaceDetect(title, site):
	""" Detect the namespace of a given title
	title - the page title
	site - the wiki object the page is on
	"""
	bits = title.split(':', 1)
	if len(bits) == 1 or bits[0] == '':
		return 0
	else:
		nsprefix = bits[0].lower() # wp:Foo and caTEGory:Foo are normalized by MediaWiki
		for ns in site.namespaces:
			if nsprefix == site.namespaces[ns]['*'].lower():
				return int(ns)
			if 'canonical' in site.namespaces[ns] and nsprefix == site.namespaces[ns]['canonical'].lower():
				return int(ns)
		else:
			if site.NSaliases:
				for ns in site.NSaliases:
					if nsprefix == ns.lower():
						return int(site.NSaliases[ns])
	return 0

class Page(object):
	""" A page on the wiki"""

	def __init__(self, site, title=None, check=True, followRedir=True, section=None, sectionnumber=None, pageid=None, namespace=None):
		"""
		site - A wiki object
		title - The page title, as a string or unicode object
		check - Checks for existence, normalizes title, required for most things
		followRedir - follow redirects (check must be true)
		section - the section name
		sectionnumber - the section number
		pageid - pageid, can be in place of title
		namespace - use to set the namespace prefix *if its not already in the title*
		"""
		# Initialize instance vars from function args
		if not title and not pageid:
			raise exceptions.WikiError("No title or pageid given")
		self.site = site
		if pageid:
			self.pageid = int(pageid)
		else:
			self.pageid = 0
		self.followRedir = followRedir
		self.title = title
		if self.title and '#' in self.title and section is None:
			self.title, section = self.title.split('#', 1)
		self.unprefixedtitle = '' # will be set later
		self.exists = None # None == not checked
		self.namespace = namespace
		self.lastedittime = ''
		# Things that need to be done before anything else
		if self.title:
			self.title = self.title.replace('_', ' ')
		if self.namespace:
			if namespace not in list(self.site.namespaces.keys()):
				raise exceptions.BadNamespace(namespace)
			if self.title:
				self.unprefixedtitle = self.title
				self.title = ':'.join((self.site.namespaces[self.namespace]['*'], self.title))
		# Setting page info with API, should set:
		# pageid, exists, title, unprefixedtitle, namespace
		if check:
			self.setPageInfo()
		elif self.title is not None:
			self.title = self.title.strip()
			if self.namespace is None and self.title:
				self.namespace = namespaceDetect(self.title, self.site)
				if self.namespace is not 0:
					nsname = self.site.namespaces[self.namespace]['*']
					case = self.site.namespaces[self.namespace]['case']
					self.unprefixedtitle = self.title.split(':', 1)[1]
					if case == 'first-letter':
						self.unprefixedtitle = self.unprefixedtitle[0].upper() + self.unprefixedtitle[1:]
					self.title = ':'.join((nsname, self.unprefixedtitle))
				else:
					case = self.site.namespaces[0]['case']
					if case == 'first-letter':
						self.title = self.title[0].upper() + self.title[1:]
					self.unprefixedtitle = self.title
		else:
			self.namespace = self.unprefixedtitle = self.urltitle = None
		if section or sectionnumber is not None:
			self.setSection(section, sectionnumber)
		else:
			self.section = None
		if self.title:
			self.urltitle = urllib.parse.quote(self.title).replace('%20', '_').replace('%2F', '/')
		if self.pageid < 0:
			self.pageid = 0

	def setPageInfo(self):
		"""Sets basic page info, required for almost everything"""
		followRedir = self.followRedir
		params = {'action':'query'}
		if self.pageid:
			params['pageids'] = self.pageid
		else:
			params['titles'] = self.title
		if followRedir:
			params['redirects'] = ''
		req = api.APIRequest(self.site, params)
		response = req.query(False)
		self.pageid = int(list(response['query']['pages'].keys())[0])
		if self.pageid > 0:
			self.exists = True
		if 'missing' in response['query']['pages'][str(self.pageid)]:
			if not self.title:
				# Pageids are never recycled, so a bad pageid with no title will never work
				raise exceptions.WikiError("Bad pageid given with no title")
			self.exists = False
		if 'invalid' in response['query']['pages'][str(self.pageid)]:
			raise exceptions.BadTitle(self.title)
		if 'title' in response['query']['pages'][str(self.pageid)]:
			self.title = response['query']['pages'][str(self.pageid)]['title']
			self.namespace = int(response['query']['pages'][str(self.pageid)]['ns'])
			if self.namespace is not 0:
				self.unprefixedtitle = self.title.split(':', 1)[1]
			else:
				self.unprefixedtitle = self.title
		if self.pageid < 0:
			self.pageid = 0
		return self

	def setNamespace(self, newns, recheck=True):
		"""Change the namespace number of a page object

		Updates the title with the new prefix
		newns - integer namespace number
		recheck - redo pageinfo checks

		"""
		if not newns in list(self.site.namespaces.keys()):
			raise exceptions.BadNamespace
		if self.namespace == newns:
			return self.namespace
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
			self.urltitle = urllib.parse.quote(self.title).replace('%20', '_').replace('%2F', '/')
		else:
			self.namespace = newns
		if recheck:
			self.pageid = 0
			self.setPageInfo()
		else:
			self.pageid = 0
		return self.namespace

	def setSection(self, section=None, number=None):
		"""Set a section for the page

		section - the section name
		number - the section number

		"""
		if section is None and number is None:
			self.section = None
		elif number is not None:
			try:
				self.section = int(number)
			except ValueError:
				raise exceptions.WikiError("Section number must be an int")
		else:
			self.section = self.__getSection(section)
		return self.section

	def __getSection(self, section):
		if not self.title:
			self.setPageInfo()
		params = {
			'action': 'parse',
			'page':self.title,
			'prop':'sections'
		}
		number = None
		req = api.APIRequest(self.site, params)
		response = req.query()
		for item in response['parse']['sections']:
			if section == item['line'] or section == item['anchor']:
				if item['index'].startswith('T'): # TODO: It would be cool if it set the page title to the template in this case
					continue
				number = item['index']
				break
		return int(number) if number is not None else None

	def canHaveSubpages(self):
		"""Is the page in a namespace that allows subpages?"""
		if not self.title:
			self.setPageInfo()
		return 'subpages' in self.site.namespaces[self.namespace]

	def isRedir(self):
		"""Is the page a redirect?"""
		if self.exists is None:
			self.setPageInfo()
		if self.exists is False:
			raise exceptions.NoPage
		params = {'action':'query',
			'redirects':'',
			'pageids':self.pageid
		}
		req = api.APIRequest(self.site, params)
		res = req.query(False)
		if 'redirects' in res['query']:
			return True
		else:
			return False

	def isTalk(self):
		"""Is the page a discussion page?"""
		if not self.title:
			self.setPageInfo()
		return (self.namespace%2==1 and self.namespace >= 0)

	def toggleTalk(self, check=True, followRedir=True):
		"""Switch to and from the talk namespaces

		Returns a new page object that's either the talk or non-talk
		version of the current page

		check and followRedir - same meaning as Page constructor

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
		"""Gets the Wikitext of the page

		expandtemplates - expand the templates to wikitext instead of transclusions
		force - Deprecated, unused

		"""
		if self.exists is None:
			self.setPageInfo()
		if self.exists is False:
			raise exceptions.NoPage
		params = {
			'action': 'query',
			'prop': 'revisions',
			'rvprop': 'content|timestamp',
			'rvlimit': '1',
			'pageids': self.pageid
		}
		if expandtemplates:
			params['rvexpandtemplates'] = '1'
		if self.section is not None:
			params['rvsection'] = self.section
		req = api.APIRequest(self.site, params)
		response = req.query(False)
		wikitext = response['query']['pages'][str(self.pageid)]['revisions'][0]['*']
		self.lastedittime = response['query']['pages'][str(self.pageid)]['revisions'][0]['timestamp']
		return wikitext

	def getLinks(self, force=False):
		"""Gets a list of all the internal links *on* the page

		force - Deprecated, unused

		"""
		if 'continue' not in self.site.features:
			raise exceptions.UnsupportedError("MediaWiki 1.21+ is required for this function")
		if self.exists is None:
			self.setPageInfo()
		if self.exists is False:
			raise exceptions.NoPage
		params = {
			'action': 'query',
			'prop': 'links',
			'pllimit': self.site.limit,
			'pageids': self.pageid
		}
		req = api.APIRequest(self.site, params)
		links = []
		for data in req.queryGen():
			links.extend(self.__extractToList(data, 'links'))
		return links

	def getProtection(self, force=False):
		"""Returns the current protection status of the page

		force - Deprecated, unused

		"""
		if self.exists is None:
			self.setPageInfo()
		params = {
			'action': 'query',
			'prop': 'info',
			'inprop': 'protection',
		}
		if not self.exists:
			params['titles'] = self.title
		else:
			params['pageids'] = self.pageid
		req = api.APIRequest(self.site, params)
		response = req.query(False)
		key = list(response['query']['pages'].keys())[0]
		pdata = response['query']['pages'][key]['protection']
		for pr in pdata:
			if pr['level']:
				if pr['expiry'] == 'infinity':
					expiry = 'infinity'
				else:
					expiry = datetime.datetime.strptime(pr['expiry'],'%Y-%m-%dT%H:%M:%SZ')
				cascade = True if 'cascade' in pr else False
				protection[pr['type']] = {
					'expiry': expiry,
					'level': pr['level'],
					'cascading': cascade
					}
		return protection

	def getTemplates(self, force=False):
		"""Gets all list of all the templates on the page

		force - Deprecated, unused

		"""
		if 'continue' not in self.site.features:
			raise exceptions.UnsupportedError("MediaWiki 1.21+ is required for this function")
		if self.exists is None:
			self.setPageInfo()
		if self.exists is False:
			raise exceptions.NoPage
		params = {
			'action': 'query',
			'prop': 'templates',
			'tllimit': self.site.limit,
			'pageids': self.pageid
		}
		req = api.APIRequest(self.site, params)
		templates = []
		for data in req.queryGen():
			templates.extend(self.__extractToList(data, 'templates'))
		return templates

	def getCategories(self, force=False):
		"""Gets all list of all the categories on the page

		force - Deprecated, unused

		"""
		if 'continue' not in self.site.features:
			raise exceptions.UnsupportedError("MediaWiki 1.21+ is required for this function")
		if self.exists is None:
			self.setPageInfo()
		if self.exists is False:
			raise exceptions.NoPage
		params = {
			'action': 'query',
			'prop': 'categories',
			'cllimit': self.site.limit,
			'pageids': self.pageid
		}
		req = api.APIRequest(self.site, params)
		categories = []
		for data in req.queryGen():
			categories.extend(self.__extractToList(data, 'categories'))
		return categories

	def getHistory(self, direction='older', content=True, limit='all', user=None):
		"""Get the history of a page

		direction - 2 options: 'older' (default) - start with the current revision and get older ones
			'newer' - start with the oldest revision and get newer ones
		content - If False, get only metadata (timestamp, edit summary, user, etc)
			If True (default), also get the revision text
		limit - Only retrieve a certain number of revisions. If 'all' (default), all revisions are returned
		user - Only get edits by a specific user. Can be a string or User object

		The data is returned in essentially the same format as the API, a list of dicts that look like:
		{'*': 'Page content', # Only returned when content=True
		 'comment': 'Edit summary',
		 'contentformat': 'text/x-wiki', # Only returned when content=True
		 'contentmodel': 'wikitext', # Only returned when content=True
		 'parentid': 1083209, # ID of previous revision
		 'revid': 1083211, # Revision ID
		 'sha1': '315748b8e6fb6343efed3c17b56edc2da1d9e8b5', # SHA1 hash of wikitext
		 'size': 157, # Size, in bytes
		 'timestamp': '2014-07-30T19:26:53Z', # Timestamp of edit
		 'user': 'Example', # Username of editor
		 'userid': 587508 # User ID of editor
		}

		Note that unlike other get* functions, the data is not cached
		"""
		if self.exists is None:
			self.setPageInfo()
		if self.exists is False:
			raise exceptions.NoPage
		rvuser = None
		if user is not None and isinstance(user, str):
			rvuser = user
		elif user is not None:
			rvuser = user.name
		rvprop='ids|flags|timestamp|user|userid|size|sha1|comment'
		if content:
			rvprop += '|content'
		return internalfunctions.getList(self, 'prop', 'revisions', 'rv', direction, limit, lowlimit=content, 
		pageids=self.pageid, rvprop=rvprop, rvuser=rvuser)


	def getHistoryGen(self, direction='older', content=True, limit='all', user=None):
		"""Generator function for page history

		The interface is the same as getHistory, but it will only retrieve 1 revision at a time.
		This will be slower and have much higher network overhead, but does not require storing
		the entire page history in memory
		"""
		if self.exists is None:
			self.setPageInfo()
		if self.exists is False:
			raise exceptions.NoPage
		rvuser = None
		if user is not None and isinstance(user, str):
			rvuser = user
		elif user is not None:
			rvuser = user.name
		rvprop='ids|flags|timestamp|user|userid|size|sha1|comment'
		if content:
			rvprop += '|content'
		return internalfunctions.getListGen(self, 'prop', 'revisions', 'rv', direction, limit, 
		pageids=self.pageid, rvprop=rvprop, rvuser=rvuser)

	def getLogs(self, logtype=None, direction='older', limit='all', user=None):
		"""Get the logs for a page

		direction - 2 options: 'older' (default) - start with most recent log entry and get older ones
			'newer' - start with the oldest entry and get newer ones
		logtype - Only get specific logs: 'delete' for deletion log, 'protect' for protection log, etc. 
			The function doesn't check this value as extensions can add their own log types. See the
			MW API's documentation for list=logevents for valid options on a given wiki
		limit - Only retrieve a certain number of entries. If 'all' (default), all revisions are returned
		user - Only get logs done BY a specific user. Can be a string or User object

		The data is returned in essentially the same format as the API, a list of dicts that look like:
                { "logid": 62110732,   # The id in the logging DB table, not really used anywhere
                  "pageid": 45262920,  # The current page ID, will be 0 for a deletion log
                  "logpage": 37927495, # The page ID at the time the log entry was made
                  "move": {            # Some log types have additional data like this, the format will vary depending on type
                      "new_ns": 0,
                      "new_title": "New page title"
                  },
                  "type": "move",
                  "action": "move",
                  "user": "Username",
                  "userid": 1137359,
                  "timestamp": "2015-01-31T02:34:48Z",
                  "comment": "Log summary",
                  "tags": []
                },

		Note that unlike other get* functions, the data is not cached
		"""
		if self.title is None:
			self.setPageInfo()
		leuser = None
		if user is not None and isinstance(user, str):
			leuser = user
		elif user is not None:
			leuser = user.name
		return internalfunctions.getList(self, 'list', 'logevents', 'le', direction, limit, letitle=self.title,
		leprop='ids|type|user|userid|timestamp|comment|tags|details', leuser=leuser, letype=logtype)


	def getLogsGen(self, logtype=None, direction='older', limit='all', user=None):
		"""Generator function for page logs

		The interface is the same as getLogs, but it will only retrieve 1 entry at a time.
		"""
		if self.title is None:
			self.setPageInfo()
		leuser = None
		if user is not None and isinstance(user, str):
			leuser = user
		elif user is not None:
			leuser = user.name
		return internalfunctions.getListGen(self, 'list', 'logevents', 'le', direction, limit, letitle=self.title,
		leprop='ids|type|user|userid|timestamp|comment|tags|details', leuser=leuser, letype=logtype)

	def __extractToList(self, json, stuff):
		datalist = []
		key = list(json['query']['pages'].keys())[0]
		if stuff in json['query']['pages'][key]:
			for item in json['query']['pages'][key][stuff]:
				datalist.append(item['title'])
		return datalist

	def edit(self, *args, **kwargs):
		"""Edit the page

		Arguments are a subset of the API's action=edit arguments, valid arguments
		are defined in the validargs set
		To skip the MD5 check, set "skipmd5" keyword argument to True
		http://www.mediawiki.org/wiki/API:Edit_-_Create%26Edit_pages#Parameters

		For backwards compatibility:
		'newtext' is equivalent to  'text'
		'basetime' is equivalent to 'basetimestamp'

		"""
		validargs = set(['text', 'summary', 'minor', 'notminor', 'bot', 'basetimestamp', 'starttimestamp',
			'recreate', 'createonly', 'nocreate', 'watch', 'unwatch', 'watchlist', 'prependtext', 'appendtext',
			'section', 'sectiontitle', 'captchaword', 'captchaid', 'contentformat', 'contentmodel'])
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
		if not 'section' in kwargs and self.section is not None:
			kwargs['section'] = self.section
		if not 'text' in kwargs and not 'prependtext' in kwargs and not 'appendtext' in kwargs:
			raise exceptions.EditError("No text specified")
		if 'prependtext' in kwargs and 'section' in kwargs:
			raise exceptions.EditError("Bad param combination")
		if 'createonly' in kwargs and 'nocreate' in kwargs:
			raise exceptions.EditError("Bad param combination")
		token = self.site.getToken('csrf')
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
			hashtext = unicodedata.normalize('NFC', hashtext).encode('utf-8')
			params['md5'] = md5(hashtext).hexdigest()
		params.update(kwargs)
		req = api.APIRequest(self.site, params, write=True)
		result = req.query()
		if 'edit' in result and result['edit']['result'] == 'Success':
			self.exists = True
			self.pageid = result['edit']['pageid']
		return result

	def move(self, mvto, reason='', movetalk=False, noredirect=False, movesubpages=True, watch=False, unwatch=False, watchlist='preferences'):
		"""Move the page

		Params are the same as the API:
		mvto - page title to move to, the only required param
		reason - summary for the log
		movetalk - move the corresponding talk page
		noredirect - don't create a redirect at the previous title
		movesubpages - Move all subpages of the title
		watch - add the page to your watchlist (DEPRECATED, use watchlist)
		unwatch - remove the page from your watchlist (DEPRECATED, use watchlist)
		watchlist - Options are "preferences", "watch", "unwatch", or "nochange"

		"""
		if self.exists is None:
			self.setPageInfo()
		if self.exists is False:
			raise exceptions.NoPage
		token = self.site.getToken('csrf')
		params = {
			'action': 'move',
			'to':mvto,
			'token':token,
			'fromid':self.pageid
		}
		if reason:
			params['reason'] = reason
		if movetalk:
			params['movetalk'] = '1'
		if noredirect:
			params['noredirect'] = '1'
		if movesubpages:
			params['movesubpages'] = '1'
		if watch:
			params['watch'] = '1'
		if unwatch:
			params['unwatch'] = '1'
		if watchlist:
			params['watchlist'] = watchlist
		req = api.APIRequest(self.site, params, write=True)
		result = req.query()
		if 'move' in result:
			self.title = result['move']['to']
			self.namespace = namespaceDetect(self.title, self.site)
			if self.namespace is not 0:
				self.unprefixedtitle = self.title.split(':', 1)[1]
			else:
				self.unprefixedtitle = self.title
			self.urltitle = urllib.parse.quote(self.title).replace('%20', '_').replace('%2F', '/')
		return result

	def protect(self, restrictions={}, expirations={}, reason='', cascade=False, watch=False, watchlist='preferences'):
		"""Protect a page

		Restrictions and expirations are dictionaries of
		protection level/expiry settings, e.g., {'edit':'sysop'} and
		{'move':'3 days'}.

		reason - summary for log
		cascade - apply protection to all pages transcluded on the page
		watch - add the page to your watchlist (DEPRECATED, use watchlist)
		watchlist - Options are "preferences", "watch", "unwatch", or "nochange"

		"""
		if not self.title:
			self.setPageInfo()
		if not restrictions:
			raise exceptions.ProtectError("No protection levels given")
		if len(expirations) > len(restrictions):
			raise exceptions.ProtectError("More expirations than restrictions given")
		token = self.site.getToken('csrf')
		protections = ''
		expiry = ''
		for prtype in restrictions:
			if protections:
				protections+="|"
			protections+= prtype+"="+restrictions[prtype]
			if prtype in expirations:
				if expiry:
					expiry+="|"
				expiry+=expirations[prtype]
			else:
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
		if watch:
			params['watch'] = '1'
		if watchlist:
			params['watchlist'] = watchlist
		req = api.APIRequest(self.site, params, write=True)
		result = req.query()
		return result

	def delete(self, reason='', watch=False, unwatch=False, watchlist='preferences'):
		"""Delete the page

		reason - summary for log
		watch - add the page to your watchlist (DEPRECATED, use watchlist)
		unwatch - remove the page from your watchlist (DEPRECATED, use watchlist)
		watchlist - Options are "preferences", "watch", "unwatch", or "nochange"

		"""
		if self.exists is None:
			self.setPageInfo()
		if self.exists is False:
			raise exceptions.NoPage
		token = self.site.getToken('csrf')
		params = {
			'action': 'delete',
			'token':token,
			'pageid':self.pageid
		}
		if reason:
			params['reason'] = reason
		if watch:
			params['watch'] = '1'
		if unwatch:
			params['unwatch'] = '1'
		if watchlist:
			params['watchlist'] = watchlist
		req = api.APIRequest(self.site, params, write=True)
		result = req.query()
		if 'delete' in result:
			self.pageid = 0
			self.exists = False
			self.section = None
		return result

	def __getattr__(self, name):
		"""Computed attributes:
		templates, links, categories, wikitext, protection
		"""
		if name not in {'templates', 'links', 'categories', 'wikitext', 'protection'}:
			msg = "{0} object has no attribute {1}".format(repr(type(self).__name__), repr(name))
			raise AttributeError(msg)
		if name == 'templates':
			return self.getTemplates()
		elif name == 'links':
			return self.getLinks()
		elif name == 'categories':
			return self.getCategories()
		elif name == 'wikitext':
			return self.getWikiText()
		elif name == 'protection':
			return self.getProtection()

	def __hash__(self):
		return hash(self.title) ^ hash(self.site.apibase)

	def __str__(self):
		if self.title:
			title = self.title
		else:
			title = 'pageid: '+self.pageid
		return self.__class__.__name__ +' '+repr(title) + " from " + repr(self.site.domain)

	def __repr__(self):
		if self.title:
			title = self.title
		else:
			title = 'pageid: '+str(self.pageid)
		return "<"+self.__module__+'.'+self.__class__.__name__+" "+repr(title)+" using "+repr(self.site.apibase)+">"

	def __eq__(self, other):
		if not isinstance(other, Page):
			return False
		if self.title:
			if self.title == other.title and self.site == other.site:
				return True
		else:
			if self.pageid == other.pageid and self.site == other.site:
				return True
		return False

	def __ne__(self, other):
		if not isinstance(other, Page):
			return True
		if self.title:
			if self.title == other.title and self.site == other.site:
				return False
		else:
			if self.pageid == other.pageid and self.site == other.site:
				return False
		return True
