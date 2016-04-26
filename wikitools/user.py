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

import wiki
import page
import api
import socket
import re

class NoUser(wiki.WikiError):
	"""Non-existent user"""

class User:
	"""A user on the wiki"""
	def __init__(self, site, name, check=True):
		"""
		wiki - A wiki object
		name - The username, as a string
		check - Checks for existence, normalizes name
		"""	
		self.site = site
		self.name = name.strip()
		if not isinstance(self.name, unicode):
			self.name = unicode(self.name, 'utf8')
		self.exists = True # If we're not going to check, assume it does
		self.blocked = None # So we can tell the difference between blocked/not blocked/haven't checked
		self.editcount = -1
		self.groups = []
		self.id = 0
		if check:
			self.setUserInfo()
		self.isIP = False
		self.IPcheck()
		self.page = page.Page(self.site, ':'.join([self.site.namespaces[2]['*'], self.name]), check=check, followRedir=False)
	
	def IPcheck(self):
		try: #IPv4 check
                        s = socket.inet_aton(self.name.replace(' ', '_'))
                        if socket.inet_ntoa(s) == self.name:
                                self.isIP = True
                                self.exists = False
				return
                except:
                        pass
		try:
			s = socket.inet_pton(socket.AF_INET6, self.name.replace(' ', '_'))
			if self.IPnorm(socket.inet_ntop(socket.AF_INET6, s)) == self.IPnorm(self.name):
				self.isIP = True
				self.exists = False
				self.name = self.IPnorm(self.name)
				return
		except:
			pass

	def IPnorm(self, ip):
		"""This is basically a port of MediaWiki's IP::sanitizeIP but assuming no CIDR ranges"""
		ip = ip.upper()
		# Expand zero abbreviations
		abbrevPos = ip.find('::')
		if abbrevPos != -1:
			addressEnd = len(ip) - 1
			# If the '::' is at the beginning...
			if abbrevPos == 0:
				repeat = '0:'
				extra = '0' if ip == '::' else ''
				pad = 9
			elif abbrevPos == addressEnd - 1:
				repeat = ':0'
				extra = ''
				pad = 9
			else:
				repeat = ':0'
				extra = ':'
				pad = 8
			ip = ip.replace( '::', repeat*(pad-ip.count(':'))+extra)
		# Remove leading zereos from each bloc as needed
		ip = re.sub('/(^|:)0+(([0-9A-Fa-f]{1,4}))/', '\1\2', ip)
		return ip;

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
			self.blocked = True
		else:
			self.blocked = False
		return self
		
	def getTalkPage(self, check=True, followRedir=False):
		"""Convenience function to get an object for the user's talk page"""
		return page.Page(self.site, ':'.join([self.site.namespaces[3]['*'], self.name]), check=check, followRedir=False)
		
	def isBlocked(self, force=False):
		"""Determine if a user is blocked"""
		if self.blocked is not None and not force:
			return self.blocked
		params = {'action':'query',
			'list':'blocks',
			'bkusers':self.name,
			'bkprop':'id'
		}
		req = api.APIRequest(self.site, params)
		res = req.query(False)
		if len(res['query']['blocks']) > 0:
			self.blocked = True
		else:
			self.blocked = False
		return self.blocked		
			
	def block(self, reason=False, expiry=False, anononly=False, nocreate=False, autoblock=False, noemail=False, hidename=False, allowusertalk=False, reblock=False):
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
		req = api.APIRequest(self.site, params, write=False)
		res = req.query()
		if 'block' in res:
			self.blocked = True
		return res
		
	def unblock(self, reason=False):
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
			self.blocked = False
		return res
	
	def getContributions(self, direction='older', limit='all'):
		"""Get the history of a user
		
		direction - 2 options: 'older' (default) - start with the current revision and get older ones
			'newer' - start with the oldest revision and get newer ones
		content - If False, get only metadata (timestamp, edit summary, user, etc)
			If True (default), also get the revision text
		limit - Only retrieve a certain number of revisions. If 'all' (default), all revisions are returned 
		
		The data is returned in essentially the same format as the API, a list of dicts that look like:
		{u'*': u"Page content", # Only returned when content=True
		 u'comment': u'Edit summary',
		 u'contentformat': u'text/x-wiki', # Only returned when content=True
		 u'contentmodel': u'wikitext', # Only returned when content=True
		 u'parentid': 139946, # id of previous revision
		 u'revid': 139871, # revision id
		 u'sha1': u'0a5cec3ca3e084e767f00c9a5645c17ac27b2757', # sha1 hash of page content
		 u'size': 129, # size of page in bytes
		 u'timestamp': u'2002-08-05T14:11:27Z', # timestamp of edit
		 u'user': u'Username',
		 u'userid': 48 # user id
		}		
		
		Note that unlike other get* functions, the data is not cached
		"""
		max = limit
		if limit == 'all':
			max = float("inf")
		if limit == 'all' or limit > self.site.limit:
			limit = self.site.limit
		history = []
		ucc = None
		while True:
			revs, ucc = self.__getContributionsInternal(direction, limit, ucc)
			history = history+revs
			if len(history) == max or ucc is None:
				break
			if max - len(history) < self.site.limit:
				limit = max - len(history)
		return history
		
	def getContributionsGen(self, direction='older', limit='all'):
		"""Generator function for user contributions
		
		The interface is the same as getHistory, but it will only retrieve 1 revision at a time.
		This will be slower and have much higher network overhead, but does not require storing
		the entire page history in memory	
		"""
		max = limit
		count = 0
		ucc = None
		while True:
			revs, ucc = self.__getContributionsInternal(direction, 1, ucc)
			yield revs[0]
			count += 1
			if count == max or ucc is None:
				break
	
	def __getContributionsInternal(self, direction, limit, uccontinue):
	
		if self.id == 0 and not self.name:
			self.setUserInfo()
		if not self.exists:
			raise NoUser
		if direction != 'newer' and direction != 'older':
			raise wiki.WikiError("direction must be 'newer' or 'older'")
		params = {
			'action':'query',
			'list':'usercontribs',
			'rvdir':direction,
			'ucprop':'ids|title|timestamp|comment|size|sizediff|tags',
			'continue':'',
			'rvlimit':limit
		}
		if self.name:
			params['ucuser'] = self.name
		else:
			raise NoUser

		if uccontinue:
			params['continue'] = uccontinue['continue']
			params['uccontinue'] = uccontinue['uccontinue']
		req = api.APIRequest(self.site, params)
		response = req.query(False)
		#id = response['query']['pages'].keys()[0]
		#if not self.pageid:
		#	self.pageid = int(id)
		revs = response['query']['usercontribs']#[id]['revisions']
		ucc = None
		if 'continue' in response:
			ucc = response['continue']
		return (revs, ucc)
	
	#def __extractToList(self, json, stuff):
	#	list = []
	#	if self.pageid == 0:
	#		self.pageid = json['query']['usercontribs'].keys()[0]
	#	if stuff in json['query']['usercontribs'][str(self.pageid)]:
	#		for item in json['query']['usercontribs'][str(self.pageid)][stuff]:
	#			list.append(item['title'])
	#	return list
	
	def __hash__(self):
		return int(self.name) ^ hash(self.site.apibase)
	
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
		
