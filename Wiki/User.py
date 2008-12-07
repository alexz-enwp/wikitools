# -*- coding: utf-8 -*-
import Wiki, Page, API

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
		self.page = Page.Page(self.wiki, self.name, check=check, followRedir=False)
	
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
		req = API.APIRequest(self.wiki, params)
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
		