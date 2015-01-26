# -*- coding: utf-8 -*-
# Copyright 2008-2013 Alex Zaddach (mrzmanwiki@gmail.com), bjweeks

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

from . import page
from . import api
import ipaddress

class User:
	"""A user on the wiki"""
	def __init__(self, site, name, check=True):
		"""
		wiki - A wiki object
		name - The username, as a string - do not include a "User:" prefix
		check - Checks for existence, normalizes name
		"""
		self.site = site
		self.name = name.strip()
		self.exists = None
		self._blocked = None
		self.editcount = 0
		self.groups = []
		self.id = 0
		try:
			ip = ipaddress.ip_address(self.name)
			self.name = ip.compressed
			self.exists = False
			self.isIP = True
			self.groups = ['*']
		except ValueError:
			self.isIP = False
			if check:
				self.setUserInfo()

	def setUserInfo(self):
		"""Sets basic user info"""
		params = {
			'action': 'query',
			'list': 'users',
			'ususers':self.name,
			'usprop':'blockinfo|groups|editcount'
		}
		req = api.APIRequest(self.site, params)
		response = req.query(False)
		user = response['query']['users'][0]
		self.name = user['name']
		if 'missing' in user or 'invalid' in user:
			self.exists = False
			return
		self.id = int(user['userid'])
		self.editcount = int(user['editcount'])
		if 'groups' in user:
			self.groups = user['groups']
		if 'blockedby' in user:
			self._blocked = True
		else:
			self._blocked = False
		return self

	def getUserPage(self, check=True, followRedir=False):
		"""Convenience function to get an object for the user's user page"""
		return page.Page(self.site, title=self.name, namespace=2, check=check, followRedir=False)

	def getTalkPage(self, check=True, followRedir=False):
		"""Convenience function to get an object for the user's talk page"""
		return page.Page(self.site, title=self.name, namespace=3, check=check, followRedir=False)

	def isBlocked(self, force=False):
		"""Determine if a user is blocked"""
		if self._blocked is not None and not force:
			return self._blocked
		params = {'action':'query',
			'list':'blocks',
			'bkusers':self.name,
			'bkprop':'id'
		}
		req = api.APIRequest(self.site, params)
		res = req.query(False)
		if len(res['query']['blocks']) > 0:
			self._blocked = True
		else:
			self._blocked = False
		return self._blocked

	def block(self, reason='', expiry=None, anononly=True, nocreate=True, autoblock=True, noemail=False, hidename=False, allowusertalk=True, reblock=False, watchuser=False):
		"""Block the user

		Params are the same as the API
		reason - block reason
		expiry - block expiration
		anononly - block anonymous users only
		nocreate - disable account creation
		autoblock - block IP addresses used by the user
		noemail - block user from sending email through the site
		hidename - hide the username from the log (requires hideuser right)
		allowusertalk - allow the user to edit their talk page
		reblock - overwrite existing block
		watchuser - Watch userpage
		"""
		token = self.site.getToken('csrf')
		params = {'action':'block',
			'user':self.name,
			'token':token
		}
		if reason:
			params['reason'] = reason
		if expiry:
			params['expiry'] = expiry
		if anononly:
			params['anononly'] = ''
		if nocreate:
			params['nocreate'] = ''
		if autoblock:
			params['autoblock'] = ''
		if noemail:
			params['noemail'] = ''
		if hidename:
			params['hidename'] = ''
		if allowusertalk:
			params['allowusertalk'] = ''
		if reblock:
			params['reblock'] = ''
		if watchuser:
			params['watchuser'] = ''
		req = api.APIRequest(self.site, params, write=False)
		res = req.query()
		if 'block' in res:
			self._blocked = True
		return res

	def unblock(self, reason=''):
		"""Unblock the user

		reason - reason for the log

		"""
		token = self.site.getToken('csrf')
		params = {
		    'action': 'unblock',
			'user': self.name,
			'token': token
		}
		if reason:
			params['reason'] = reason
		req = api.APIRequest(self.site, params, write=False)
		res = req.query()
		if 'unblock' in res:
			self._blocked = False
		return res

	def __getattr__(self, name):
		"""Computed attributes:
		page, talk, blocked
		"""
		if name not in {'page', 'talk', 'blocked'}:
			raise AttributeError
		if name == 'page':
			return self.getUserPage()
		elif name == 'talk':
			return self.getTalkPage()
		elif name == 'blocked':
			return self.isBlocked()

	def __hash__(self):
		return hash(self.name) ^ hash(self.site.apibase)

	def __eq__(self, other):
		if not isinstance(other, User):
			return False
		if self.name == other.name and self.site == other.site:
			return True
		return False
	def __ne__(self, other):
		if not isinstance(other, User):
			return True
		if self.name == other.name and self.site == other.site:
			return False
		return True

	def __str__(self):
		return self.__class__.__name__ + ' ' + repr(self.name) + " on " + repr(self.site.domain)

	def __repr__(self):
		return "<"+self.__module__+'.'+self.__class__.__name__+" "+repr(self.name)+" on "+repr(self.site.apibase)+">"
		
