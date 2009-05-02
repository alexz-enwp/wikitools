# -*- coding: utf-8 -*-
import wiki, page, api, urllib2

class FileDimensionError(wiki.WikiError):
	"""Invalid dimensions"""

class File(page.Page):
	"""
	A File on the wiki
	title should be the full title, including "File:"
	"""
	def __init__(self, wiki, title, check=True, followRedir=False, section=False, sectionnumber=False):
		self.local = ''
		self.url = ''
		page.Page.__init__(self, wiki, title, check, followRedir, section, sectionnumber)
		if self.namespace != 6:
			self.setNamespace(6, check)
		self.usage = []
			
	def getUsage(self, namespaces=False):
		"""
		Gets all list of all the pages that use the file
		force - load the list even if we already loaded it before
		namespaces - list of namespaces to look in
		"""	
		if self.usage and not force:
			return self.usage
		if not self.title:
			self.setPageInfo()
			if not self.title:
				raise page.NoPage
		params = {
			'action': 'query',
			'list': 'imageusage',
			'iulimit': self.site.limit,
		}
		if namespaces is not False:
			params['iunamespace'] = '|'.join([str(ns) for ns in namespaces])
		params['iutitle'] = self.title	
		req = api.APIRequest(self.site, params)
		response = req.query()
		if isinstance(response, list):
			for part in response:
				self.usage.extend(self.__extractToList(part, 'imageusage'))
		else:
			self.usage = self.__extractToList(response, 'imageusage')
		return self.usage
		
	def __extractToList(self, json, stuff):
		list = []
		if stuff in json['query']:
			for item in json['query'][stuff]:
				list.append(item['title'])
		return list
	
	def download(self, width=False, height=False, location=False):
		"""
		Download the image to a local file
		width/height - set width OR height of the downloaded image
		location - set the filename to save to. If not set, the page title
		minus the namespace prefix will be used
		"""
		if self.pageid == 0:
			self.setPageInfo()
		params = {'action':'query',
			'prop':'imageinfo',
			'iiprop':'url'
		}
		if width and height:
			raise DimensionError("Can't specify both width and height")
		if width:
			params['iiurlwidth'] = width
		if height:
			params['iiurlheight'] = height
		if self.pageid != 0:
			params['pageids'] = self.pageid
		elif self.title:
			params['titles'] = self.title
		else:
			self.setPageInfo()
			if not self.exists: # Non-existant files may be on a shared repo (e.g. commons)
				params['titles'] = self.title
			else:
				params['pageids'] = self.pageid
		req = api.APIRequest(self.site, params)
		res = req.query(False)
		key = res['query']['pages'].keys()[0]
		url = res['query']['pages'][key]['imageinfo'][0]['url']
		if not location:
			location = self.title.split(':', 1)[1]
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.site.cookies))
		headers = { "User-agent": self.site.useragent }
		request = urllib2.Request(url, None, headers)
		data = opener.open(request)
		f = open(location, 'wb', 0)
		f.write(data.read())
		f.close()
		return location
			
			