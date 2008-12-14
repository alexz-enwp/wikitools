# -*- coding: utf-8 -*-
import wiki, page, api

class User:
	""" A user on the wiki
	wiki - A wiki object
	name - The username, as a string
	check - Checks for existence, normalizes name
	"""	
	def __init__(self, wiki, name, check=True):
		self.wiki = wiki
		self.name = name
		if not isinstance(self.name, unicode):
			self.name = unicode(self.name, 'utf8')
		self.exists = True # If we're not going to check, assume it does
		self.blocked = False
		self.editcount = -1
		self.groups = []
		if check:
			self.setUserInfo()
		self.page = page.Page(self.wiki, self.name, check=check, followRedir=False)
	
	def setUserInfo(self):
		"""
		Sets basic user info
		"""		
		params = {
			'action': 'query',
			'list': 'users',
			'ususers':self.name,
			'usprop':'blockinfo|groups|editcount'
		}
		req = api.APIRequest(self.wiki, params)
		response = req.query()
		user = response['query']['users'][0]
		self.name = user['name']
		if 'missing' in user or 'invalid' in user:
			self.exists = False
			return
		self.editcount = int(user['editcount'])
		if 'groups' in user:
			self.groups = user['groups']
		if 'blockedby' in user:
			self.blocked = True
			
	def block(self, reason=False, expiry=False, anononly=False, nocreate=False, autoblock=False, noemail=False, hidename=False, allowusertalk=False):
		params = {'action':'block',
			'user':self.name,
			'gettoken':''
		}
		req = api.APIRequest(self.wiki, params)
		res = req.query()
		token = res['block']['blocktoken']
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
		req = api.APIRequest(self.wiki, params, write=False)
		res = req.query()
		return res
		
	def unblock(self, reason=False):
		params = {
		    'action': 'unblock',
			'user': self.name,
			'gettoken': ''
		}
		req = api.APIRequest(self.wiki, params)
		res = req.query()
		token = res['unblock']['unblocktoken']
		params = {
		    'action': 'unblock',
			'user': self.name,
			'token': token
		}
		if reason:
			params['reason'] = reason
		req = api.APIRequest(self.wiki, params, write=False)
		res = req.query()
		return res
	
	def __eq__(self, other):
		if not isinstance(other, User):
			return False
		if self.name == other.name and self.wiki == other.wiki:
			return True
		return False
	def __ne__(self, other):
		if not isinstance(other, User):
			return True
		if self.name == other.name and self.wiki == other.wiki:
			return False
		return True
			
		