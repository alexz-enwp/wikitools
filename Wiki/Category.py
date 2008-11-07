import Wiki, Page, API

class Category(Page.Page):
	"""
	A category on the wiki
	title should be the full title, including "Category:"
	"""
	def __init__(self, wiki, title, check=True, followRedir=False, section=False, sectionnumber=False):
		self.members = []
		Page.Page.__init__(self, wiki, title, check, followRedir, section, sectionnumber)
			
	def getAllMembers(self, titleonly=False, reload=False):
		"""
		Gets a list of pages in the category
		titleonly - set to True to only create a list of strings,
		else it will be a list of Page objects
		reload - reload the list even if it was generated before
		"""
		if self.members and not reload:
			return self.members
		else:
			self.members = []
			for page in self.__getMembersInternal(titleonly):
				self.members.append(page)
			return self.members
	
	def getAllMembersGen(self, titleonly=False, reload=False):
		"""
		Generator function for pages in the category
		titleonly - set to True to return strings,
		else it will return Page objects
		reload - reload the list even if it was generated before
		"""
		if self.members and not reload:
			for page in self.members:
				yield page
		else:
			self.members = []
			for page in self.__getMembersInternal(titleonly):
				self.members.append(page)
				yield page
	
	def __getMembersInternal(self, titleonly):
		params = {'action':'query',
			'list':'categorymembers',
			'cmtitle':self.title,
			'cmlimit':self.wiki.limit,
			'cmprop':'title'
		}
		while True:
			req = API.APIRequest(self.wiki, params)
			data = req.query(False)
			for page in data['query']['categorymembers']:
				if titleonly:
					yield page['title']
				else:
					yield Page.Page(self.wiki, page['title'], check=False, followRedir=False)
			try:
				params['cmcontinue'] = data['query-continue']['categorymembers']['cmcontinue']
			except:
				break 