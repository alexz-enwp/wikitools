# -*- coding: utf-8 -*-
# Copyright 2008-2013 Alex Zaddach (mrzmanwiki@gmail.com)

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

import requests
import wikitools.api
import re
import time
import os
import warnings
from urllib.parse import urlparse

class WikiError(Exception):
	"""Base class for errors"""

class UserBlocked(WikiError):
	"""Trying to edit while blocked"""

class Namespace(int):
	"""
	Class for namespace 'constants'
	Names are based on canonical (non-localized) names
	This functions as an integer in every way, except that the OR operator ( | )
	is overridden to produce a string namespace list for use in API queries
	wikiobj.NS_MAIN|wikiobj.NS_USER|wikiobj.NS_PROJECT returns '0|2|4'
	"""
	def __or__(self, other):
		return '|'.join([str(self), str(other)])

	def __ror__(self, other):
		return '|'.join([str(other), str(self)])

VERSION = '2.0'

class Wiki:
	"""A Wiki site"""

	def __init__(self, url="https://en.wikipedia.org/w/api.php", httpuser=None, httppass=None, authman=None):
		"""
		url - A URL to the site's API, defaults to en.wikipedia
		httpuser - optional user name for HTTP Basic Auth
		httppass - password for HTTP Basic Auth, leave out to enter interactively
		authman - If using something other than HTTP Basic Auth, a requests Auth object
		such as requests.auth.HTTPDigestAuth('user', 'pass') for Digest Auth
		See <http://docs.python-requests.org/en/latest/user/authentication/>
		"""
		self.apibase = url
		self.session = requests.Session()
		self.username = ''
		urlbits = urlparse(self.apibase)
		self.domain = '://'.join([urlbits.scheme, urlbits.netloc])
		if httpuser is not None:
			if httppass is None:
				from getpass import getpass
				httppass = getpass("HTTP Auth password for "+httpuser+": ")
			self.auth = requests.auth.HTTPBasicAuth(httpuser, httppass)
		elif authman:
			self.auth=authman
		else:
			self.auth = None
		self.maxlag = 5
		self.maxwaittime = 120
		self.useragent = "python-wikitools/%s" % VERSION
		self.limit = 500
		self.siteinfo = {}
		self.namespaces = {}
		self.NSaliases = {}
		self.assertval = None
		self.newtoken = False
		try:
			self.setSiteinfo()
		except wikitools.api.APIError: # probably read-restricted
			pass

	def setSiteinfo(self):
		"""Retrieves basic siteinfo

		Called when constructing,
		or after login if the first call failed

		"""
		params = {'action':'query',
			'meta':'siteinfo|tokens',
			'siprop':'general|namespaces|namespacealiases',
		}
		if self.maxlag < 120:
			params['maxlag'] = 120
		req = wikitools.api.APIRequest(self, params)
		info = req.query(False)
		sidata = info['query']['general']
		for item in sidata:
			self.siteinfo[item] = sidata[item]
		nsdata = info['query']['namespaces']
		for ns in nsdata:
			nsinfo = nsdata[ns]
			self.namespaces[nsinfo['id']] = nsinfo
			if ns != "0":
				try:
					attr = "NS_%s" % (nsdata[ns]['canonical'].replace(' ', '_').upper())
				except KeyError:
					attr = "NS_%s" % (nsdata[ns]['*'].replace(' ', '_').upper())
			else:
				attr = "NS_MAIN"
			setattr(self, attr, Namespace(ns))
		nsaliasdata = info['query']['namespacealiases']
		if nsaliasdata:
			for ns in nsaliasdata:
				self.NSaliases[ns['*']] = ns['id']
		if not 'writeapi' in sidata:
			warnings.warn("WARNING: Write-API not enabled, you will not be able to edit", UserWarning)
		version = re.search("\d\.(\d\d)", self.siteinfo['generator'])
		if not int(version.group(1)) >= 13: # Will this even work on 13?
			warnings.warn("WARNING: Some features may not work on older versions of MediaWiki", UserWarning)
		if 'tokens' in list(info['query'].keys()):
			self.newtoken = True
		return self

	def login(self, username, password=False, verify=True, domain=None):
		"""Login to the site

		username - the user account name on the wiki
		password - the password for the account - leave empty to enter interactively
		verify - Checks cookie validity with isLoggedIn()
		domain - domain name, required for some auth systems like LDAP

		"""
		if not password:
			from getpass import getpass
			password = getpass("Wiki password for "+username+": ")
		def loginerror(info):
			try:
				warnings.warn(info['login']['result'], UserWarning)
			except:
				warnings.warn(info['error']['code'], UserWarning)
				warnings.warn(info['error']['info'], UserWarning)
			return False
		data = {
			"action" : "login",
			"lgname" : username,
			"lgpassword" : password,
		}
		if domain is not None:
			data["lgdomain"] = domain
		if self.maxlag < 120:
			data['maxlag'] = 120
		req = wikitools.api.APIRequest(self, data)
		info = req.query()
		if info['login']['result'] == "Success":
			self.username = username
		elif info['login']['result'] == "NeedToken":
			req.changeParam('lgtoken', info['login']['token'])
			info = req.query()
			if info['login']['result'] == "Success":
				self.username = username
			else:
				return loginerror(info)
		else:
			return loginerror(info)
		if verify and not self.isLoggedIn(self.username):
			return False
		if not self.siteinfo:
			self.setSiteinfo()
		params = {
			'action': 'query',
			'meta': 'userinfo',
			'uiprop': 'rights',
		}
		if self.maxlag < 120:
			params['maxlag'] = 120
		req = wikitools.api.APIRequest(self, params)
		info = req.query(False)
		user_rights = info['query']['userinfo']['rights']
		if 'apihighlimits' in user_rights:
			self.limit = 5000
		if self.useragent == "python-wikitools/%s" % VERSION:
			self.useragent = "python-wikitools/%s (User:%s)" % (VERSION, self.username)
			return True

	def logout(self):
		params = { 'action': 'logout' }
		if self.maxlag < 120:
			params['maxlag'] = 120
		req = wikitools.api.APIRequest(self, params, write=True)
		# action=logout returns absolutely nothing, which json.loads() treats as False
		# causing APIRequest.query() to get stuck in a loop
		req.wiki.session.post(req.wiki.apibase, params=req.data, headers=req.headers, auth=req.authman)
		self.username = ''
		self.maxlag = 5
		self.useragent = "python-wikitools/%s" % VERSION
		self.limit = 500
		self.session = requests.Session()
		return True

	def isLoggedIn(self, username=None):
		"""Verify that we are a logged in user

		username - specify a username to check against

		"""

		data = {
			"action" : "query",
			"meta" : "userinfo",
		}
		if self.maxlag < 120:
			data['maxlag'] = 120
		req = wikitools.api.APIRequest(self, data)
		info = req.query(False)
		if info['query']['userinfo']['id'] == 0:
			return False
		elif username and info['query']['userinfo']['name'] != username:
			return False
		else:
			return True

	def setMaxlag(self, maxlag = 5):
		"""Set the maximum server lag to allow

		If the lag is > the maxlag value, all requests will wait
		Setting to a negative number will disable maxlag checks

		"""
		try:
			int(maxlag)
		except:
			raise WikiError("maxlag must be an integer")
		self.maxlag = int(maxlag)
		return self.maxlag

	def setUserAgent(self, useragent):
		"""Function to set a different user-agent"""
		self.useragent = str(useragent)
		return self.useragent

	def setAssert(self, value):
		"""Set an assertion value

		This only makes a difference on sites with the AssertEdit extension
		on others it will be silently ignored
		This is only checked on edits, so only applied to write queries

		Set to None (the default) to not use anything
		http://www.mediawiki.org/wiki/Extension:Assert_Edit

		"""
		valid = ['user', 'bot', 'true', 'false', 'exists', 'test', None]
		if value not in valid:
			raise WikiError("Invalid assertion")
		self.assertval = value
		return self.assertval

	def getToken(self, tokentype):
		"""Get a token

		For wikis with MW 1.24 or newer:
		tokentype (string) - csrf, deleteglobalaccount, patrol, rollback, setglobalaccountstatus, userrights, watch

		For older wiki versions, only csrf (edit, move, etc.) tokens are supported

		"""
		if self.newtoken:
			params = {
				'action':'query',
				'meta':'tokens',
				'type':tokentype,
			}
			req = wikitools.api.APIRequest(self, params)
			response = req.query(False)
			token = response['query']['tokens'][tokentype+'token']
		else:
			if tokentype not in ['edit', 'delete', 'protect', 'move', 'block', 'unblock', 'email', 'csrf']:
				raise WikiError('Token type unavailable')
			params = {
				'action':'query',
				'prop':'info',
				'intoken':'edit',
				'titles':'1'
			}
			req = wikitools.api.APIRequest(self, params)
			response = req.query(False)
			pid = list(response['data']['query']['pages'].keys())[0]
			token = response['query']['pages'][pid]['edittoken']
		return token


	def __hash__(self):
		return hash(self.apibase)

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

	def __str__(self):
		if self.username:
			user = ' - using User:'+self.username
		else:
			user = ' - not logged in'
		return self.domain + user

	def __repr__(self):
		if self.username:
			user = ' User:'+self.username
		else:
			user = ' not logged in'
		return "<"+self.__module__+'.'+self.__class__.__name__+" "+repr(self.apibase)+user+">"
	
