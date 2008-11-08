import Wiki, API, urllib, re

class BadTitle(Wiki.WikiError):
	"""Invalid title"""
	
class NoPage(Wiki.WikiError):
	"""Non-existent page"""

class EditError(Wiki.WikiError):
	"""Problem with edit request"""

class Page:
	""" A page on the wiki
	wiki - A wiki object
	title - The page title, as a string
	check - Checks for existence, normalizes title, required for most things
	followRedir - follow redirects (check must be true)
	section - the section name
	sectionnumber - the section number
	"""	
	def __init__(self, wiki, title, check=True, followRedir=True, section=False, sectionnumber=False):
		self.wiki = wiki
		self.title = title
		self.wikitext = ''
		self.templates = ''
		self.pageid = 0 # The API will set a negative pageid for bad titles
		self.exists = True # If we're not going to check, assume it does
		if check:
			self.setPageInfo(followRedir)
		else: # Guess at some stuff
			self.namespace = False
			for ns in wiki.namespaces:
				if title.startswith(wiki.namespaces[ns]['*']+':'):
					self.namespace = int(ns)
					break
			if not self.namespace:
				self.namespace = 0
		if section or sectionnumber:
			self.setSection(section, sectionnumber)
		else:
			self.section = False
		self.urltitle = urllib.urlencode({self.title.encode('utf-8'):''}).split('=')[0].replace('+', '_').replace('%2F', '/')		

	def setPageInfo(self, followRedir=True):
		"""
		Sets basic page info, required for almost everything
		"""
		
		params = {
			'action': 'query',
			'titles': self.title,
			'indexpageids':'1'
		}
		if followRedir:
			params['redirects'] = '1'
		req = API.APIRequest(self.wiki, params)
		response = req.query()
		if response['query'].has_key('normalized'):
			self.title = response['query']['normalized'][0]['to'].encode('utf-8')
		if followRedir and response['query'].has_key('redirects'):
			self.title = response['query']['redirects'][0]['to'].encode('utf-8')
		self.pageid = response['query']['pageids'][0]
		if not self.title:
			self.title = response['query']['pages'][self.pageid]['title'].encode('utf-8')
		if response['query']['pages'][self.pageid].has_key('missing'):
			self.exists = False
		if response['query']['pages'][self.pageid].has_key('invalid'):
			raise BadTitle(self.title)
		self.namespace = int(response['query']['pages'][self.pageid].get('ns'))
		
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
		params = {
			'action': 'parse',
			'text': '{{:'+self.title+'}}__TOC__',
			'title':self.title,
			'prop':'sections'
		}
		number = False
		req = API.APIRequest(self.wiki, params)
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
		return self.wiki.namespaces[self.namespace].has_key('subpages')
		
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
		try:
			self.namespace
		except:
			self.setPageInfo(False)
		ns = self.namespace
		if ns < 0:
			return False
		nsname = self.wiki.namespaces[ns]['*']
		if self.isTalk():
			newns = self.wiki.namespaces[ns-1]['*']
		else:
			newns = self.wiki.namespaces[ns+1]['*']
		try:
			pagename = self.title.split(nsname+':',1)[1]
		except:
			pagename = self.title
		if newns != '':
			newname = newns+':'+pagename
		else:
			newname = pagename
		return Page(self.wiki, newname, check, followRedir)						
			
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
		req = API.APIRequest(self.wiki, params)
		response = req.query(False)
		self.wikitext = unicode(response['query']['pages'][self.pageid]['revisions'][0]['*'])
		self.lastedittime = response['query']['pages'][self.pageid]['revisions'][0]['timestamp']
		return self.wikitext

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
			'tllimit': self.wiki.limit,
		}
		req = API.APIRequest(self.wiki, params)
		response = req.query()
		self.templates = []
		if isinstance(response, list): #There shouldn't be more than 5000 templates on a page...
			for page in response:
				self.templates.extend(self.__extractTemplates(page))
		else:
			self.templates = self.__extractTemplates(response)
		return self.templates
	
	def __extractTemplates(self, json):
		list = []
		if json['query']['pages'][self.pageid].has_key('templates'):
			for template in json['query']['pages'][self.pageid]['templates']:
				list.append(template['title'].encode('utf-8'))
		return list
	
	def edit(self, newtext=False, prependtext=False, appendtext=False, summary=False, section=False, minor=False, bot=False, basetime=False, recreate=False, createonly=False, nocreate=False, watch=False, unwatch=False):
		"""
		Edit the page
		Most params are self-explanatory
		basetime - set this to the time you loaded the pagetext to avoid
		overwriting other people's edits in edit conflicts
		"""
	
		if not newtext and not prependtext and not appendtext:
			raise EditError("No text specified")
		if prependtext and section:
			raise EditError("Bad param combination")
		if createonly and nocreate:
			raise EditError("Bad param combination")
		token = self.getToken('edit')
		from hashlib import md5
		if newtext:
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
		if newtext:
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
		req = API.APIRequest(self.wiki, params)
		result = req.query()
		return result
		
	def move(self, mvto, reason=False, movetalk=False, noredirect=False, watch=False, unwatch=False):
		"""
		Move the page
		Most params are self-explanatory
		mvto (move to) is the only required param
		must have "suppressredirect" right to use noredirect
		"""
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
		req = API.APIRequest(self.wiki, params)
		result = req.query()
		return result

	def delete(self, reason=False, watch=False, unwatch=False):
		"""
		Delete the page
		Most params are self-explanatory
		"""
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
		req = API.APIRequest(self.wiki, params)
		result = req.query()
		return result
	
	def getToken(self, type):
		""" 
		Get a token for everything except blocks and rollbacks
		type (String) - edit, delete, protect, move, block, unblock, email
		Currently all the tokens are interchangeable, but this may change in the future
		"""
			
		if self.pageid == 0:
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
		req = API.APIRequest(self.wiki, params)
		response = req.query()
		token = response['query']['pages'][self.pageid][type+'token']
		return token			