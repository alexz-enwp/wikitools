# -*- coding: utf-8 -*-
import wiki, page, api

class Category(page.Page):
	"""
	A category on the wiki
	title should be the full title, including "Category:"
	"""
	def __init__(self, site, title=False, check=True, followRedir=False, section=False, sectionnumber=False, pageid=False):
		self.members = []
		page.Page.__init__(self, site=site, title=title, check=check, followRedir=followRedir, section=section, sectionnumber=sectionnumber, pageid=pageid)
			
	def getAllMembers(self, titleonly=False, reload=False):
		"""
		Gets a list of pages in the category
		titleonly - set to True to only create a list of strings,
		else it will be a list of Page objects
		reload - reload the list even if it was generated before
		"""
		if self.members and not reload:
			if titleonly:
				ret = []
				for member in self.members:
					ret.append(member.title)
				return ret
			return self.members
		else:
			ret = []
			self.members = []
			for member in self.__getMembersInternal():
				self.members.append(member)
				if titleonly:
					ret.append(member.title)
			if titleonly:
				return ret
			return self.members
	
	def getAllMembersGen(self, titleonly=False, reload=False):
		"""
		Generator function for pages in the category
		titleonly - set to True to return strings,
		else it will return Page objects
		reload - reload the list even if it was generated before
		"""
		if self.members and not reload:
			for member in self.members:
				if titleonly:
					yield member.title
				else:
					yield member
		else:
			self.members = []
			for member in self.__getMembersInternal():
				self.members.append(member)
				if titleonly:
					yield member.title
				else:
					yield member
				
	def __getMembersInternal(self, namespace=False):
		params = {'action':'query',
			'list':'categorymembers',
			'cmtitle':self.title,
			'cmlimit':self.site.limit,
			'cmprop':'title'
		}
		if namespace != False:
			params['cmnamespace'] = namespace
		while True:
			req = api.APIRequest(self.site, params)
			data = req.query(False)
			for item in data['query']['categorymembers']:
				yield page.Page(self.site, item['title'], check=False, followRedir=False)
			try:
				params['cmcontinue'] = data['query-continue']['categorymembers']['cmcontinue']
			except:
				break 
